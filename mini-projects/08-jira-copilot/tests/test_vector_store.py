"""Tests for vector store pure helpers and semantic/keyword/hybrid search."""

from __future__ import annotations

from jira_copilot.services.vector_store import (
    StubEmbedder,
    build_issue_content,
    fuse_scores,
    issue_metadata,
    normalize_scores,
    tokenize,
)


def test_tokenize_lowercases_and_splits():
    assert tokenize("APACHE-3: Add OAuth!") == ["apache", "3", "add", "oauth"]
    assert tokenize("") == []


def test_build_issue_content_includes_key_title_description(session):
    from jira_copilot.services.issue_service import IssueService

    issue = IssueService(session).get_issue("APACHE-3")
    content = build_issue_content(issue)
    assert "APACHE-3" in content
    assert "Add OAuth login" in content
    assert "Google and GitHub" in content


def test_issue_metadata_is_chroma_safe(session):
    from jira_copilot.services.issue_service import IssueService

    issue = IssueService(session).get_issue("APACHE-4")  # no sprint, has component
    meta = issue_metadata(issue)
    assert meta["project"] == "APACHE"
    assert meta["sprint_id"] == -1  # None coerced to sentinel
    assert meta["components"]  # comma-joined string, not a list
    for value in meta.values():
        assert isinstance(value, (str, int, float, bool))


def test_normalize_scores():
    assert normalize_scores({}) == {}
    norm = normalize_scores({"a": 2.0, "b": 4.0, "c": 6.0})
    assert norm["a"] == 0.0 and norm["c"] == 1.0 and norm["b"] == 0.5
    assert normalize_scores({"a": 3.0, "b": 3.0}) == {"a": 1.0, "b": 1.0}


def test_fuse_scores_weights_semantic_higher():
    fused = dict(fuse_scores({"x": 1.0, "y": 0.0}, {"x": 0.0, "y": 1.0}, alpha=0.7))
    assert fused["x"] > fused["y"]
    # alpha=0.7 -> x = 0.7*1, y = 0.3*1
    assert abs(fused["x"] - 0.7) < 1e-9
    assert abs(fused["y"] - 0.3) < 1e-9


def test_fuse_scores_union_of_keys():
    fused = dict(fuse_scores({"a": 1.0}, {"b": 1.0}, alpha=0.5))
    assert set(fused) == {"a", "b"}


def test_stub_embedder_is_deterministic_and_normalized():
    emb = StubEmbedder(dim=64)
    v1 = emb.embed(["add oauth login"])[0]
    v2 = emb.embed(["add oauth login"])[0]
    assert v1 == v2
    assert abs(sum(x * x for x in v1) - 1.0) < 1e-9


def test_semantic_search_finds_relevant_issue(vector_store):
    results = vector_store.semantic_search("application crashes when starting up", limit=3)
    assert results
    assert results[0]["key"] == "APACHE-1"
    assert results[0]["score"] > results[-1]["score"] or len(results) == 1


def test_keyword_search_matches_exact_terms(vector_store):
    results = vector_store.keyword_search("oauth", limit=5)
    assert results[0]["key"] == "APACHE-3"


def test_keyword_search_respects_filters(vector_store):
    results = vector_store.keyword_search("bug", filters={"status": "Open"}, limit=10)
    assert all(r["metadata"]["status"] == "Open" for r in results)


def test_semantic_search_respects_filters(vector_store):
    results = vector_store.semantic_search("issue", filters={"type": "Story"}, limit=10)
    assert results
    assert all(r["metadata"]["type"] == "Story" for r in results)


def test_index_is_idempotent(session, vector_store):
    from sqlalchemy import select

    from jira_copilot.db.models import Issue

    before = vector_store.collection.count()
    issues = list(session.scalars(select(Issue)))
    vector_store.index_issues(issues)  # re-index same issues
    assert vector_store.collection.count() == before
