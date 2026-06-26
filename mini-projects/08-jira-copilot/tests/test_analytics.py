"""Tests for the analytics / feedback service."""

from __future__ import annotations

import pytest

from jira_copilot.schemas.responses import Suggestion
from jira_copilot.services.analytics import Analytics, acceptance_rates


def _sug(stype: str, key: str = "APACHE-1", suggested: str = "x", conf: float = 0.5) -> Suggestion:
    return Suggestion(type=stype, issue_key=key, suggested=suggested, confidence=conf)


def test_acceptance_rates_pure():
    rows = [("priority", True), ("priority", False), ("estimate", True)]
    rates = acceptance_rates(rows)
    assert rates["priority"] == {"total": 2, "accepted": 1, "rate": 0.5}
    assert rates["estimate"] == {"total": 1, "accepted": 1, "rate": 1.0}
    assert acceptance_rates([]) == {}


def test_log_and_history(session):
    an = Analytics(session)
    sid = an.log_suggestion(_sug("priority", "APACHE-1", "Critical", 0.8))
    an.log_suggestion(_sug("estimate", "APACHE-2", "5", 0.6))
    assert isinstance(sid, int)

    history = an.get_suggestion_history()
    assert len(history) == 2
    only_p = an.get_suggestion_history(type="priority")
    assert len(only_p) == 1 and only_p[0]["suggested"] == "Critical"
    by_issue = an.get_suggestion_history(issue_key="APACHE-2")
    assert len(by_issue) == 1 and by_issue[0]["type"] == "estimate"


def test_record_feedback_and_rates(session):
    an = Analytics(session)
    s1 = an.log_suggestion(_sug("priority"))
    s2 = an.log_suggestion(_sug("priority"))
    s3 = an.log_suggestion(_sug("estimate"))
    an.record_feedback(s1, accepted=True)
    an.record_feedback(s2, accepted=False, reason="wrong")
    an.record_feedback(s3, accepted=True)

    by_type = an.get_acceptance_rates(by_type=True)
    assert by_type["priority"]["rate"] == 0.5
    assert by_type["estimate"]["rate"] == 1.0

    overall = an.get_acceptance_rates(by_type=False)
    assert overall["overall"]["total"] == 3
    assert overall["overall"]["accepted"] == 2


def test_record_feedback_unknown_suggestion_raises(session):
    an = Analytics(session)
    with pytest.raises(ValueError):
        an.record_feedback(999, accepted=True)


def test_quality_metrics(session):
    an = Analytics(session)
    s1 = an.log_suggestion(_sug("priority", conf=0.8))
    an.log_suggestion(_sug("estimate", conf=0.4))
    an.record_feedback(s1, accepted=True)

    metrics = an.get_quality_metrics()
    assert metrics["total_suggestions"] == 2
    assert metrics["suggestions_by_type"] == {"priority": 1, "estimate": 1}
    assert metrics["average_confidence"] == 0.6
    assert metrics["total_feedback"] == 1
    assert metrics["overall_acceptance_rate"] == 1.0
