"""Budget management for RAG Pipeline.

Tracks costs of:
- Embedding API calls (~$0.00002 per query embedding, ~$0.0001 per chunk embedding)
- LLM generation (~$0.001 per completion)
- Retrieval latency limits (SLA enforcement)

Usage:
    from rag.budgets import get_budget_manager, BudgetExceeded

    budget = get_budget_manager()
    export BUDGET_MAX_QUERIES=1000
    export BUDGET_MAX_COST_USD=5.0  # ~$5 for 1000 queries

    try:
        budget.record_embedding(cost=0.0001, latency_ms=50)
    except BudgetExceeded:
        # Use cached embeddings or fallback retriever
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


class BudgetExceeded(Exception):
    """Raised when a budget limit is exceeded."""
    pass


@dataclass
class LatencyStats:
    """Latency tracking for SLA enforcement."""
    p50_ms: float = 0
    p95_ms: float = 0
    p99_ms: float = 0
    count: int = 0

    def update(self, latency_ms: float) -> None:
        """Update with a new latency measurement."""
        self.count += 1
        # Simple approximation (full percentile tracking would use histogram)
        if self.p50_ms == 0:
            self.p50_ms = latency_ms
        else:
            self.p50_ms = (self.p50_ms * 0.9) + (latency_ms * 0.1)


class BudgetManager:
    """Manages costs and latency for RAG pipeline."""

    def __init__(
        self,
        max_queries: Optional[int] = None,
        max_cost_usd: Optional[float] = None,
        max_retrieval_latency_ms: int = 200,
    ):
        """Initialize budget manager.

        Args:
            max_queries: Max queries to process
            max_cost_usd: Max USD spend
            max_retrieval_latency_ms: SLA target for retrieval (milliseconds)
        """
        self.max_queries = max_queries or int(os.getenv("BUDGET_MAX_QUERIES", "0")) or None
        self.max_cost_usd = max_cost_usd or float(os.getenv("BUDGET_MAX_COST_USD", "0")) or None
        self.max_retrieval_latency_ms = max_retrieval_latency_ms

        self.queries_processed = 0
        self.total_cost = 0.0
        self.embedding_calls = 0
        self.generation_calls = 0
        self.retrieval_stats = LatencyStats()

    def record_query(self) -> None:
        """Record a query processed."""
        if self.max_queries and self.queries_processed >= self.max_queries:
            raise BudgetExceeded(
                f"Query limit exceeded: {self.queries_processed} >= {self.max_queries}"
            )
        self.queries_processed += 1

    def record_embedding(self, cost: float = 0.0001, latency_ms: float = 0) -> None:
        """Record an embedding call."""
        if self.max_cost_usd and (self.total_cost + cost) > self.max_cost_usd:
            raise BudgetExceeded(
                f"Cost would exceed budget: ${self.total_cost + cost:.6f} > ${self.max_cost_usd:.6f}"
            )
        self.embedding_calls += 1
        self.total_cost += cost

    def record_retrieval(self, latency_ms: float) -> None:
        """Record a retrieval operation and check SLA."""
        self.retrieval_stats.update(latency_ms)
        if latency_ms > self.max_retrieval_latency_ms:
            print(
                f"⚠️  SLA violation: retrieval took {latency_ms}ms "
                f"(target: {self.max_retrieval_latency_ms}ms)"
            )

    def record_generation(self, cost: float = 0.001) -> None:
        """Record an LLM generation call."""
        if self.max_cost_usd and (self.total_cost + cost) > self.max_cost_usd:
            raise BudgetExceeded(
                f"Cost would exceed budget: ${self.total_cost + cost:.6f} > ${self.max_cost_usd:.6f}"
            )
        self.generation_calls += 1
        self.total_cost += cost

    def summary(self) -> str:
        """Get a summary of usage."""
        lines = ["Budget Summary:"]
        lines.append(f"  Queries: {self.queries_processed}")
        lines.append(f"  Embeddings: {self.embedding_calls}")
        lines.append(f"  Generations: {self.generation_calls}")
        lines.append(f"  Total cost: ${self.total_cost:.6f}")

        if self.max_cost_usd:
            pct = int(100 * self.total_cost / self.max_cost_usd)
            lines.append(f"  Cost limit: ${self.total_cost:.6f} / ${self.max_cost_usd:.6f} ({pct}%)")

        lines.append(f"  Retrieval latency: p50={self.retrieval_stats.p50_ms:.0f}ms")

        if self.max_queries:
            pct = int(100 * self.queries_processed / self.max_queries)
            lines.append(f"  Query limit: {self.queries_processed} / {self.max_queries} ({pct}%)")

        return "\n".join(lines)


_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    """Get or initialize the global budget manager."""
    global _manager
    if _manager is None:
        _manager = BudgetManager()
    return _manager
