"""Distributed tracing for Embedding Finetuning.

Logs embedding quality, match predictions, and false positives. Enables
root-cause analysis of why embeddings misclassify certain profile pairs.

Usage:
    from pipeline.tracing import get_trace_handler
    handler = get_trace_handler()
    handler.trace_embedding_quality(pair_id, fpr, auc)
"""

from __future__ import annotations

import os
from typing import Any, Optional

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False


class TraceHandler:
    """Wrapper for optional Langfuse integration."""

    def __init__(self):
        self.enabled = LANGFUSE_AVAILABLE and bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
        self.client: Optional[Langfuse] = None

        if self.enabled:
            try:
                self.client = Langfuse(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                )
            except Exception as e:
                print(f"Warning: Langfuse initialization failed: {e}. Tracing disabled.")
                self.enabled = False

    def trace_embedding_quality(
        self,
        model_version: str,
        false_positive_rate: float,
        auc_roc: float,
        category: str = "overall",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log embedding model quality."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"embed_quality:{category}",
                metadata={
                    "model": model_version,
                    "fpr": false_positive_rate,
                    "auc_roc": auc_roc,
                    "category": category,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log embedding quality trace: {e}")

    def trace_prediction(
        self,
        pair_id: str,
        predicted_match: bool,
        confidence: float,
        category: str = "overall",
        correct: Optional[bool] = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a match prediction."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"predict:{pair_id}",
                metadata={
                    "pair_id": pair_id,
                    "predicted_match": predicted_match,
                    "confidence": confidence,
                    "category": category,
                    **({"correct": correct} if correct is not None else {}),
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log prediction trace: {e}")

    def trace_finetuning_step(
        self,
        epoch: int,
        loss: float,
        validation_auc: float,
        learning_rate: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a finetuning step."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"finetune:epoch_{epoch}",
                metadata={
                    "epoch": epoch,
                    "loss": loss,
                    "val_auc": validation_auc,
                    "learning_rate": learning_rate,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log finetuning trace: {e}")

    def flush(self) -> None:
        """Flush pending traces."""
        if self.enabled and self.client:
            try:
                self.client.flush()
            except Exception as e:
                print(f"Warning: Failed to flush traces: {e}")


_handler: Optional[TraceHandler] = None


def get_trace_handler() -> TraceHandler:
    """Get or initialize the trace handler."""
    global _handler
    if _handler is None:
        _handler = TraceHandler()
    return _handler
