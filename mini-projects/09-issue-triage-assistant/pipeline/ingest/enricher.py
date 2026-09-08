"""Assemble full issue context (comments, transitions, links) for the LLM/agents."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.tables import IssueComment, IssueLink, JiraIssue, StatusTransition


def enrich_issue_with_comments(session: Session, issue_key: str) -> list[IssueComment]:
    return list(
        session.scalars(
            select(IssueComment)
            .where(IssueComment.issue_key == issue_key)
            .order_by(IssueComment.created_at)
        )
    )


def enrich_issue_with_transitions(session: Session, issue_key: str) -> list[StatusTransition]:
    return list(
        session.scalars(
            select(StatusTransition)
            .where(StatusTransition.issue_key == issue_key)
            .order_by(StatusTransition.created_at)
        )
    )


def enrich_issue_with_links(session: Session, issue_key: str) -> list[IssueLink]:
    return list(session.scalars(select(IssueLink).where(IssueLink.source_key == issue_key)))


def build_issue_context(session: Session, issue_key: str) -> dict:
    """Full context dict for an issue: fields + comments + transitions + links."""
    issue = session.get(JiraIssue, issue_key)
    if issue is None:
        return {}
    comments = enrich_issue_with_comments(session, issue_key)
    transitions = enrich_issue_with_transitions(session, issue_key)
    links = enrich_issue_with_links(session, issue_key)
    return {
        "key": issue.key,
        "project_key": issue.project_key,
        "summary": issue.summary,
        "description": issue.description,
        "issuetype": issue.issuetype,
        "priority": issue.priority,
        "status": issue.status,
        "resolution": issue.resolution,
        "components": issue.components,
        "classification": issue.classification,
        "comments": [
            {"author": c.author, "body": c.body, "contains_fix": c.contains_fix} for c in comments
        ],
        "transitions": [
            {"from": t.from_value, "to": t.to_value, "field": t.field} for t in transitions
        ],
        "links": [{"target": link.target_key, "type": link.link_type} for link in links],
    }
