"""Calendar slot generation and fallback-response construction."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import FallbackResponse


def generate_slots(start: datetime | None = None, count: int = 3, hour: int = 10) -> list[str]:
    """Return ``count`` upcoming weekday slots formatted for display."""
    current = start or datetime.now()
    slots: list[str] = []
    while len(slots) < count:
        current = current + timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            slots.append(current.replace(hour=hour, minute=0).strftime("%A %b %d, %I:%M %p"))
    return slots


def calendar_link(employee: str) -> str:
    handle = employee.split("@")[0].replace(".", "-") or "clone"
    return f"https://cal.example.com/{handle}/30min"


def build_fallback(
    trigger_reason: str,
    context_summary: str,
    employee: str,
    start: datetime | None = None,
) -> FallbackResponse:
    return FallbackResponse(
        trigger_reason=trigger_reason,
        context_summary=context_summary,
        calendar_link=calendar_link(employee),
        available_slots=generate_slots(start),
    )
