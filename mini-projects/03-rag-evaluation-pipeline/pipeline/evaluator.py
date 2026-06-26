"""Information-retrieval metrics and dataset-level aggregation.

All per-query functions take ``relevant`` (the ground-truth chunk ids for a
query) and ``retrieved`` (the ranked list of chunk ids returned by a retriever).
Relevance is binary. These functions are pure and deterministic.
"""

from __future__ import annotations

import math

from .models import MetricsResult, QAExample, RetrievalResult


def recall_at_k(relevant: list[str], retrieved: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    hits = sum(1 for cid in retrieved[:k] if cid in relevant_set)
    return hits / len(relevant_set)


def precision_at_k(relevant: list[str], retrieved: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    relevant_set = set(relevant)
    hits = sum(1 for cid in retrieved[:k] if cid in relevant_set)
    return hits / k


def mean_reciprocal_rank(relevant: list[str], retrieved: list[str]) -> float:
    relevant_set = set(relevant)
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant_set:
            return 1.0 / rank
    return 0.0


def average_precision(relevant: list[str], retrieved: list[str]) -> float:
    """Average precision for a single query (the per-query term of MAP)."""
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    hits = 0
    score = 0.0
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant_set:
            hits += 1
            score += hits / rank
    return score / len(relevant_set)


def ndcg_at_k(relevant: list[str], retrieved: list[str], k: int) -> float:
    relevant_set = set(relevant)
    dcg = 0.0
    for rank, cid in enumerate(retrieved[:k], start=1):
        if cid in relevant_set:
            dcg += 1.0 / math.log2(rank + 1)

    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_retrieval(
    qa_dataset: list[QAExample],
    retrieval_results: list[RetrievalResult],
    k_values: list[int] | None = None,
) -> MetricsResult:
    """Aggregate per-query metrics across a QA dataset.

    ``qa_dataset[i]`` is paired with ``retrieval_results[i]``; lengths must match.
    """
    if len(qa_dataset) != len(retrieval_results):
        raise ValueError("qa_dataset and retrieval_results must be the same length")

    k_values = k_values or [1, 3, 5, 10]
    recall_acc: dict[int, list[float]] = {k: [] for k in k_values}
    precision_acc: dict[int, list[float]] = {k: [] for k in k_values}
    ndcg_acc: dict[int, list[float]] = {k: [] for k in k_values}
    mrr_acc: list[float] = []
    ap_acc: list[float] = []
    times: list[float] = []

    for qa, result in zip(qa_dataset, retrieval_results):
        relevant = qa.relevant_chunk_ids
        retrieved = result.retrieved_chunk_ids
        for k in k_values:
            recall_acc[k].append(recall_at_k(relevant, retrieved, k))
            precision_acc[k].append(precision_at_k(relevant, retrieved, k))
            ndcg_acc[k].append(ndcg_at_k(relevant, retrieved, k))
        mrr_acc.append(mean_reciprocal_rank(relevant, retrieved))
        ap_acc.append(average_precision(relevant, retrieved))
        times.append(result.time_taken)

    return MetricsResult(
        recall_at_k={str(k): _mean(recall_acc[k]) for k in k_values},
        precision_at_k={str(k): _mean(precision_acc[k]) for k in k_values},
        ndcg_at_k={str(k): _mean(ndcg_acc[k]) for k in k_values},
        mrr=_mean(mrr_acc),
        map_score=_mean(ap_acc),
        total_queries=len(qa_dataset),
        avg_retrieval_time=_mean(times),
    )
