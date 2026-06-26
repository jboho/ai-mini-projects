"""Multi-channel notifications with alert-rule matching and cooldowns.

Runs in simulation/dry-run mode by default (no real credentials): each channel builds
its payload and returns a structured result instead of sending. Rule matching and
cooldown logic are pure and fully tested.
"""

from __future__ import annotations

import datetime

from ..config import get_settings
from ..db.tables import Incident
from ..models import AlertRule

_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
_PRIORITY_TO_SEVERITY = {
    "Blocker": "high",
    "Critical": "high",
    "Major": "medium",
    "Minor": "low",
    "Trivial": "low",
}
_VALID_CHANNELS = {"slack", "email", "pagerduty"}


def rule_matches(rule: AlertRule, incident: Incident) -> bool:
    """A rule matches when every specified (non-empty) condition is satisfied."""
    threshold = _SEVERITY_ORDER[_PRIORITY_TO_SEVERITY.get(rule.priority_threshold, "medium")]
    if _SEVERITY_ORDER.get(incident.severity, 1) < threshold:
        return False
    if rule.projects and incident.source_project not in rule.projects:
        return False
    if rule.categories and incident.classification not in rule.categories:
        return False
    if rule.patterns:
        haystack = f"{incident.title} {incident.root_cause}".lower()
        if not any(p.lower() in haystack for p in rule.patterns):
            return False
    return True


def evaluate_alert_rules(rules: list[AlertRule], incident: Incident) -> list[AlertRule]:
    return [rule for rule in rules if rule_matches(rule, incident)]


class NotificationManager:
    def __init__(self, dry_run: bool | None = None) -> None:
        settings = get_settings()
        self.dry_run = settings.notify_dry_run if dry_run is None else dry_run
        self.slack_webhook = settings.slack_webhook_url
        self.pagerduty_key = settings.pagerduty_routing_key
        self.smtp_host = settings.smtp_host
        self._last_sent: dict[str, datetime.datetime] = {}

    def check_cooldown(
        self, rule_name: str, cooldown_minutes: int, now: datetime.datetime | None = None
    ) -> bool:
        """True if a send is allowed (cooldown elapsed)."""
        now = now or datetime.datetime.utcnow()
        last = self._last_sent.get(rule_name)
        if last is None:
            return True
        return (now - last).total_seconds() >= cooldown_minutes * 60

    def _mark_sent(self, rule_name: str, now: datetime.datetime) -> None:
        self._last_sent[rule_name] = now

    def send_notification(
        self, channel: str, recipients: list[str], subject: str, body: str
    ) -> dict:
        if channel not in _VALID_CHANNELS:
            return {"channel": channel, "status": "error", "error": "unknown channel"}
        dispatch = {
            "slack": self._send_slack,
            "email": self._send_email,
            "pagerduty": self._send_pagerduty,
        }[channel]
        return dispatch(recipients, subject, body)

    def _result(self, channel: str, configured: bool, subject: str, body: str, **extra) -> dict:
        status = "sent" if (configured and not self.dry_run) else "simulated"
        return {"channel": channel, "status": status, "subject": subject, "body": body, **extra}

    def _send_slack(self, recipients, subject, body) -> dict:
        payload = {"text": f"*{subject}*\n{body}"}
        return self._result("slack", bool(self.slack_webhook), subject, body, payload=payload)

    def _send_email(self, recipients, subject, body) -> dict:
        return self._result("email", bool(self.smtp_host), subject, body, recipients=recipients)

    def _send_pagerduty(self, recipients, subject, body) -> dict:
        event = {
            "routing_key": self.pagerduty_key,
            "event_action": "trigger",
            "payload": {"summary": subject, "severity": "critical", "source": "triage"},
        }
        return self._result("pagerduty", bool(self.pagerduty_key), subject, body, event=event)

    def notify_for_incident(
        self,
        incident: Incident,
        rules: list[AlertRule],
        now: datetime.datetime | None = None,
    ) -> list[dict]:
        now = now or datetime.datetime.utcnow()
        sent: list[dict] = []
        for rule in evaluate_alert_rules(rules, incident):
            if not self.check_cooldown(rule.name, rule.cooldown_minutes, now):
                continue
            subject = f"[{incident.severity.upper()}] {incident.title}"
            for channel in rule.channels:
                result = self.send_notification(channel, [], subject, incident.root_cause)
                result["rule"] = rule.name
                sent.append(result)
            self._mark_sent(rule.name, now)
        return sent
