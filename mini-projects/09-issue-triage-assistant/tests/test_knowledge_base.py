"""Phase 4: knowledge base CRUD, search, and learning from resolved issues."""

from __future__ import annotations

from pipeline.services.knowledge_base import (
    add_entry,
    get_coverage_stats,
    learn_from_resolved,
    search_by_category,
    search_by_error_pattern,
)


def test_add_and_search_by_category(session):
    add_entry(session, "Heap tuning", "increase executor memory", category="memory")
    add_entry(session, "GC tuning", "use G1GC", category="memory")
    add_entry(session, "Retry", "add backoff", category="network")
    assert len(search_by_category(session, "memory")) == 2
    assert len(search_by_category(session, "network")) == 1
    assert search_by_category(session, "security") == []


def test_search_by_error_pattern(session):
    add_entry(
        session,
        "OOM fix",
        "raise spark.executor.memory",
        category="memory",
        error_patterns="OutOfMemoryError",
    )
    assert search_by_error_pattern(session, "OutOfMemory")
    assert search_by_error_pattern(session, "executor.memory")  # matches content
    assert search_by_error_pattern(session, "nonexistent") == []


def test_learn_from_resolved(session):
    entry = learn_from_resolved(session, "KAFKA-4001")  # resolved, has fix comment
    assert entry is not None
    assert entry.category == "network"
    assert entry.source_issue_key == "KAFKA-4001"
    assert "timeout" in entry.content.lower() or "retry" in entry.content.lower()


def test_learn_from_resolved_skips_unresolved(session):
    assert learn_from_resolved(session, "SPARK-1001") is None  # still Open
    assert learn_from_resolved(session, "NOPE-1") is None


def test_learn_is_idempotent(session):
    a = learn_from_resolved(session, "CASSANDRA-7001")
    b = learn_from_resolved(session, "CASSANDRA-7001")
    assert a is not None and a.id == b.id  # no duplicate KB entry


def test_coverage_stats(session):
    stats = get_coverage_stats(session)
    assert stats["categories_total"] == 13
    assert stats["categories_covered"] == 0  # empty KB initially

    for key in ("KAFKA-4001", "CASSANDRA-7001", "ZOOKEEPER-9001", "SPARK-1003"):
        learn_from_resolved(session, key)
    stats2 = get_coverage_stats(session)
    assert stats2["categories_covered"] >= 3
    assert 0 < stats2["coverage_pct"] <= 100
