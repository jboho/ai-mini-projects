"""Reporting agent: aggregate triage statistics across issues and incidents."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.tables import Incident, JiraIssue


def build_report(session: Session, project_key: str | None = None) -> dict:
    issue_stmt = select(JiraIssue)
    if project_key:
        issue_stmt = issue_stmt.where(JiraIssue.project_key == project_key)
    issues = list(session.scalars(issue_stmt))

    by_classification: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_project: dict[str, int] = {}
    for issue in issues:
        if issue.classification:
            by_classification[issue.classification] = (
                by_classification.get(issue.classification, 0) + 1
            )
        by_status[issue.status] = by_status.get(issue.status, 0) + 1
        by_project[issue.project_key] = by_project.get(issue.project_key, 0) + 1

    incident_stmt = select(func.count()).select_from(Incident)
    open_incidents = session.scalar(
        select(func.count()).select_from(Incident).where(Incident.status == "open")
    )
    return {
        "total_issues": len(issues),
        "by_classification": dict(sorted(by_classification.items(), key=lambda kv: -kv[1])),
        "by_status": by_status,
        "by_project": by_project,
        "total_incidents": session.scalar(incident_stmt) or 0,
        "open_incidents": open_incidents or 0,
    }


def create_reporter_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Reporter",
        goal="Summarize triage activity and project health into clear reports.",
        backstory="An engineering manager who turns raw triage data into actionable summaries.",
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
