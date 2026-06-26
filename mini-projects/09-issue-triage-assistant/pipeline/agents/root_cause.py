"""Root Cause Analyst agent: diagnose why an issue failed.

Deterministic offline diagnosis from extracted signals; richer narrative when an LLM
is injected. Returns a structured RootCauseResult either way.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from ..config import RESOLUTION_TEMPLATES
from ..db.tables import JiraIssue
from ..models import RootCauseResult
from .text_analyzer import analyze_issue


def diagnose(
    session: Session, issue_key: str, llm: Callable[[str], str] | None = None
) -> RootCauseResult:
    issue = session.get(JiraIssue, issue_key)
    if issue is None:
        return RootCauseResult()

    analysis = analyze_issue(session, issue_key)
    category = analysis["classification"]
    primary_error = analysis["errors"][0] if analysis["errors"] else issue.summary
    evidence = (
        analysis["stack_traces"][0][:300] if analysis["stack_traces"] else issue.description[:200]
    )
    template = RESOLUTION_TEMPLATES.get(category, RESOLUTION_TEMPLATES["other"])

    summary = f"{category.replace('_', ' ').title()} failure: {primary_error}"
    why = template
    if llm is not None:
        prompt = (
            "You are a root-cause analyst. In 2 sentences, explain the likely root cause.\n"
            f"Issue: {issue.summary}\nError: {primary_error}\nCategory: {category}\n"
            f"Context: {issue.description[:500]}"
        )
        try:
            why = llm(prompt).strip() or template
        except Exception:
            why = template

    return RootCauseResult(
        summary=summary,
        what_failed=primary_error,
        why_failed=why,
        evidence=evidence,
        confidence=round(analysis["confidence"], 2),
        suggested_steps=[template],
    )


def create_root_cause_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Root Cause Analyst",
        goal="Diagnose the underlying cause of a failure from its signals and context.",
        backstory="A debugging veteran who reasons from stack traces to root causes.",
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
