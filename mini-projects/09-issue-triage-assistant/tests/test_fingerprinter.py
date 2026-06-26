"""Phase 3: fingerprint normalization + duplicate detection."""

from __future__ import annotations

from pipeline.db.tables import JiraIssue
from pipeline.services.fingerprinter import (
    _normalize_text,
    compute_signature,
    get_occurrence_count,
    is_duplicate,
    register_signature,
)


def test_normalize_strips_volatile_tokens():
    a = _normalize_text("2024-01-03 10:22:41 error at Foo.java:142 addr 0xABCD id 5")
    b = _normalize_text("2024-09-09 23:11:07 error at Foo.java:377 addr 0x1234 id 9")
    assert a == b  # timestamps, line numbers, hex, numbers normalized away


def test_same_bug_same_signature(session):
    a = session.get(JiraIssue, "SPARK-1001")
    b = session.get(JiraIssue, "SPARK-1002")
    c = session.get(JiraIssue, "FLINK-2001")
    sig_a = compute_signature(a.summary, a.description)
    sig_b = compute_signature(b.summary, b.description)
    sig_c = compute_signature(c.summary, c.description)
    assert sig_a == sig_b == sig_c  # 3 reports of the same OOM collapse


def test_different_bug_different_signature(session):
    oom = session.get(JiraIssue, "SPARK-1001")
    npe = session.get(JiraIssue, "HADOOP-3001")
    assert compute_signature(oom.summary, oom.description) != compute_signature(
        npe.summary, npe.description
    )


def test_register_and_count(session):
    sig = compute_signature("OutOfMemoryError", "heap space")
    assert is_duplicate(session, sig) is None
    register_signature(session, sig, "SPARK-1001", classification="memory")
    assert is_duplicate(session, sig) is not None
    assert get_occurrence_count(session, sig) == 1

    register_signature(session, sig, "SPARK-1002", classification="memory")
    assert get_occurrence_count(session, sig) == 2  # recurring


def test_register_fills_known_cause(session):
    sig = compute_signature("ClassNotFound", "snappy missing")
    register_signature(session, sig, "C-1")
    row = register_signature(session, sig, "C-2", known_cause="add snappy to classpath")
    assert row.known_cause == "add snappy to classpath"
    assert row.occurrence_count == 2
