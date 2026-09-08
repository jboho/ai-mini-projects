"""Phase 1: ORM models persist, query, relate, and cascade-delete correctly."""

from __future__ import annotations

from sqlalchemy import func, select

from pipeline.config import CATEGORIES, CLASSIFICATION_TAXONOMY, IMPACT_RULES, get_settings
from pipeline.db.tables import IssueComment, IssueLink, JiraIssue, StatusTransition


def test_sample_seeds_issues(session):
    count = session.scalar(select(func.count()).select_from(JiraIssue))
    assert count == 14
    spark = session.get(JiraIssue, "SPARK-1001")
    assert spark is not None and spark.project_key == "SPARK"


def test_resolved_issues_have_fix_comments(session):
    resolved = list(session.scalars(select(JiraIssue).where(JiraIssue.status == "Resolved")))
    assert len(resolved) == 4
    fix_comments = list(
        session.scalars(select(IssueComment).where(IssueComment.contains_fix.is_(True)))
    )
    assert len(fix_comments) == 4


def test_relationships_and_links(session):
    comments = session.get(JiraIssue, "SPARK-1001").comments
    assert any(c.contains_stacktrace for c in comments)
    links = list(session.scalars(select(IssueLink).where(IssueLink.source_key == "SPARK-1002")))
    assert links[0].link_type == "duplicates" and links[0].target_key == "SPARK-1001"


def test_cascade_delete_removes_children(session):
    issue = session.get(JiraIssue, "KAFKA-4001")
    session.add(StatusTransition(issue_key="KAFKA-4001", to_value="Closed"))
    session.flush()
    session.delete(issue)
    session.flush()
    assert session.get(JiraIssue, "KAFKA-4001") is None
    remaining = session.scalars(
        select(IssueComment).where(IssueComment.issue_key == "KAFKA-4001")
    ).all()
    assert remaining == []  # cascade removed the fix comment


def test_taxonomy_and_config():
    assert len(CATEGORIES) == 13
    assert "memory" in CLASSIFICATION_TAXONOMY and "other" in CLASSIFICATION_TAXONOMY
    assert IMPACT_RULES["close_issue"] == "HIGH" and IMPACT_RULES["add_label"] == "LOW"
    assert "SPARK" in get_settings().project_keys
