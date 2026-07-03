"""Budget management for Embedding Finetuning.

Tracks training costs, validation metrics, and early stopping to prevent
overfitting or wasted compute.

Usage:
    from pipeline.budgets import get_budget_manager

    budget = get_budget_manager()
    budget.record_training_step(loss=0.15, val_auc=0.92)
    if budget.should_stop():
        print("Early stopping: validation AUC plateaued")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


class BudgetExceeded(Exception):
    """Raised when a budget limit is exceeded."""
    pass


@dataclass
class TrainingMetrics:
    """Metrics for training progress."""
    epoch: int = 0
    loss: float = 0.0
    val_auc: float = 0.0
    val_fpr: float = 1.0
    best_val_auc: float = 0.0
    epochs_without_improvement: int = 0
    history: list[dict] = field(default_factory=list)


class BudgetManager:
    """Manages training budgets and early stopping."""

    def __init__(
        self,
        max_epochs: Optional[int] = None,
        max_compute_hours: Optional[float] = None,
        target_fpr: float = 0.010,
        patience: int = 3,
    ):
        """Initialize budget manager.

        Args:
            max_epochs: Max training epochs
            max_compute_hours: Max GPU hours budget
            target_fpr: Target false positive rate
            patience: Early stopping patience (epochs without improvement)
        """
        self.max_epochs = max_epochs or int(os.getenv("BUDGET_MAX_EPOCHS", "0")) or None
        self.max_compute_hours = max_compute_hours or float(os.getenv("BUDGET_MAX_COMPUTE_HOURS", "0")) or None
        self.target_fpr = target_fpr
        self.patience = patience

        self.metrics = TrainingMetrics()
        self.compute_hours_used = 0.0

    def record_training_step(
        self,
        loss: float,
        val_auc: float,
        val_fpr: float,
        compute_hours: float = 0.5,
    ) -> None:
        """Record a training step.

        Args:
            loss: Training loss
            val_auc: Validation AUC
            val_fpr: Validation false positive rate
            compute_hours: Compute hours for this epoch
        """
        if self.max_epochs and self.metrics.epoch >= self.max_epochs:
            raise BudgetExceeded(
                f"Max epochs exceeded: {self.metrics.epoch} >= {self.max_epochs}"
            )

        if self.max_compute_hours and (self.compute_hours_used + compute_hours) > self.max_compute_hours:
            raise BudgetExceeded(
                f"Compute budget exceeded: {self.compute_hours_used + compute_hours:.1f} > {self.max_compute_hours:.1f} hours"
            )

        # Update metrics
        self.metrics.epoch += 1
        self.metrics.loss = loss
        self.metrics.val_auc = val_auc
        self.metrics.val_fpr = val_fpr
        self.compute_hours_used += compute_hours

        # Track best AUC for early stopping
        if val_auc > self.metrics.best_val_auc:
            self.metrics.best_val_auc = val_auc
            self.metrics.epochs_without_improvement = 0
        else:
            self.metrics.epochs_without_improvement += 1

        # Log history
        self.metrics.history.append({
            "epoch": self.metrics.epoch,
            "loss": loss,
            "val_auc": val_auc,
            "val_fpr": val_fpr,
            "compute_hours": compute_hours,
        })

        # Warn if FPR is high
        if val_fpr > self.target_fpr:
            print(f"⚠️  FPR {val_fpr:.3f} > target {self.target_fpr:.3f}")

    def should_stop(self) -> bool:
        """Check if training should stop (early stopping)."""
        return self.metrics.epochs_without_improvement >= self.patience

    def summary(self) -> str:
        """Get training summary."""
        lines = ["Training Summary:"]
        lines.append(f"  Epochs: {self.metrics.epoch}")
        lines.append(f"  Loss: {self.metrics.loss:.4f}")
        lines.append(f"  Val AUC: {self.metrics.val_auc:.4f} (best: {self.metrics.best_val_auc:.4f})")
        lines.append(f"  Val FPR: {self.metrics.val_fpr:.4f} (target: {self.target_fpr:.4f})")
        lines.append(f"  Compute: {self.compute_hours_used:.1f} hours")

        if self.max_compute_hours:
            pct = int(100 * self.compute_hours_used / self.max_compute_hours)
            lines.append(f"  Budget: {self.compute_hours_used:.1f} / {self.max_compute_hours:.1f} hours ({pct}%)")

        if self.should_stop():
            lines.append(f"  Status: Early stopping ({self.patience} epochs without improvement)")

        return "\n".join(lines)


_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    """Get or initialize the global budget manager."""
    global _manager
    if _manager is None:
        _manager = BudgetManager()
    return _manager
