"""Validation tests for the Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import EvaluationConfig, EvaluationResult, StyleFeatures, StyleProfile


def test_evaluation_result_score_bounds():
    with pytest.raises(ValidationError):
        EvaluationResult(
            style_score=1.5,
            groundedness_score=0.5,
            confidence_score=0.5,
            final_score=0.5,
            decision="deliver",
        )


def test_evaluation_decision_literal():
    with pytest.raises(ValidationError):
        EvaluationResult(
            style_score=0.5,
            groundedness_score=0.5,
            confidence_score=0.5,
            final_score=0.5,
            decision="maybe",
        )


def test_evaluation_config_defaults():
    cfg = EvaluationConfig()
    assert cfg.style_weight + cfg.groundedness_weight + cfg.confidence_weight == pytest.approx(1.0)
    assert cfg.deliver_threshold == 0.75


def test_style_profile_roundtrip():
    profile = StyleProfile(
        employee_name="vince.kaminski",
        email_count=200,
        style_features=StyleFeatures(avg_message_length=42.0),
        style_embedding=[0.1, 0.2, 0.3],
    )
    restored = StyleProfile.model_validate_json(profile.model_dump_json())
    assert restored.employee_name == "vince.kaminski"
    assert restored.style_features.avg_message_length == 42.0
