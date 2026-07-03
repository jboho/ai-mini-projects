"""Writing-style feature extraction, vectorization, and incremental learning.

Extracts 11+ interpretable features from a person's emails and packs them into a
fixed-length vector (the style embedding). Incremental learning updates the
embedding with an exponential moving average so new email batches refine the
profile without full recomputation.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone

import numpy as np

from .models import EmailMessage, StyleFeatures, StyleProfile

_WORD_RE = re.compile(r"[a-zA-Z']+")

GREETINGS = ["hi", "dear", "hey", "hello", "none"]
SIGNOFFS = ["thanks", "regards", "best", "sincerely", "none"]
PUNCTUATION = ["...", "!!", "--", ";"]
CONNECTORS = ["because", "therefore", "however", "thus", "although"]
SENTIMENT_KEYS = ["pos", "neu", "neg"]

_POS_WORDS = {"good", "great", "thanks", "appreciate", "happy", "glad", "excellent", "agree"}
_NEG_WORDS = {"bad", "problem", "issue", "concern", "wrong", "sorry", "unfortunately", "disagree"}
_FORMAL = {"regarding", "therefore", "hereby", "furthermore", "sincerely", "kindly", "please"}
_INFORMAL = {"gonna", "wanna", "yeah", "hey", "ok", "thanks", "cool", "stuff"}
_TECHNICAL = {
    "model",
    "analysis",
    "data",
    "risk",
    "trade",
    "market",
    "price",
    "portfolio",
    "algorithm",
    "system",
}


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _distribution(emails, keywords, picker) -> dict[str, float]:
    n = len(emails) or 1
    counts = {k: 0 for k in keywords}
    for e in emails:
        match = picker(e)
        counts[match if match in counts else "none"] += 1
    return {k: round(v / n, 4) for k, v in counts.items()}


def _greeting_of(email: EmailMessage) -> str:
    first = email.body.strip().split()
    return first[0].lower().strip(",!") if first else "none"


def _signoff_of(email: EmailMessage) -> str:
    tokens = _words(email.body)
    for w in reversed(tokens[-6:]):
        if w in {"thanks", "regards", "best", "sincerely"}:
            return w
    return "none"


def extract_features(emails: list[EmailMessage]) -> StyleFeatures:
    bodies = [e.body for e in emails]
    all_words = [w for b in bodies for w in _words(b)]
    total_words = len(all_words) or 1
    n = len(emails) or 1

    alpha_chars = [c for b in bodies for c in b if c.isalpha()]
    upper = sum(1 for c in alpha_chars if c.isupper())
    cap_ratio = upper / (len(alpha_chars) or 1)

    bigrams = Counter(zip(all_words, all_words[1:]))
    common = [f"{a} {b}" for (a, b), _ in bigrams.most_common(10)]

    punct = {p: round(sum(b.count(p) for b in bodies) / n, 4) for p in PUNCTUATION}
    connectors = {c: round(all_words.count(c) / total_words, 5) for c in CONNECTORS}

    pos = sum(1 for w in all_words if w in _POS_WORDS)
    neg = sum(1 for w in all_words if w in _NEG_WORDS)
    neu = total_words - pos - neg
    sentiment = {
        "pos": round(pos / total_words, 4),
        "neg": round(neg / total_words, 4),
        "neu": round(neu / total_words, 4),
    }

    formal = sum(1 for w in all_words if w in _FORMAL)
    informal = sum(1 for w in all_words if w in _INFORMAL)
    formality = formal / ((formal + informal) or 1)
    technical = sum(1 for w in all_words if w in _TECHNICAL) / total_words

    return StyleFeatures(
        avg_message_length=round(total_words / n, 2),
        greeting_patterns=_distribution(emails, GREETINGS, _greeting_of),
        signoff_patterns=_distribution(emails, SIGNOFFS, _signoff_of),
        punctuation_patterns=punct,
        capitalization_ratio=round(cap_ratio, 4),
        question_frequency=round(sum(b.count("?") for b in bodies) / n, 3),
        vocabulary_richness=round(len(set(all_words)) / total_words, 4),
        common_phrases=common,
        reasoning_patterns=connectors,
        sentiment_distribution=sentiment,
        formality_level=round(formality, 4),
        technical_terminology_usage=round(technical, 5),
    )


def vectorize_features(f: StyleFeatures) -> np.ndarray:
    """Pack features into a fixed-length, deterministically-ordered vector."""
    vec: list[float] = [
        f.avg_message_length / 100.0,  # scaled to ~[0,1]
        f.capitalization_ratio,
        f.question_frequency,
        f.vocabulary_richness,
        f.formality_level,
        f.technical_terminology_usage,
    ]
    vec += [f.greeting_patterns.get(k, 0.0) for k in GREETINGS]
    vec += [f.signoff_patterns.get(k, 0.0) for k in SIGNOFFS]
    vec += [f.punctuation_patterns.get(k, 0.0) for k in PUNCTUATION]
    vec += [f.reasoning_patterns.get(k, 0.0) for k in CONNECTORS]
    vec += [f.sentiment_distribution.get(k, 0.0) for k in SENTIMENT_KEYS]
    return np.asarray(vec, dtype="float32")


def incremental_update(current: np.ndarray, new: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    if current.size == 0:
        return new
    return (1 - alpha) * current + alpha * new


def build_style_profile(
    employee: str, emails: list[EmailMessage], alpha: float = 0.3
) -> StyleProfile:
    features = extract_features(emails)
    embedding = vectorize_features(features)
    return StyleProfile(
        employee_name=employee,
        email_count=len(emails),
        style_features=features,
        style_embedding=embedding.tolist(),
        last_updated=datetime.now(timezone.utc),
        learning_alpha=alpha,
    )
