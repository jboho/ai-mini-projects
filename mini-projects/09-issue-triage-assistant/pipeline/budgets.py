"""Token and cost budgets for Issue Triage Assistant.

Enforces per-session and per-operation limits on LLM calls to prevent runaway costs
and token consumption. Budgets can be configured via environment variables.

Usage:
    from pipeline.budgets import BudgetManager, BudgetExceeded

    budget = BudgetManager(max_tokens=50000, max_cost_usd=10.0)

    try:
        budget.check_and_record("classify", tokens=150, cost=0.0015)
    except BudgetExceeded as e:
        print(f"Budget exceeded: {e}")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BudgetType(Enum):
    """Types of budgets."""
    TOKENS = "tokens"
    COST = "cost"


class BudgetExceeded(Exception):
    """Raised when a budget limit is exceeded."""
    pass


@dataclass
class BudgetMetrics:
    """Metrics for a budget."""
    operation: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    call_count: int = 0

    def __str__(self) -> str:
        return (
            f"{self.operation}: {self.call_count} calls, "
            f"{self.tokens_used:,} tokens, ${self.cost_usd:.4f}"
        )


class BudgetManager:
    """Manages token and cost budgets across operations."""

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        max_cost_usd: Optional[float] = None,
        warn_at_pct: int = 80,
    ):
        """Initialize budget manager.

        Args:
            max_tokens: Maximum tokens for the session (from env: BUDGET_MAX_TOKENS)
            max_cost_usd: Maximum cost in USD (from env: BUDGET_MAX_COST_USD)
            warn_at_pct: Warn when usage exceeds this percentage of limit
        """
        self.max_tokens = max_tokens or int(os.getenv("BUDGET_MAX_TOKENS", "0")) or None
        self.max_cost_usd = max_cost_usd or float(os.getenv("BUDGET_MAX_COST_USD", "0")) or None
        self.warn_at_pct = warn_at_pct

        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.operations: dict[str, BudgetMetrics] = {}

    def check_and_record(
        self,
        operation: str,
        tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Check budget and record usage.

        Args:
            operation: Name of the operation (for tracking)
            tokens: Tokens to consume
            cost: Cost in USD

        Raises:
            BudgetExceeded: If budget would be exceeded
        """
        new_tokens = self.total_tokens_used + tokens
        new_cost = self.total_cost_usd + cost

        # Check token budget
        if self.max_tokens and new_tokens > self.max_tokens:
            raise BudgetExceeded(
                f"{operation} would exceed token budget: "
                f"{self.total_tokens_used:,} + {tokens} > {self.max_tokens:,}"
            )

        # Check cost budget
        if self.max_cost_usd and new_cost > self.max_cost_usd:
            raise BudgetExceeded(
                f"{operation} would exceed cost budget: "
                f"${self.total_cost_usd:.4f} + ${cost:.4f} > ${self.max_cost_usd:.4f}"
            )

        # Record usage
        self.total_tokens_used = new_tokens
        self.total_cost_usd = new_cost

        if operation not in self.operations:
            self.operations[operation] = BudgetMetrics(operation=operation)

        ops = self.operations[operation]
        ops.tokens_used += tokens
        ops.cost_usd += cost
        ops.call_count += 1

        # Warn if approaching limit
        if self.max_tokens and self._pct_of_budget("tokens") >= self.warn_at_pct:
            pct = self._pct_of_budget("tokens")
            print(f"⚠️  Token budget {pct}% used ({self.total_tokens_used:,} / {self.max_tokens:,})")

        if self.max_cost_usd and self._pct_of_budget("cost") >= self.warn_at_pct:
            pct = self._pct_of_budget("cost")
            print(f"⚠️  Cost budget {pct}% used (${self.total_cost_usd:.4f} / ${self.max_cost_usd:.4f})")

    def _pct_of_budget(self, budget_type: str) -> int:
        """Get percentage of budget used."""
        if budget_type == "tokens" and self.max_tokens:
            return int(100 * self.total_tokens_used / self.max_tokens)
        elif budget_type == "cost" and self.max_cost_usd:
            return int(100 * self.total_cost_usd / self.max_cost_usd)
        return 0

    def summary(self) -> str:
        """Get a summary of budget usage."""
        lines = ["Budget Usage Summary:"]

        if self.max_tokens:
            pct = self._pct_of_budget("tokens")
            lines.append(
                f"  Tokens: {self.total_tokens_used:,} / {self.max_tokens:,} ({pct}%)"
            )

        if self.max_cost_usd:
            pct = self._pct_of_budget("cost")
            lines.append(
                f"  Cost:   ${self.total_cost_usd:.4f} / ${self.max_cost_usd:.4f} ({pct}%)"
            )

        lines.append("\nPer-Operation Breakdown:")
        for op_name in sorted(self.operations.keys()):
            lines.append(f"  {self.operations[op_name]}")

        return "\n".join(lines)

    def remaining(self) -> dict[str, float | int | None]:
        """Get remaining budget."""
        return {
            "tokens": (self.max_tokens - self.total_tokens_used) if self.max_tokens else None,
            "cost_usd": (self.max_cost_usd - self.total_cost_usd) if self.max_cost_usd else None,
        }


# Global budget manager instance
_budget_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    """Get or initialize the global budget manager."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager()
    return _budget_manager


def set_budget_manager(manager: BudgetManager) -> None:
    """Set the global budget manager (for testing)."""
    global _budget_manager
    _budget_manager = manager
