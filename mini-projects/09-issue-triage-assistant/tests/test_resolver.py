"""Phase 6: resolver (similar issues, templates, fix extraction)."""

from __future__ import annotations

from pipeline.ingest.enricher import enrich_issue_with_comments
from pipeline.services.resolver import (
    _jaccard,
    extract_fix_from_comments,
    find_similar_issues,
    generate_resolution,
)


def test_jaccard():
    assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert _jaccard({"a"}, {"b"}) == 0.0
    assert _jaccard(set(), {"a"}) == 0.0


def test_find_similar_returns_resolved_only(session):
    similar = find_similar_issues(
        session, "Producer fails with timeout to broker", "socket timed out"
    )
    assert similar  # KAFKA-4001 is a resolved timeout issue
    assert all(i.status.lower() in {"resolved", "closed", "fixed", "done"} for i in similar)
    assert similar[0].key == "KAFKA-4001"


def test_extract_fix_from_comments(session):
    comments = enrich_issue_with_comments(session, "KAFKA-4001")
    fix = extract_fix_from_comments(comments)
    assert fix is not None and ("timeout" in fix.lower() or "retry" in fix.lower())


def test_extract_fix_none_when_absent(session):
    comments = enrich_issue_with_comments(session, "HADOOP-3001")  # no fix comment
    assert extract_fix_from_comments(comments) is None


def test_generate_resolution_template(session):
    similar = find_similar_issues(session, "OutOfMemoryError heap", "heap space")
    suggestion = generate_resolution("memory", similar)
    assert suggestion.category == "memory"
    assert suggestion.steps and "heap" in suggestion.steps[0].lower()


def test_generate_resolution_with_llm():
    suggestion = generate_resolution(
        "network", [], context="broker timeout", llm=lambda p: "1. raise timeout\n2. add retries"
    )
    assert len(suggestion.steps) == 2
    assert "retries" in suggestion.steps[1]
