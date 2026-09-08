"""Knowledge base: CRUD, pattern search, and learning from resolved issues."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import CATEGORIES
from ..db.tables import IssueComment, JiraIssue, KnowledgeBaseEntry
from .classifier import classify_issue
from .text_analysis import extract_errors

_RESOLVED_STATUSES = {"resolved", "closed", "fixed", "done"}


def add_entry(
    session: Session,
    title: str,
    content: str,
    entry_type: str = "resolution",
    category: str = "other",
    error_patterns: str = "",
    source_issue_key: str = "",
) -> KnowledgeBaseEntry:
    entry = KnowledgeBaseEntry(
        title=title,
        content=content,
        entry_type=entry_type,
        category=category,
        error_patterns=error_patterns,
        source_issue_key=source_issue_key,
    )
    session.add(entry)
    session.flush()
    return entry


def search_by_category(session: Session, category: str) -> list[KnowledgeBaseEntry]:
    return list(
        session.scalars(select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.category == category))
    )


def search_by_error_pattern(session: Session, pattern: str) -> list[KnowledgeBaseEntry]:
    """Case-insensitive substring match against stored error patterns or content."""
    needle = f"%{pattern}%"
    return list(
        session.scalars(
            select(KnowledgeBaseEntry).where(
                KnowledgeBaseEntry.error_patterns.ilike(needle)
                | KnowledgeBaseEntry.content.ilike(needle)
            )
        )
    )


def learn_from_resolved(session: Session, issue_key: str) -> KnowledgeBaseEntry | None:
    """Extract a resolution pattern from a resolved ticket + its fix comments."""
    issue = session.get(JiraIssue, issue_key)
    if issue is None or issue.status.lower() not in _RESOLVED_STATUSES:
        return None

    fix_comments = list(
        session.scalars(
            select(IssueComment).where(
                IssueComment.issue_key == issue_key, IssueComment.contains_fix.is_(True)
            )
        )
    )
    if not fix_comments:
        return None

    category = classify_issue(issue.summary, issue.description, issue.components).category
    error_patterns = ",".join(extract_errors(f"{issue.summary}\n{issue.description}"))
    content = "\n".join(c.body for c in fix_comments)

    # Avoid duplicate KB entries for the same source issue.
    existing = session.scalar(
        select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.source_issue_key == issue_key)
    )
    if existing is not None:
        return existing

    return add_entry(
        session,
        title=f"Resolution for {category}: {issue.summary[:60]}",
        content=content,
        entry_type="resolution",
        category=category,
        error_patterns=error_patterns,
        source_issue_key=issue_key,
    )


def get_coverage_stats(session: Session) -> dict:
    """Coverage of the 13 categories by KB entries."""
    covered = {c for (c,) in session.execute(select(KnowledgeBaseEntry.category).distinct()) if c}
    covered_known = covered & set(CATEGORIES)
    total_entries = session.scalar(
        select(KnowledgeBaseEntry.id).order_by(KnowledgeBaseEntry.id.desc())
    )
    return {
        "categories_total": len(CATEGORIES),
        "categories_covered": len(covered_known),
        "coverage_pct": round(100 * len(covered_known) / len(CATEGORIES), 1),
        "uncovered": sorted(set(CATEGORIES) - covered_known),
        "has_entries": total_entries is not None,
    }
