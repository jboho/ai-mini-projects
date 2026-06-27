"""Distributed tracing for Issue Triage Assistant.

Integrates Langfuse for observability. When LANGFUSE_PUBLIC_KEY is set, traces are
sent to Langfuse; otherwise, tracing is a no-op.

Usage:
    from pipeline.tracing import trace_context, get_trace_handler

    with trace_context(name="classify_issue", metadata={"issue_id": "ABC-123"}):
        # code to trace
"""

from __future__ import annotations

import os
from contextlib import contextmanager
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

    def trace_llm_call(
        self,
        name: str,
        model: str,
        prompt: str,
        completion: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an LLM call to Langfuse."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.generation(
                name=name,
                model=model,
                input={"prompt": prompt},
                output=completion,
                usage={
                    "input": tokens_in,
                    "output": tokens_out,
                },
                metadata=metadata or {},
                cost_usd=cost,
            )
        except Exception as e:
            print(f"Warning: Failed to log LLM trace: {e}")

    def trace_classifier(
        self,
        issue_id: str,
        category: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a classification decision."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"classify:{issue_id}",
                metadata={
                    "issue_id": issue_id,
                    "category": category,
                    "confidence": confidence,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log classifier trace: {e}")

    def trace_workflow_transition(
        self,
        issue_id: str,
        from_state: str,
        to_state: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an approval workflow state change."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"workflow:{from_state}→{to_state}",
                metadata={
                    "issue_id": issue_id,
                    "from_state": from_state,
                    "to_state": to_state,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log workflow trace: {e}")

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


@contextmanager
def trace_context(name: str, metadata: dict[str, Any] | None = None):
    """Context manager for tracing a span."""
    handler = get_trace_handler()
    # Langfuse doesn't have a simple context manager, so this is a placeholder.
    # In production, you'd use the trace context from the SDK if available.
    try:
        yield
    finally:
        if metadata:
            handler.trace_llm_call(
                name=name,
                model="unknown",
                prompt="",
                completion="",
                tokens_in=0,
                tokens_out=0,
                cost=0.0,
                metadata=metadata,
            )
