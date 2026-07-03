"""FallbackAgent: on low confidence, produce a calendar booking message (core)."""

from __future__ import annotations

from core.calendar import build_fallback
from core.models import FallbackResponse


class FallbackAgent:
    role = "Scheduling Fallback"

    def build(self, trigger_reason: str, query: str, employee: str) -> FallbackResponse:
        context = f"The user asked: {query!r}. The clone could not answer confidently."
        return build_fallback(trigger_reason, context, employee)
