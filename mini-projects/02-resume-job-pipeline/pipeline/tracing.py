"""Distributed tracing for Resume-Job Pipeline.

Logs generation, judgment, and correction events to Langfuse. Tracks which
resume/job pairs failed which criteria, enabling rapid diagnosis of systematic issues.

Usage:
    from pipeline.tracing import get_trace_handler
    handler = get_trace_handler()
    handler.trace_pair_generation(pair_id, resume_len, job_len)
    handler.trace_judgment(pair_id, failures)
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

    def trace_pair_generation(
        self,
        pair_id: str,
        resume_len: int,
        job_len: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a resume/job pair generation."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"generate:{pair_id}",
                metadata={
                    "pair_id": pair_id,
                    "resume_len": resume_len,
                    "job_len": job_len,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log generation trace: {e}")

    def trace_judgment(
        self,
        pair_id: str,
        failures: list[str],
        llm_model: str = "gpt-4o-mini",
        cost: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a judgment decision with failure modes."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"judge:{pair_id}",
                metadata={
                    "pair_id": pair_id,
                    "failure_count": len(failures),
                    "failures": failures,
                    "model": llm_model,
                    "cost_usd": cost,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log judgment trace: {e}")

    def trace_correction(
        self,
        pair_id: str,
        attempt: int,
        success: bool,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a correction attempt."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"correct:{pair_id}",
                metadata={
                    "pair_id": pair_id,
                    "attempt": attempt,
                    "success": success,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log correction trace: {e}")

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
