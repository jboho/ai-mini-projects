"""Phase 7: multi-channel notifications (simulation mode)."""

from __future__ import annotations

import datetime

from pipeline.db.tables import Incident
from pipeline.models import AlertRule
from pipeline.services.notifier import (
    NotificationManager,
    evaluate_alert_rules,
    rule_matches,
)


def _incident(**kw) -> Incident:
    base = dict(
        title="OOM in executor",
        severity="high",
        source_project="SPARK",
        classification="memory",
        root_cause="OutOfMemoryError: Java heap space",
    )
    base.update(kw)
    return Incident(**base)


# --- rule matching ---------------------------------------------------------


def test_empty_rule_matches_any_incident():
    rule = AlertRule(name="catch-all", priority_threshold="Trivial")
    assert rule_matches(rule, _incident(severity="low"))


def test_severity_threshold_blocks_low_severity():
    rule = AlertRule(name="crit", priority_threshold="Critical")  # -> high
    assert rule_matches(rule, _incident(severity="high"))
    assert not rule_matches(rule, _incident(severity="medium"))
    assert not rule_matches(rule, _incident(severity="low"))


def test_project_filter():
    rule = AlertRule(name="spark-only", priority_threshold="Trivial", projects=["SPARK"])
    assert rule_matches(rule, _incident(source_project="SPARK"))
    assert not rule_matches(rule, _incident(source_project="KAFKA"))


def test_category_filter():
    rule = AlertRule(name="mem", priority_threshold="Trivial", categories=["memory"])
    assert rule_matches(rule, _incident(classification="memory"))
    assert not rule_matches(rule, _incident(classification="network"))


def test_pattern_filter_matches_title_or_root_cause():
    rule = AlertRule(name="oom", priority_threshold="Trivial", patterns=["heap space"])
    assert rule_matches(rule, _incident())  # root_cause contains it
    assert not rule_matches(rule, _incident(root_cause="connection reset", title="timeout"))


def test_evaluate_alert_rules_returns_only_matches():
    incident = _incident(source_project="SPARK", severity="high")
    rules = [
        AlertRule(name="spark", priority_threshold="Trivial", projects=["SPARK"]),
        AlertRule(name="kafka", priority_threshold="Trivial", projects=["KAFKA"]),
    ]
    matched = evaluate_alert_rules(rules, incident)
    assert [r.name for r in matched] == ["spark"]


# --- cooldown --------------------------------------------------------------


def test_cooldown_first_send_allowed_then_blocked_then_elapsed():
    mgr = NotificationManager(dry_run=True)
    t0 = datetime.datetime(2026, 1, 1, 12, 0, 0)
    assert mgr.check_cooldown("r", 30, now=t0)
    mgr._mark_sent("r", t0)
    assert not mgr.check_cooldown("r", 30, now=t0 + datetime.timedelta(minutes=10))
    assert mgr.check_cooldown("r", 30, now=t0 + datetime.timedelta(minutes=31))


# --- dispatch (simulation) -------------------------------------------------


def test_send_notification_simulated_for_each_channel():
    mgr = NotificationManager(dry_run=True)
    for channel in ("slack", "email", "pagerduty"):
        result = mgr.send_notification(channel, ["a@b.c"], "subj", "body")
        assert result["channel"] == channel
        assert result["status"] == "simulated"


def test_unknown_channel_returns_error():
    mgr = NotificationManager(dry_run=True)
    result = mgr.send_notification("carrier-pigeon", [], "s", "b")
    assert result["status"] == "error"


def test_notify_for_incident_dispatches_and_respects_cooldown():
    mgr = NotificationManager(dry_run=True)
    incident = _incident()
    rule = AlertRule(
        name="oom-alert",
        priority_threshold="Critical",
        channels=["slack", "pagerduty"],
        cooldown_minutes=60,
    )
    t0 = datetime.datetime(2026, 1, 1, 12, 0, 0)

    first = mgr.notify_for_incident(incident, [rule], now=t0)
    assert [r["channel"] for r in first] == ["slack", "pagerduty"]
    assert all(r["rule"] == "oom-alert" and r["status"] == "simulated" for r in first)

    within = mgr.notify_for_incident(incident, [rule], now=t0 + datetime.timedelta(minutes=5))
    assert within == []

    after = mgr.notify_for_incident(incident, [rule], now=t0 + datetime.timedelta(minutes=61))
    assert len(after) == 2
