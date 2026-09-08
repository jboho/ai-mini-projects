"""Phase 5: agent engines + TriageCrew orchestration (offline)."""

from __future__ import annotations

from sqlalchemy import select

from pipeline.agents.crew import TriageCrew
from pipeline.agents.issue_monitor import scan_new_issues
from pipeline.agents.reporter import build_report
from pipeline.agents.resolution_advisor import advise, find_similar_resolved
from pipeline.agents.root_cause import diagnose
from pipeline.agents.text_analyzer import analyze_issue
from pipeline.db.tables import Incident, JiraIssue, Resolution


def test_scan_new_issues_excludes_resolved(session):
    active = scan_new_issues(session)
    keys = {i.key for i in active}
    assert "SPARK-1001" in keys  # Open
    assert "KAFKA-4001" not in keys  # Resolved
    spark_only = scan_new_issues(session, project_key="SPARK")
    assert all(i.project_key == "SPARK" for i in spark_only)


def test_analyze_issue(session):
    result = analyze_issue(session, "SPARK-1001")
    assert result["classification"] == "memory"
    assert any("OutOfMemoryError" in e for e in result["errors"])
    assert result["has_stacktrace"]
    assert len(result["signature"]) == 16


def test_diagnose_offline(session):
    rc = diagnose(session, "SPARK-1001")
    assert "Memory" in rc.summary
    assert rc.what_failed and rc.suggested_steps
    assert rc.confidence > 0


def test_diagnose_with_stub_llm(session):
    rc = diagnose(session, "SPARK-1001", llm=lambda p: "Heap exhausted under shuffle pressure.")
    assert rc.why_failed == "Heap exhausted under shuffle pressure."


def test_find_similar_resolved(session):
    # ZOOKEEPER-9001 is a resolved security issue.
    similar = find_similar_resolved(session, "security")
    assert any(i.key == "ZOOKEEPER-9001" for i in similar)


def test_advise_uses_kb_and_similar(session):
    from pipeline.services.knowledge_base import learn_from_resolved

    learn_from_resolved(session, "ZOOKEEPER-9001")  # seed KB with a security resolution
    # Classify an open security-ish issue first
    suggestion = advise(session, "ZOOKEEPER-9001")
    assert suggestion.category == "security"
    assert suggestion.steps  # template + KB
    assert suggestion.confidence > 0.5


def test_run_triage_persists_incident_and_resolution(session):
    crew = TriageCrew(session)
    result = crew.run_triage("SPARK-1001")
    assert result["classification"] == "memory"
    assert result["incident_id"]
    incident = session.get(Incident, result["incident_id"])
    assert incident.severity == "high"  # Critical -> high
    assert incident.error_signature == result["signature"]
    res = session.scalars(select(Resolution).where(Resolution.incident_id == incident.id)).first()
    assert res is not None

    # Classification written back to the issue.
    assert session.get(JiraIssue, "SPARK-1001").classification == "memory"


def test_recurring_detection_in_batch(session):
    crew = TriageCrew(session)
    results = crew.run_batch_triage(["SPARK-1001", "SPARK-1002", "FLINK-2001"])
    # All three share the OOM signature -> later ones flagged recurring.
    assert results[0]["is_recurring"] is False
    assert results[-1]["is_recurring"] is True
    assert len({r["signature"] for r in results}) == 1


def test_monitoring_cycle_and_report(session):
    crew = TriageCrew(session)
    triaged = crew.run_monitoring_cycle(project_key="SPARK")
    assert triaged  # SPARK has open issues
    report = build_report(session, "SPARK")
    assert report["total_issues"] == 3
    assert report["total_incidents"] >= 1
