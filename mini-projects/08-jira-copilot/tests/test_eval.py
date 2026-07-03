"""Tests for eval metrics and a full offline eval run with the stub embedder."""

from __future__ import annotations

from eval.common import mean, precision_at_k, recall_at_k, reciprocal_rank
from eval.eval_retrieval import run_eval as run_retrieval
from eval.eval_suggestions import run_eval as run_suggestions
from jira_copilot.services.vector_store import StubEmbedder


def test_recall_at_k():
    assert recall_at_k(["A", "B", "C"], ["B"], k=5) == 1.0
    assert recall_at_k(["A", "B", "C"], ["Z"], k=5) == 0.0
    assert recall_at_k(["A", "B"], ["A", "B"], k=1) == 0.5  # only top-1 considered


def test_precision_at_k():
    assert precision_at_k(["A", "B", "C", "D", "E"], ["A"], k=5) == 0.2
    assert precision_at_k(["A"], ["A"], k=0) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(["A", "B", "C"], ["B"]) == 0.5
    assert reciprocal_rank(["A", "B"], ["Z"]) == 0.0
    assert mean([1.0, 0.0]) == 0.5


def test_retrieval_eval_runs_offline():
    results = run_retrieval(embedder=StubEmbedder())
    assert results["n_queries"] == 16
    assert 0.0 <= results["semantic"]["recall@5"] <= 1.0
    assert 0.0 <= results["hybrid"]["recall@5"] <= 1.0


def test_suggestion_eval_runs_offline():
    results = run_suggestions()
    assert results["n_issues"] == 6
    assert results["estimate_mae"] >= 0.0
    assert 0.0 <= results["priority_agreement"] <= 1.0
