"""Tests for skill normalization and Jaccard similarity."""

from __future__ import annotations

import pytest

from pipeline.normalizer import (
    jaccard_similarity,
    normalize_skill,
    normalized_skill_set,
)


@pytest.mark.parametrize("raw, expected", [
    ("Python 3", "python"),
    ("React.js", "react"),
    ("Node.js v18", "node"),
    ("  AWS S3  ", "aws s3"),
    ("PostgreSQL", "postgresql"),
    ("TypeScript", "typescript"),
    ("Go", "go"),
])
def test_normalize_skill(raw: str, expected: str):
    assert normalize_skill(raw) == expected


def test_jaccard_identical_sets():
    a = {"python", "fastapi", "docker"}
    assert jaccard_similarity(a, a) == 1.0


def test_jaccard_disjoint_sets():
    a = {"python", "django"}
    b = {"java", "spring"}
    assert jaccard_similarity(a, b) == 0.0


def test_jaccard_partial_overlap():
    a = {"python", "fastapi", "docker"}
    b = {"python", "flask", "docker"}
    # intersection=2, union=4
    assert jaccard_similarity(a, b) == pytest.approx(2 / 4)


def test_jaccard_both_empty():
    assert jaccard_similarity(set(), set()) == 0.0


def test_normalized_skill_set_deduplicates():
    skills = ["Python 3", "python", "Python"]
    result = normalized_skill_set(skills)
    assert result == {"python"}
