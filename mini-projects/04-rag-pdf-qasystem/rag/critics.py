"""Quality critics for RAG Pipeline.

Validates retrieval results and generated responses before returning to user.

Usage:
    from rag.critics import RetrievalCritic, ResponseCritic

    retrieval_critic = RetrievalCritic()
    verdict = retrieval_critic.evaluate(retrieved_chunks, precision_at_1)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CriticVerdict:
    """Result of evaluation."""
    pass_: bool
    severity: Severity
    reason: str
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        status = "✓ PASS" if self.pass_ else f"✗ {self.severity.value.upper()}"
        msg = f"{status}: {self.reason}"
        if self.suggestion:
            msg += f" → {self.suggestion}"
        return msg


class RetrievalCritic:
    """Validates retrieval results."""

    def evaluate(
        self,
        retrieved_count: int,
        precision_at_1: float,
        requested_k: int = 10,
    ) -> CriticVerdict:
        """Evaluate retrieval quality.

        Args:
            retrieved_count: Number of chunks retrieved
            precision_at_1: Whether top result was relevant (0 or 1)
            requested_k: Number of results requested

        Returns:
            CriticVerdict
        """
        if retrieved_count == 0:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason="No chunks retrieved",
                suggestion="Check if corpus is empty or query too specific",
            )

        if retrieved_count < requested_k:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason=f"Fewer chunks returned ({retrieved_count}) than requested ({requested_k})",
                suggestion="Corpus may be small or sparse",
            )

        if precision_at_1 == 0:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason="Top retrieval was not relevant (precision@1 = 0)",
                suggestion="Low-quality retrieval; consider reranking or different embedder",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid retrieval: {retrieved_count} chunks, precision@1 = {precision_at_1}",
        )


class ResponseCritic:
    """Validates LLM responses."""

    MIN_LEN = 20
    MAX_LEN = 5000

    def evaluate(self, response: str, cited_context: bool = False) -> CriticVerdict:
        """Evaluate a generated response.

        Args:
            response: Generated text
            cited_context: Whether response cited retrieved context

        Returns:
            CriticVerdict
        """
        if not isinstance(response, str):
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Response must be string, got {type(response).__name__}",
            )

        if len(response) < self.MIN_LEN:
            return CriticVerdict(
                pass_=False,
                severity=Severity.WARNING,
                reason=f"Response too short ({len(response)} chars)",
                suggestion=f"Expect {self.MIN_LEN}+ chars for complete answer",
            )

        if len(response) > self.MAX_LEN:
            return CriticVerdict(
                pass_=False,
                severity=Severity.WARNING,
                reason=f"Response unusually long ({len(response)} chars)",
                suggestion=f"Typical responses are <{self.MAX_LEN} chars",
            )

        if not cited_context:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason="Response did not cite source context",
                suggestion="Consider adding '[Source: ...]' citations for transparency",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid response: {len(response)} chars, cited context",
        )
