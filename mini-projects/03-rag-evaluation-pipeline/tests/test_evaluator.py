"""Known-answer tests for IR metrics (hand-computed expected values)."""

from __future__ import annotations

import math

import pytest

from pipeline.evaluator import (
    average_precision,
    evaluate_retrieval,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from pipeline.models import QAExample, RetrievalResult


def test_recall_at_k():
    assert recall_at_k(["a"], ["x", "a", "y"], 3) == 1.0
    assert recall_at_k(["a"], ["x", "a", "y"], 1) == 0.0
    assert recall_at_k(["a", "b"], ["a", "x", "y"], 3) == 0.5
    assert recall_at_k([], ["a"], 3) == 0.0


def test_precision_at_k():
    assert precision_at_k(["a", "b"], ["a", "x", "b"], 3) == pytest.approx(2 / 3)
    assert precision_at_k(["a"], ["a", "x"], 1) == 1.0
    assert precision_at_k(["a"], ["x"], 0) == 0.0


def test_mean_reciprocal_rank():
    assert mean_reciprocal_rank(["a"], ["x", "a", "y"]) == pytest.approx(0.5)
    assert mean_reciprocal_rank(["a"], ["a", "x"]) == 1.0
    assert mean_reciprocal_rank(["a"], ["x", "y"]) == 0.0


def test_average_precision():
    # hits at rank 1 (1/1) and rank 3 (2/3), 2 relevant -> (1 + 0.6667) / 2
    assert average_precision(["a", "b"], ["a", "x", "b"]) == pytest.approx((1 + 2 / 3) / 2)
    assert average_precision([], ["a"]) == 0.0


def test_ndcg_at_k():
    # single relevant doc at rank 2: dcg = 1/log2(3), idcg = 1/log2(2) = 1
    expected = (1 / math.log2(3)) / 1.0
    assert ndcg_at_k(["a"], ["x", "a"], 2) == pytest.approx(expected)
    # relevant doc at rank 1 -> perfect
    assert ndcg_at_k(["a"], ["a", "x"], 2) == pytest.approx(1.0)


def test_evaluate_retrieval_aggregates():
    qa = [
        QAExample(question="q1", relevant_chunk_ids=["a"]),
        QAExample(question="q2", relevant_chunk_ids=["b"]),
    ]
    results = [
        RetrievalResult(query="q1", retrieved_chunk_ids=["a", "x"], scores=[0.9, 0.1], method="v"),
        RetrievalResult(query="q2", retrieved_chunk_ids=["x", "b"], scores=[0.8, 0.2], method="v"),
    ]
    metrics = evaluate_retrieval(qa, results, k_values=[1, 3])
    assert metrics.total_queries == 2
    assert metrics.mrr == pytest.approx((1.0 + 0.5) / 2)
    assert metrics.recall_at_k["3"] == pytest.approx(1.0)
    assert metrics.recall_at_k["1"] == pytest.approx(0.5)


def test_evaluate_retrieval_length_mismatch():
    qa = [QAExample(question="q1", relevant_chunk_ids=["a"])]
    with pytest.raises(ValueError):
        evaluate_retrieval(qa, [], k_values=[1])
