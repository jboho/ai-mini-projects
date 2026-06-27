"""Known-answer tests for IR metrics."""

from __future__ import annotations

import math

import pytest

from rag.metrics import (
    average_precision,
    evaluate_retrieval,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_precision_at_k():
    assert precision_at_k({"a", "b"}, ["a", "x", "b"], 3) == pytest.approx(2 / 3)
    assert precision_at_k({"a"}, ["a"], 1) == 1.0


def test_recall_at_k():
    assert recall_at_k({"a", "b"}, ["a", "x"], 3) == 0.5
    assert recall_at_k(set(), ["a"], 3) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank({"a"}, ["x", "a", "y"]) == pytest.approx(0.5)
    assert reciprocal_rank({"a"}, ["x"]) == 0.0


def test_average_precision():
    assert average_precision({"a", "b"}, ["a", "x", "b"]) == pytest.approx((1 + 2 / 3) / 2)


def test_ndcg_at_k():
    assert ndcg_at_k({"a"}, ["x", "a"], 2) == pytest.approx((1 / math.log2(3)))
    assert ndcg_at_k({"a"}, ["a", "x"], 2) == pytest.approx(1.0)


def test_evaluate_retrieval_aggregates():
    per_query = [
        ({"a"}, ["a", "x"]),
        ({"b"}, ["x", "b"]),
    ]
    m = evaluate_retrieval(per_query, k_values=[1, 3])
    assert m.total_queries == 2
    assert m.mrr == pytest.approx((1.0 + 0.5) / 2)
    assert m.recall_at_k["3"] == pytest.approx(1.0)
    assert m.recall_at_k["1"] == pytest.approx(0.5)
