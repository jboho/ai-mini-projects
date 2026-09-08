"""Text Analyzer agent: classify + extract errors + fingerprint. Pure engine."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..db.tables import JiraIssue
from ..services.classifier import classify_issue
from ..services.fingerprinter import compute_signature, get_occurrence_count
from ..services.text_analysis import analyze_description


def analyze_issue(session: Session, issue_key: str, llm=None) -> dict:
    issue = session.get(JiraIssue, issue_key)
    if issue is None:
        return {}
    text = f"{issue.summary}\n{issue.description}"
    classification = classify_issue(issue.summary, issue.description, issue.components, llm=llm)
    analysis = analyze_description(text)
    signature = compute_signature(issue.summary, issue.description)
    return {
        "key": issue_key,
        "classification": classification.category,
        "confidence": classification.confidence,
        "method": classification.method,
        "errors": analysis.errors,
        "stack_traces": analysis.stack_traces,
        "has_stacktrace": analysis.has_stacktrace,
        "signature": signature,
        "prior_occurrences": get_occurrence_count(session, signature),
    }


def create_text_analyzer_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Text Analyzer",
        goal="Classify issues and extract errors, stack traces, and fingerprints.",
        backstory="A meticulous log analyst who turns raw bug reports into structured signals.",
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
