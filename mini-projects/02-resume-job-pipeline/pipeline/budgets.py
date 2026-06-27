"""Budget management for Resume-Job Pipeline.

Tracks costs of:
- Generation: ~0.002 USD per pair (GPT-4o-mini, ~200 tokens)
- API judgment: ~0.005 USD per judgment call
- Correction: ~0.003 USD per attempt

Usage:
    from pipeline.budgets import get_budget_manager, BudgetExceeded

    budget = get_budget_manager()
    export BUDGET_MAX_PAIRS=100  # 100 pairs ≈ $0.50
    export BUDGET_MAX_JUDGES=500  # 500 judgments ≈ $2.50

    try:
        budget.record_generation(cost=0.002)
        budget.record_judgment(cost=0.005)
    except BudgetExceeded:
        # Stop batch, escalate
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


class BudgetExceeded(Exception):
    """Raised when a budget limit is exceeded."""
    pass


@dataclass
class BudgetMetrics:
    """Metrics for a budget category."""
    category: str
    count: int = 0
    total_cost: float = 0.0

    def __str__(self) -> str:
        return f"{self.category}: {self.count} calls, ${self.total_cost:.4f}"


class BudgetManager:
    """Manages LLM call budgets and costs for the pipeline."""

    def __init__(
        self,
        max_pairs: Optional[int] = None,
        max_judges: Optional[int] = None,
        max_cost_usd: Optional[float] = None,
    ):
        """Initialize budget manager.

        Args:
            max_pairs: Max resume/job pairs to generate
            max_judges: Max judgment calls allowed
            max_cost_usd: Max USD spend for the run
        """
        self.max_pairs = max_pairs or int(os.getenv("BUDGET_MAX_PAIRS", "0")) or None
        self.max_judges = max_judges or int(os.getenv("BUDGET_MAX_JUDGES", "0")) or None
        self.max_cost_usd = max_cost_usd or float(os.getenv("BUDGET_MAX_COST_USD", "0")) or None

        self.generation = BudgetMetrics(category="generation")
        self.judgment = BudgetMetrics(category="judgment")
        self.correction = BudgetMetrics(category="correction")
        self.total_cost = 0.0

    def record_generation(self, cost: float = 0.002) -> None:
        """Record a pair generation."""
        if self.max_pairs and self.generation.count >= self.max_pairs:
            raise BudgetExceeded(
                f"Pair generation limit exceeded: {self.generation.count} >= {self.max_pairs}"
            )

        if self.max_cost_usd and (self.total_cost + cost) > self.max_cost_usd:
            raise BudgetExceeded(
                f"Cost limit would be exceeded: ${self.total_cost + cost:.4f} > ${self.max_cost_usd:.4f}"
            )

        self.generation.count += 1
        self.generation.total_cost += cost
        self.total_cost += cost

    def record_judgment(self, cost: float = 0.005, failures: int = 0) -> None:
        """Record a judgment call."""
        if self.max_judges and self.judgment.count >= self.max_judges:
            raise BudgetExceeded(
                f"Judgment limit exceeded: {self.judgment.count} >= {self.max_judges}"
            )

        if self.max_cost_usd and (self.total_cost + cost) > self.max_cost_usd:
            raise BudgetExceeded(
                f"Cost limit would be exceeded: ${self.total_cost + cost:.4f} > ${self.max_cost_usd:.4f}"
            )

        self.judgment.count += 1
        self.judgment.total_cost += cost
        self.total_cost += cost

        if failures >= 3:
            print(f"⚠️  High failure count in judgment: {failures} issues")

    def record_correction(self, cost: float = 0.003) -> None:
        """Record a correction attempt."""
        if self.max_cost_usd and (self.total_cost + cost) > self.max_cost_usd:
            raise BudgetExceeded(
                f"Cost limit would be exceeded: ${self.total_cost + cost:.4f} > ${self.max_cost_usd:.4f}"
            )

        self.correction.count += 1
        self.correction.total_cost += cost
        self.total_cost += cost

    def summary(self) -> str:
        """Get a summary of budget usage."""
        lines = ["Budget Summary:"]
        lines.append(f"  {self.generation}")
        lines.append(f"  {self.judgment}")
        lines.append(f"  {self.correction}")
        lines.append(f"  Total: ${self.total_cost:.4f}")

        if self.max_cost_usd:
            pct = int(100 * self.total_cost / self.max_cost_usd)
            lines.append(f"  Cost limit: ${self.total_cost:.4f} / ${self.max_cost_usd:.4f} ({pct}%)")

        return "\n".join(lines)


_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    """Get or initialize the global budget manager."""
    global _manager
    if _manager is None:
        _manager = BudgetManager()
    return _manager
