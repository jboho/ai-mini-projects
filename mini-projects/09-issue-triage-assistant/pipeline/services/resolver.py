"""Resolution generation: similar-issue retrieval, templates, fix extraction."""

from __future__ import annotations

import re
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import RESOLUTION_TEMPLATES
from ..db.tables import IssueComment, JiraIssue
from ..models import ResolutionSuggestion

_RESOLVED = {"resolved", "closed", "fixed", "done"}
_TOKEN = re.compile(r"[a-z0-9]+")
_FIX_LANGUAGE = re.compile(
    r"\b(fixed by|resolved by|resolution:|workaround|patched|committed in|fix:)\b", re.IGNORECASE
)


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall((text or "").lower()) if len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_similar_issues(
    session: Session, summary: str, description: str = "", k: int = 5
) -> list[JiraIssue]:
    """Most similar RESOLVED issues by token overlap on summary+description."""
    query_tokens = _tokens(f"{summary} {description}")
    scored: list[tuple[float, JiraIssue]] = []
    for issue in session.scalars(select(JiraIssue)):
        if issue.status.lower() not in _RESOLVED:
            continue
        score = _jaccard(query_tokens, _tokens(f"{issue.summary} {issue.description}"))
        if score > 0:
            scored.append((score, issue))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [issue for _, issue in scored[:k]]


def extract_fix_from_comments(comments: list[IssueComment]) -> str | None:
    """Return the body of the first comment that reads like a resolution."""
    for comment in comments:
        if comment.contains_fix or _FIX_LANGUAGE.search(comment.body or ""):
            return comment.body
    return None


def generate_resolution(
    category: str,
    similar_issues: list[JiraIssue] | None = None,
    context: str = "",
    llm: Callable[[str], str] | None = None,
) -> ResolutionSuggestion:
    similar_issues = similar_issues or []
    template = RESOLUTION_TEMPLATES.get(category, RESOLUTION_TEMPLATES["other"])
    steps = [template]

    if llm is not None:
        prompt = (
            f"Give 3 concise, numbered remediation steps for a {category} issue.\n"
            f"Context: {context[:500]}\nBase guidance: {template}"
        )
        try:
            enriched = llm(prompt).strip()
            if enriched:
                steps = [line.strip() for line in enriched.splitlines() if line.strip()]
        except Exception:
            pass

    confidence = round(min(0.5 + 0.1 * len(similar_issues), 0.95), 2)
    return ResolutionSuggestion(
        title=f"Resolution for {category}",
        steps=steps,
        confidence=confidence,
        based_on_keys=[i.key for i in similar_issues],
        category=category,
    )
