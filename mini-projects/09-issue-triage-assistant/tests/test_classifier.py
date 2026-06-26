"""Phase 3: layered classifier."""

from __future__ import annotations

import pytest

from pipeline.services.classifier import (
    _component_match,
    _pattern_match,
    classify_issue,
)


@pytest.mark.parametrize(
    "summary,description,expected",
    [
        ("Executor OOM", "java.lang.OutOfMemoryError: Java heap space", "memory"),
        ("NPE in reducer", "java.lang.NullPointerException at ReduceTask", "data_processing"),
        ("Broker timeout", "java.net.SocketTimeoutException: Read timed out", "network"),
        ("DataNode write", "java.io.IOException: No space left on device", "io_storage"),
        ("Compaction stuck", "two threads deadlock acquiring locks", "concurrency"),
        ("Missing snappy", "java.lang.ClassNotFoundException: Snappy", "dependency"),
        ("Bad config", "ConfigException: quorum not set", "configuration"),
        ("Kerberos", "javax.security.sasl.AuthenticationException", "security"),
        ("Checkpoint", "java.io.NotSerializableException: UserState", "serialization"),
        ("Slow", "aggregation slow query took 45000 ms", "performance"),
        ("Build", "BUILD FAILURE cannot find symbol", "build"),
        ("Old API", "uses deprecated API removed in 1.17", "api_compatibility"),
    ],
)
def test_keyword_layer(summary, description, expected):
    result = classify_issue(summary, description)
    assert result.category == expected
    assert result.confidence >= 0.9
    assert result.method == "keyword"


def test_component_layer():
    # No keyword/pattern hit in text, but component maps to a category.
    result = classify_issue("Generic failure", "something went wrong", components="security")
    assert result.category == "security"
    assert result.method == "component"
    assert _component_match("rpc") is not None
    assert _component_match(None) is None


def test_composite_pattern_layer():
    result = _pattern_match("we saw a long gc pause on the node")
    assert result is not None and result.category == "memory" and result.method == "pattern"


def test_llm_fallback_used_only_when_unmatched():
    calls = []

    def stub_llm(prompt):
        calls.append(prompt)
        return "the category is security"

    # Matches keyword layer -> LLM not called.
    r1 = classify_issue("OOM", "OutOfMemoryError", llm=stub_llm)
    assert r1.category == "memory" and not calls

    # No rule matches -> LLM consulted.
    r2 = classify_issue("weird thing", "nothing recognizable here", llm=stub_llm)
    assert r2.category == "security" and r2.method == "llm" and calls


def test_fallback_to_other():
    result = classify_issue("mysterious", "the gizmo behaved oddly overnight")
    assert result.category == "other"
    assert result.method == "fallback"


def test_classifies_all_sample_issues(session):
    from pipeline.db.tables import JiraIssue

    issues = session.query(JiraIssue).all()
    cats = {i.key: classify_issue(i.summary, i.description, i.components).category for i in issues}
    assert cats["SPARK-1001"] == "memory"
    assert cats["KAFKA-4001"] == "network"
    assert cats["ZOOKEEPER-9001"] == "security"
    # Every issue gets a non-empty category.
    assert all(cats.values())
