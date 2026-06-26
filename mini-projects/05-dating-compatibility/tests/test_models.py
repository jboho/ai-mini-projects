"""Validation tests for the Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.models import DataQualityReport, DataQualityScore, DatingPair


def test_valid_pair():
    p = DatingPair(
        text_1="I'm a woman who loves travel.",
        text_2="I'm a man who loves travel.",
        label=1,
        category="interests",
        subcategory="travel",
        pair_type="interests_aligned",
    )
    assert p.label == 1 and p.pair_type == "interests_aligned"


def test_invalid_label():
    with pytest.raises(ValidationError):
        DatingPair(text_1="a", text_2="b", label=2, category="values", pair_type="values_aligned")


def test_invalid_pair_type():
    with pytest.raises(ValidationError):
        DatingPair(text_1="a", text_2="b", label=1, category="values", pair_type="bogus")


def test_empty_text_rejected():
    with pytest.raises(ValidationError):
        DatingPair(text_1="", text_2="b", label=1, category="values", pair_type="values_aligned")


def test_quality_report_by_dimension():
    rep = DataQualityReport(
        dimensions=[DataQualityScore(dimension="diversity", score=70.0)],
        overall_score=70.0,
        passed=True,
    )
    assert rep.by_dimension == {"diversity": 70.0}
