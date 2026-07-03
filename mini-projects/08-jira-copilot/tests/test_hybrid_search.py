"""Hybrid search behavior: fusion combines semantic + keyword signal."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "query,expected_key",
    [
        ("application crashes on startup", "APACHE-1"),
        ("oauth login support", "APACHE-3"),
        ("dark theme for the interface", "APACHE-6"),
        ("data not syncing across devices", "APACHE-5"),
    ],
)
def test_hybrid_search_top_hit(vector_store, query, expected_key):
    results = vector_store.hybrid_search(query, limit=3)
    assert results
    assert results[0]["key"] == expected_key


def test_hybrid_exposes_component_scores(vector_store):
    results = vector_store.hybrid_search("oauth login", limit=3)
    top = results[0]
    assert "semantic_score" in top and "keyword_score" in top
    # combined score is the alpha-weighted blend of the two components
    assert top["score"] <= 1.0


def test_hybrid_keyword_rescues_exact_key(vector_store):
    """A raw issue key barely embeds but BM25 matches it exactly."""
    results = vector_store.hybrid_search("APACHE-4", limit=5)
    keys = [r["key"] for r in results]
    assert "APACHE-4" in keys


def test_hybrid_respects_filters(vector_store):
    results = vector_store.hybrid_search("bug", filters={"status": "Closed"}, limit=10)
    assert results
    assert all(r["metadata"]["status"] == "Closed" for r in results)


def test_alpha_shifts_ranking_weight(vector_store):
    """alpha=1.0 ranks by semantic only; alpha=0.0 ranks by keyword only."""
    query = "slow dashboard query performance"
    hybrid_semantic = vector_store.hybrid_search(query, limit=5, alpha=1.0)
    hybrid_keyword = vector_store.hybrid_search(query, limit=5, alpha=0.0)

    semantic_top = vector_store.semantic_search(query, limit=5)[0]["key"]
    keyword_top = vector_store.keyword_search(query, limit=5)[0]["key"]
    assert hybrid_semantic[0]["key"] == semantic_top
    assert hybrid_keyword[0]["key"] == keyword_top
