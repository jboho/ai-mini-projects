"""Tests for fallback-response construction."""

from __future__ import annotations

from datetime import datetime

from core.calendar import build_fallback


def test_build_fallback():
    fb = build_fallback(
        trigger_reason="low confidence (0.42)",
        context_summary="User asked about hedging strategy.",
        employee="vince.kaminski@enron.com",
        start=datetime(2025, 1, 6, 9, 0),
    )
    assert fb.trigger_reason.startswith("low confidence")
    assert fb.calendar_link.endswith("/30min")
    assert len(fb.available_slots) == 3
    assert "vince-kaminski" in fb.calendar_link
