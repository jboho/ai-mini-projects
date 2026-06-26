"""Extract errors and stack traces from issue text (pure regex, offline)."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.tables import JiraIssue
from ..models import TextAnalysisResult

# Java/Scala exception or error type, optionally fully-qualified, optional message.
_JAVA_EXCEPTION = re.compile(
    r"\b(?:[a-zA-Z_][\w]*\.)*([A-Z][A-Za-z0-9_]*(?:Exception|Error))\b(?:: ?([^\n]+))?"
)
# Java stack frames: one or more consecutive "\tat ..." lines.
_JAVA_STACK = re.compile(r"(?m)^[ \t]*at[ \t]+\S.*(?:\n[ \t]*at[ \t]+\S.*)*")
# Python tracebacks.
_PY_TRACE = re.compile(r"Traceback \(most recent call last\):(?:\n.*)*?(?:\n\w+Error.*)")
# Generic log-level error lines.
_LOG_ERROR = re.compile(r"(?m)^.*\b(?:ERROR|FATAL|SEVERE)\b.*$")


def extract_errors(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for match in _JAVA_EXCEPTION.finditer(text):
        exc_type = match.group(1)
        message = (match.group(2) or "").strip()
        entry = f"{exc_type}: {message}" if message else exc_type
        if entry not in found:
            found.append(entry)
    return found


def extract_stack_traces(text: str) -> list[str]:
    if not text:
        return []
    traces = [m.group(0).strip() for m in _JAVA_STACK.finditer(text)]
    traces += [m.group(0).strip() for m in _PY_TRACE.finditer(text)]
    return traces


def _keywords_from_errors(errors: list[str]) -> list[str]:
    """Exception type names (before any colon), deduped, preserving order."""
    out: list[str] = []
    for err in errors:
        name = err.split(":")[0].strip()
        if name and name not in out:
            out.append(name)
    return out


def analyze_description(description: str) -> TextAnalysisResult:
    errors = extract_errors(description)
    traces = extract_stack_traces(description)
    return TextAnalysisResult(
        errors=errors,
        stack_traces=traces,
        keywords=_keywords_from_errors(errors),
        has_error=bool(errors),
        has_stacktrace=bool(traces),
    )


def analyze_comment(body: str) -> TextAnalysisResult:
    return analyze_description(body)


def profile_error_frequency(session: Session, project_key: str) -> dict[str, int]:
    """Count exception-type occurrences across a project's issues."""
    counts: dict[str, int] = {}
    issues = session.scalars(select(JiraIssue).where(JiraIssue.project_key == project_key))
    for issue in issues:
        for name in _keywords_from_errors(extract_errors(f"{issue.summary}\n{issue.description}")):
            counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
