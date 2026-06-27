"""Information-retrieval metrics over relevant/retrieved chunk-id sets.

Pure and deterministic. ``relevant`` is the set of ground-truth chunk ids for a
query (chunks overlapping the qrel section); ``retrieved`` is the ranked list of
chunk ids a retriever returned.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from .models import MetricsResult


def precision_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for cid in retrieved[:k] if cid in relevant)
    return hits / k


def recall_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = sum(1 for cid in retrieved[:k] if cid in relevant)
    return hits / len(relevant)


def reciprocal_rank(relevant: set[str], retrieved: list[str]) -> float:
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant:
            return 1.0 / rank
    return 0.0


def average_precision(relevant: set[str], retrieved: list[str]) -> float:
    if not relevant:
        return 0.0
    hits = 0
    score = 0.0
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant:
            hits += 1
            score += hits / rank
    return score / len(relevant)


def ndcg_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, cid in enumerate(retrieved[:k], start=1)
        if cid in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_retrieval(
    per_query: Iterable[tuple[set[str], list[str]]],
    k_values: list[int] | None = None,
    times: list[float] | None = None,
) -> MetricsResult:
    """Aggregate metrics over ``(relevant_ids, retrieved_ids)`` per query."""
    k_values = k_values or [1, 3, 5, 10]
    per_query = list(per_query)
    prec = {k: [] for k in k_values}
    rec = {k: [] for k in k_values}
    ndcg = {k: [] for k in k_values}
    rr, ap = [], []

    for relevant, retrieved in per_query:
        for k in k_values:
            prec[k].append(precision_at_k(relevant, retrieved, k))
            rec[k].append(recall_at_k(relevant, retrieved, k))
            ndcg[k].append(ndcg_at_k(relevant, retrieved, k))
        rr.append(reciprocal_rank(relevant, retrieved))
        ap.append(average_precision(relevant, retrieved))

    return MetricsResult(
        precision_at_k={str(k): _mean(prec[k]) for k in k_values},
        recall_at_k={str(k): _mean(rec[k]) for k in k_values},
        ndcg_at_k={str(k): _mean(ndcg[k]) for k in k_values},
        mrr=_mean(rr),
        map_score=_mean(ap),
        total_queries=len(per_query),
        avg_retrieval_time=_mean(times) if times else 0.0,
    )
