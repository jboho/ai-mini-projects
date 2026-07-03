"""Tests for calendar slot generation and links."""

from __future__ import annotations

from datetime import datetime

from core.calendar import calendar_link, generate_slots


def test_generate_slots_weekdays_only():
    # start on a Friday -> next slots skip the weekend
    friday = datetime(2025, 1, 3, 9, 0)
    slots = generate_slots(start=friday, count=3)
    assert len(slots) == 3
    assert "Monday" in slots[0]  # Jan 6 2025 is a Monday
    assert all("Saturday" not in s and "Sunday" not in s for s in slots)


def test_calendar_link():
    assert (
        calendar_link("vince.kaminski@enron.com") == "https://cal.example.com/vince-kaminski/30min"
    )
