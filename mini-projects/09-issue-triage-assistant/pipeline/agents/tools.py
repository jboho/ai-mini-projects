"""CrewAI tool wrappers bound (via closure) to a live DB session."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session


def build_tools(session: Session) -> list:
    from crewai.tools import tool

    from .issue_monitor import fetch_issue_details, scan_new_issues
    from .reporter import build_report
    from .resolution_advisor import advise
    from .text_analyzer import analyze_issue

    @tool("scan_new_issues")
    def scan_new_issues_tool(project_key: str = "") -> str:
        """List active (unresolved) issue keys, optionally filtered by project."""
        issues = scan_new_issues(session, project_key=project_key or None)
        return json.dumps([i.key for i in issues])

    @tool("get_issue_context")
    def get_issue_context_tool(issue_key: str) -> str:
        """Get full context (fields, comments, links) for an issue key as JSON."""
        return json.dumps(fetch_issue_details(session, issue_key))

    @tool("analyze_issue")
    def analyze_issue_tool(issue_key: str) -> str:
        """Classify an issue and extract its errors, stack traces, and fingerprint."""
        return json.dumps(analyze_issue(session, issue_key))

    @tool("suggest_resolution")
    def suggest_resolution_tool(issue_key: str) -> str:
        """Suggest a resolution for an issue from the KB and similar issues."""
        return advise(session, issue_key).model_dump_json()

    @tool("triage_report")
    def triage_report_tool(project_key: str = "") -> str:
        """Aggregate triage statistics, optionally for one project."""
        return json.dumps(build_report(session, project_key or None))

    return [
        scan_new_issues_tool,
        get_issue_context_tool,
        analyze_issue_tool,
        suggest_resolution_tool,
        triage_report_tool,
    ]
