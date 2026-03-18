"""Tests for the semantic validator and error categorization."""

from __future__ import annotations

import copy

from pipeline.schemas.validation import ValidationErrorCategory
from pipeline.validator import validate_pair


def test_valid_pair_passes(sample_pair):
    result = validate_pair(sample_pair)
    assert result.is_valid
    assert result.error_count == 0


def test_future_start_date_flagged(sample_pair):
    pair = copy.deepcopy(sample_pair)
    pair.resume.experience[0] = pair.resume.experience[0].__class__(
        company="FutureCo",
        title="Dev",
        start_date="2099-01",
        end_date="Present",
        responsibilities=["future work"],
    )
    result = validate_pair(pair)
    assert not result.is_valid
    cats = [e.category for e in result.errors]
    assert ValidationErrorCategory.LOGICAL_INCONSISTENCY in cats


def test_future_graduation_date_flagged(sample_pair):
    pair = copy.deepcopy(sample_pair)
    edu = pair.resume.education[0]
    pair.resume.education = [
        edu.__class__(
            degree=edu.degree,
            institution=edu.institution,
            graduation_date="2099-05",
        )
    ]
    result = validate_pair(pair)
    assert not result.is_valid
    cats = [e.category for e in result.errors]
    assert ValidationErrorCategory.LOGICAL_INCONSISTENCY in cats


def test_short_phone_flagged(sample_pair):
    pair = copy.deepcopy(sample_pair)
    pair.resume.contact.phone = "123"
    result = validate_pair(pair)
    assert not result.is_valid
    cats = [e.category for e in result.errors]
    assert ValidationErrorCategory.FORMAT_VIOLATION in cats


def test_errors_by_category(sample_pair):
    pair = copy.deepcopy(sample_pair)
    pair.resume.contact.phone = "123"
    result = validate_pair(pair)
    by_cat = result.errors_by_category()
    assert ValidationErrorCategory.FORMAT_VIOLATION in by_cat
