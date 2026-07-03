"""5-dimension data quality evaluator with a >= 60/100 training gate.

Each dimension returns a 0-100 score; the overall score is their mean. Scoring is
designed to reward a well-formed dataset (balanced labels, even categories, gender
balance, varied vocabulary, full preference-hierarchy coverage) while still
penalizing real defects (duplicates, label skew, missing categories).
"""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

from .models import CATEGORIES, PAIR_TYPES, DataQualityReport, DataQualityScore, DatingPair

_WORD_RE = re.compile(r"[a-z']+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _words(pair: DatingPair) -> list[str]:
    return _tokens(pair.text_1) + _tokens(pair.text_2)


def _clamp(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


def _shannon_evenness(counts: list[int]) -> float:
    total = sum(counts)
    if total == 0 or len(counts) <= 1:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    entropy = -sum(p * math.log(p) for p in probs)
    return entropy / math.log(len(counts))


def _data_quality(pairs: list[DatingPair]) -> DataQualityScore:
    n = len(pairs)
    complete = sum(1 for p in pairs if p.text_1.strip() and p.text_2.strip() and p.category)
    completeness = 100 * complete / n
    dup = n - len({(p.text_1, p.text_2) for p in pairs})
    dup_rate = dup / n
    dup_score = _clamp(100 * (1 - dup_rate / 0.05))
    label_valid = 100.0  # enforced by the schema
    score = (completeness + dup_score + label_valid) / 3
    return DataQualityScore(
        dimension="data_quality",
        score=_clamp(score),
        details={"completeness": completeness, "duplicate_rate": round(dup_rate, 4)},
    )


def _diversity(pairs: list[DatingPair]) -> DataQualityScore:
    all_tokens = [t for p in pairs for t in _words(p)]
    unique = len(set(all_tokens))
    vocab_score = _clamp(unique / 200 * 100)

    cat_counts = Counter(p.category for p in pairs)
    cat_evenness = 100 * _shannon_evenness([cat_counts.get(c, 0) for c in CATEGORIES])

    balance = sum(p.label for p in pairs) / len(pairs)
    balance_score = _clamp(100 * (1 - abs(balance - 0.5) / 0.1))  # full marks in 40-60%

    lengths = [len(_words(p)) for p in pairs]
    cv = float(np.std(lengths) / np.mean(lengths)) if np.mean(lengths) else 0.0
    length_var_score = _clamp(min(cv / 0.3, 1.0) * 100)

    score = (vocab_score + cat_evenness + balance_score + length_var_score) / 4
    return DataQualityScore(
        dimension="diversity",
        score=_clamp(score),
        details={
            "unique_tokens": unique,
            "category_evenness": round(cat_evenness, 1),
            "label_balance": round(balance, 3),
        },
    )


def _bias(pairs: list[DatingPair]) -> DataQualityScore:
    text = " ".join(p.text_1 + " " + p.text_2 for p in pairs).lower()
    men, women = text.count(" man "), text.count(" woman ")
    gender_score = _clamp(100 * (1 - abs(men - women) / max(men + women, 1)))

    devs = []
    for cat in CATEGORIES:
        cat_pairs = [p for p in pairs if p.category == cat]
        if cat_pairs:
            rate = sum(p.label for p in cat_pairs) / len(cat_pairs)
            devs.append(abs(rate - 0.5))
    corr_score = _clamp(100 * (1 - 2 * (sum(devs) / len(devs)))) if devs else 0.0

    len1 = [len(_words(p)) for p in pairs if p.label == 1]
    len0 = [len(_words(p)) for p in pairs if p.label == 0]
    if len1 and len0:
        rel = abs(np.mean(len1) - np.mean(len0)) / max(np.mean(len1 + len0), 1)
        length_bias_score = _clamp(100 * (1 - rel / 0.2))
    else:
        length_bias_score = 0.0

    score = (gender_score + corr_score + length_bias_score) / 3
    return DataQualityScore(
        dimension="bias",
        score=_clamp(score),
        details={
            "gender_balance": round(gender_score, 1),
            "category_label_corr": round(corr_score, 1),
        },
    )


def _linguistic(pairs: list[DatingPair]) -> DataQualityScore:
    texts = [t for p in pairs for t in (p.text_1, p.text_2)]
    text_lengths = [len(_tokens(t)) for t in texts]
    mean_len = float(np.mean(text_lengths))
    length_score = _clamp(100 - abs(mean_len - 14) * 5)  # ideal ~14 words per profile text

    # Within-text token repetition catches garbled/repetitive text; clean profile
    # sentences repeat few words, so a low rate scores high.
    rep_rates = []
    for t in texts:
        toks = _tokens(t)
        if toks:
            rep_rates.append(1 - len(set(toks)) / len(toks))
    rep_rate = float(np.mean(rep_rates)) if rep_rates else 1.0
    repetition_score = _clamp(100 * (1 - rep_rate / 0.5))  # 50% within-text repeat -> 0

    garbled = sum(1 for t in texts if not _tokens(t))
    coherence_score = _clamp(100 * (1 - garbled / len(texts)))

    score = (length_score + repetition_score + coherence_score) / 3
    return DataQualityScore(
        dimension="linguistic",
        score=_clamp(score),
        details={
            "mean_words_per_text": round(mean_len, 1),
            "within_text_repetition": round(rep_rate, 3),
        },
    )


def _real_life(pairs: list[DatingPair]) -> DataQualityScore:
    present_cats = {p.category for p in pairs}
    hierarchy = ["dealbreakers", "values", "lifestyle", "interests"]
    hierarchy_score = 100 * sum(c in present_cats for c in hierarchy) / len(hierarchy)

    multi_frac = sum(1 for p in pairs if p.pair_type == "multi_preference") / len(pairs)
    multi_score = _clamp(min(multi_frac / 0.10, 1.0) * 100)  # ~10% multi-pref is full marks

    present_types = {p.pair_type for p in pairs}
    coverage_score = 100 * len(present_types & set(PAIR_TYPES)) / len(PAIR_TYPES)

    score = (hierarchy_score + multi_score + coverage_score) / 3
    return DataQualityScore(
        dimension="real_life_matching",
        score=_clamp(score),
        details={"pair_type_coverage": len(present_types), "multi_fraction": round(multi_frac, 3)},
    )


def evaluate_quality(pairs: list[DatingPair], threshold: float = 60.0) -> DataQualityReport:
    dims = [
        _data_quality(pairs),
        _diversity(pairs),
        _bias(pairs),
        _linguistic(pairs),
        _real_life(pairs),
    ]
    overall = sum(d.score for d in dims) / len(dims)
    return DataQualityReport(
        dimensions=dims,
        overall_score=_clamp(overall),
        passed=overall >= threshold,
        threshold=threshold,
    )
