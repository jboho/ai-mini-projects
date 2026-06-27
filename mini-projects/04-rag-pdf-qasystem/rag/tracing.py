"""Distributed tracing for RAG PDF QA System.

Logs retrieval quality, embedding latency, and reranker decisions. Enables
diagnosis of which pipeline components are bottlenecks or sources of errors.

Usage:
    from rag.tracing import get_trace_handler
    handler = get_trace_handler()
    handler.trace_retrieval(query_id, k, precision_at_k)
"""

from __future__ import annotations

import os
import time
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

    def trace_retrieval(
        self,
        query_id: str,
        query: str,
        k: int,
        retrieved_count: int,
        precision: float,
        latency_ms: float,
        retriever_type: str = "dense",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a retrieval operation."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"retrieve:{query_id}",
                metadata={
                    "query_id": query_id,
                    "query_len": len(query),
                    "k": k,
                    "retrieved": retrieved_count,
                    "precision_at_k": precision,
                    "latency_ms": latency_ms,
                    "retriever": retriever_type,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log retrieval trace: {e}")

    def trace_embedding(
        self,
        text_id: str,
        text_len: int,
        embedding_dim: int,
        model: str,
        latency_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an embedding operation."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"embed:{text_id}",
                metadata={
                    "text_id": text_id,
                    "text_len": text_len,
                    "embedding_dim": embedding_dim,
                    "model": model,
                    "latency_ms": latency_ms,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log embedding trace: {e}")

    def trace_generation(
        self,
        query_id: str,
        context_len: int,
        response_len: int,
        model: str,
        cost: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an LLM generation call."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.event(
                name=f"generate:{query_id}",
                metadata={
                    "query_id": query_id,
                    "context_len": context_len,
                    "response_len": response_len,
                    "model": model,
                    "cost_usd": cost,
                    **(metadata or {}),
                },
            )
        except Exception as e:
            print(f"Warning: Failed to log generation trace: {e}")

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
