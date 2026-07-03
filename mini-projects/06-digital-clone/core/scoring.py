"""Response evaluation math (pure): style, groundedness, confidence -> decision.

final = style_weight*style + groundedness_weight*groundedness + confidence_weight*confidence
Weights and threshold come from EvaluationConfig.
"""

from __future__ import annotations

import re

import numpy as np

from .models import EmailMessage, EvaluationConfig, EvaluationResult, KnowledgeChunk, StyleProfile
from .style_features import extract_features, vectorize_features

_WORD_RE = re.compile(r"[a-zA-Z']+")
_HEDGES = ["maybe", "perhaps", "i think", "not sure", "possibly", "might", "unclear", "i guess"]


def _words(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def style_score(response: str, profile: StyleProfile) -> float:
    """Cosine between the response's style vector and the profile embedding."""
    resp_vec = vectorize_features(extract_features([EmailMessage(body=response)]))
    prof_vec = np.asarray(profile.style_embedding, dtype="float32")
    if resp_vec.shape != prof_vec.shape or not np.any(resp_vec) or not np.any(prof_vec):
        return 0.0
    cos = float(np.dot(resp_vec, prof_vec) / (np.linalg.norm(resp_vec) * np.linalg.norm(prof_vec)))
    return _clamp01(cos)


def groundedness_score(response: str, chunks: list[KnowledgeChunk]) -> float:
    """Fraction of response content words present in the retrieved chunks."""
    resp = _words(response)
    if not resp:
        return 0.0
    chunk_words = set().union(*[_words(c.content) for c in chunks]) if chunks else set()
    return _clamp01(len(resp & chunk_words) / len(resp))


def confidence_score(retrieval_scores: list[float], response: str) -> float:
    """Average retrieval relevance minus a hedging penalty."""
    avg_sim = float(np.mean(retrieval_scores)) if retrieval_scores else 0.0
    hedges = sum(response.lower().count(h) for h in _HEDGES)
    return _clamp01(avg_sim - 0.1 * hedges)


def evaluate_response(
    response: str,
    retrieved: list[tuple[KnowledgeChunk, float]],
    profile: StyleProfile,
    config: EvaluationConfig | None = None,
) -> EvaluationResult:
    config = config or EvaluationConfig()
    chunks = [c for c, _ in retrieved]
    scores = [s for _, s in retrieved]

    style = style_score(response, profile)
    ground = groundedness_score(response, chunks)
    conf = confidence_score(scores, response)
    final = (
        config.style_weight * style
        + config.groundedness_weight * ground
        + config.confidence_weight * conf
    )
    decision = "deliver" if final >= config.deliver_threshold else "fallback"
    return EvaluationResult(
        style_score=round(style, 4),
        groundedness_score=round(ground, 4),
        confidence_score=round(conf, 4),
        final_score=round(_clamp01(final), 4),
        decision=decision,
        reasoning=(
            f"style={style:.2f}, groundedness={ground:.2f}, confidence={conf:.2f} "
            f"-> {final:.2f} ({'>=' if decision == 'deliver' else '<'} {config.deliver_threshold})"
        ),
    )
