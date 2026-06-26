"""Tests for the priority score formula and GapAgent aggregation."""

from __future__ import annotations

import pytest

from pipeline.agents.gap import GapAgent, priority_score
from pipeline.config import PriorityWeights
from pipeline.models import AlignmentResult

_W = PriorityWeights()


def test_priority_uncovered_beats_covered():
    covered = priority_score(0.8, 1.0, has_coverage=True, neg_ratio=1.0, weights=_W)
    gap = priority_score(0.8, 1.0, has_coverage=False, neg_ratio=1.0, weights=_W)
    assert gap > covered
    assert gap == pytest.approx(0.35 * 0.8 + 0.25 * 1.0 + 0.25 * 1.0 + 0.15 * 1.0)


def test_priority_zero_when_empty():
    assert priority_score(0.0, 0.0, has_coverage=True, neg_ratio=0.0, weights=_W) == 0.0


def test_gap_agent_sorts_and_flags_coverage(sample_themes, sample_sentiment):
    alignments = [
        AlignmentResult(theme_id="T1", aligned=True, roadmap_item_id="R1"),
        AlignmentResult(theme_id="T2", aligned=False),
        AlignmentResult(theme_id="T3", aligned=False),
    ]
    gaps = GapAgent().analyze(
        sample_themes, alignments, sample_sentiment, generate_recommendations=False
    )
    assert [g.priority_score for g in gaps] == sorted(
        (g.priority_score for g in gaps), reverse=True
    )
    cov = {g.theme_id: g.has_coverage for g in gaps}
    assert cov["T1"] is True and cov["T2"] is False
