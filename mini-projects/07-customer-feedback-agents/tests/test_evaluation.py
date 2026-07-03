"""Tests for sentiment accuracy and pain calibration."""

from __future__ import annotations

from pipeline.evaluation import pain_calibration, sentiment_accuracy, star_to_sentiment


def test_star_to_sentiment():
    assert star_to_sentiment(1) == "negative"
    assert star_to_sentiment(3) == "neutral"
    assert star_to_sentiment(5) == "positive"


def test_sentiment_accuracy(sample_feedback, sample_sentiment):
    acc = sentiment_accuracy(sample_feedback, sample_sentiment)
    # a1(1*->neg pred neg), y1(2*->neg pred neg), s1(5*->pos pred pos) -> all correct
    assert acc["overall"] == 1.0
    assert acc["amazon"] == 1.0


def test_pain_calibration_positive(sample_feedback, sample_sentiment):
    # high pain aligns with low stars -> positive correlation
    assert pain_calibration(sample_feedback, sample_sentiment) > 0.5
