"""Validation tests for the Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.models import Feedback, GapAnalysis, SentimentResult


def test_feedback_requires_text():
    with pytest.raises(ValidationError):
        Feedback(id="x", source="amazon", text="")


def test_feedback_source_literal():
    with pytest.raises(ValidationError):
        Feedback(id="x", source="reddit", text="hello")


def test_sentiment_bounds():
    with pytest.raises(ValidationError):
        SentimentResult(feedback_id="x", sentiment="negative", confidence=1.5, pain_intensity=0.5)


def test_sentiment_literal():
    with pytest.raises(ValidationError):
        SentimentResult(feedback_id="x", sentiment="angry", confidence=0.5, pain_intensity=0.5)


def test_gap_priority_bounds():
    GapAnalysis(theme_id="T1", theme_name="t", priority_score=0.5)
    with pytest.raises(ValidationError):
        GapAnalysis(theme_id="T1", theme_name="t", priority_score=1.2)
