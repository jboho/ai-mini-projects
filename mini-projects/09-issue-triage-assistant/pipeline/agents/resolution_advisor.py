"""Resolution Advisor agent: suggest a fix from KB entries, similar issues, templates."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import RESOLUTION_TEMPLATES
from ..db.tables import JiraIssue
from ..models import ResolutionSuggestion
from ..services.classifier import classify_issue
from ..services.knowledge_base import search_by_category

_RESOLVED = {"resolved", "closed", "fixed", "done"}


def find_similar_resolved(
    session: Session, category: str, exclude_key: str = "", k: int = 3
) -> list[JiraIssue]:
    """Resolved issues whose classification matches -- a cheap, dependency-free similarity."""
    out: list[JiraIssue] = []
    for issue in session.scalars(select(JiraIssue)):
        if issue.key == exclude_key or issue.status.lower() not in _RESOLVED:
            continue
        if classify_issue(issue.summary, issue.description, issue.components).category == category:
            out.append(issue)
        if len(out) >= k:
            break
    return out


def advise(
    session: Session, issue_key: str, llm: Callable[[str], str] | None = None
) -> ResolutionSuggestion:
    issue = session.get(JiraIssue, issue_key)
    if issue is None:
        return ResolutionSuggestion(title="No such issue", category="other")

    category = (
        issue.classification
        or classify_issue(issue.summary, issue.description, issue.components).category
    )
    template = RESOLUTION_TEMPLATES.get(category, RESOLUTION_TEMPLATES["other"])

    kb_entries = search_by_category(session, category)
    similar = find_similar_resolved(session, category, exclude_key=issue_key)

    steps = [template]
    based_on: list[str] = []
    for entry in kb_entries[:3]:
        steps.append(f"From KB ({entry.title}): {entry.content[:160]}")
        if entry.source_issue_key:
            based_on.append(entry.source_issue_key)
    for sim in similar:
        based_on.append(sim.key)

    confidence = 0.5 + 0.1 * min(len(kb_entries) + len(similar), 4)
    return ResolutionSuggestion(
        title=f"Suggested resolution for {category} in {issue_key}",
        steps=steps,
        confidence=round(min(confidence, 0.95), 2),
        based_on_keys=list(dict.fromkeys(based_on)),
        category=category,
    )


def create_resolution_advisor_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Resolution Advisor",
        goal="Recommend concrete fixes drawing on the knowledge base and similar issues.",
        backstory="A staff engineer who has seen these failures before and knows the fixes.",
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
