"""Issue Monitor agent: detect new/active issues. Engine is pure + offline-testable."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.tables import JiraIssue
from ..ingest.enricher import build_issue_context

_RESOLVED = {"resolved", "closed", "fixed", "done"}


def scan_new_issues(
    session: Session,
    project_key: str | None = None,
    since_hours: int | None = None,
    reference_time: datetime.datetime | None = None,
) -> list[JiraIssue]:
    """Active (unresolved) issues, optionally filtered by project and recency."""
    stmt = select(JiraIssue)
    if project_key:
        stmt = stmt.where(JiraIssue.project_key == project_key)
    issues = [i for i in session.scalars(stmt) if i.status.lower() not in _RESOLVED]
    if since_hours is not None and reference_time is not None:
        cutoff = reference_time - datetime.timedelta(hours=since_hours)
        issues = [i for i in issues if i.created_at and i.created_at >= cutoff]
    return issues


def fetch_issue_details(session: Session, issue_key: str) -> dict:
    return build_issue_context(session, issue_key)


def create_monitor_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Issue Monitor",
        goal="Detect new and active bug reports across Apache projects.",
        backstory="A senior SRE who continuously watches issue trackers for fresh failures.",
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
