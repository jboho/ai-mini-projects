"""Evaluation: sentiment accuracy vs star ratings, pain calibration."""

from __future__ import annotations

import numpy as np

from .models import Feedback, SentimentResult


def star_to_sentiment(star: int) -> str:
    if star <= 2:
        return "negative"
    if star == 3:
        return "neutral"
    return "positive"


def sentiment_accuracy(
    feedback: list[Feedback], sentiments: list[SentimentResult]
) -> dict[str, float]:
    """Accuracy of predicted sentiment vs star-derived expectation, overall + per source."""
    by_id = {f.id: f for f in feedback}
    correct: dict[str, list[int]] = {}
    for s in sentiments:
        fb = by_id.get(s.feedback_id)
        if not fb or fb.rating is None:
            continue
        expected = star_to_sentiment(fb.rating)
        hit = int(expected == s.sentiment)
        correct.setdefault("overall", []).append(hit)
        correct.setdefault(fb.source, []).append(hit)
    return {k: round(sum(v) / len(v), 4) for k, v in correct.items() if v}


def pain_calibration(feedback: list[Feedback], sentiments: list[SentimentResult]) -> float:
    """Pearson correlation between pain intensity and inverted star rating."""
    by_id = {f.id: f for f in feedback}
    pains, inv_stars = [], []
    for s in sentiments:
        fb = by_id.get(s.feedback_id)
        if fb and fb.rating is not None:
            pains.append(s.pain_intensity)
            inv_stars.append(6 - fb.rating)  # 5 stars -> 1, 1 star -> 5
    if len(pains) < 2 or len(set(pains)) < 2 or len(set(inv_stars)) < 2:
        return 0.0
    return round(float(np.corrcoef(pains, inv_stars)[0, 1]), 4)
