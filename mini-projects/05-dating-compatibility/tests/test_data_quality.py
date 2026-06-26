"""Tests for the synthetic generator and the data-quality evaluator."""

from __future__ import annotations

from pipeline.data_gen import generate_pairs
from pipeline.data_quality import evaluate_quality
from pipeline.models import PAIR_TYPES, DatingPair


def _pairs(n: int = 600):
    return [DatingPair(**p) for p in generate_pairs(n, seed=1)]


def test_generated_pairs_are_valid_and_balanced():
    raw = generate_pairs(600, seed=1)
    pairs = [DatingPair(**p) for p in raw]  # validates schema
    balance = sum(p.label for p in pairs) / len(pairs)
    assert 0.4 <= balance <= 0.6
    assert {p.pair_type for p in pairs} == set(PAIR_TYPES)


def test_quality_passes_on_generated_data():
    report = evaluate_quality(_pairs(800))
    assert report.passed
    assert report.overall_score >= 60
    assert set(report.by_dimension) == {
        "data_quality",
        "diversity",
        "bias",
        "linguistic",
        "real_life_matching",
    }


def test_quality_flags_duplicate_heavy_data():
    dup = [
        DatingPair(
            text_1="same", text_2="same", label=i % 2, category="values", pair_type="values_aligned"
        )
        for i in range(100)
    ]
    report = evaluate_quality(dup)
    # all-duplicate, single-category, single-pair-type data should fail the gate
    assert not report.passed
    assert report.by_dimension["diversity"] < 50
    assert report.dimensions[0].details["duplicate_rate"] > 0.9
