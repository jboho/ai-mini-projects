"""Phase 2: chunked CSV ingestion + enrichment."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from pipeline.db.tables import Base, IssueComment, JiraIssue
from pipeline.ingest.enricher import build_issue_context, enrich_issue_with_comments
from pipeline.ingest.loader import ingest_dir, load_issues, write_sample_csvs


@pytest.fixture
def csv_dir(tmp_path):
    return write_sample_csvs(tmp_path / "data")


@pytest.fixture
def empty_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = Session(engine)
    yield s
    s.close()


def test_write_sample_csvs(csv_dir):
    for name in ("issues", "comments", "changelog", "issuelinks"):
        assert (csv_dir / f"{name}.csv").exists()


def test_ingest_dir_loads_all(csv_dir, empty_session):
    counts = ingest_dir(
        csv_dir,
        [
            "SPARK",
            "HADOOP",
            "HDFS",
            "FLINK",
            "KAFKA",
            "HIVE",
            "CASSANDRA",
            "HBASE",
            "ZOOKEEPER",
            "YARN",
        ],
        50_000,
        empty_session,
    )
    assert counts["issues"] == 14
    assert counts["comments"] == 5
    assert counts["issuelinks"] == 3
    assert counts["changelog"] == 4
    total = empty_session.scalar(select(func.count()).select_from(JiraIssue))
    assert total == 14


def test_project_filter_excludes_unwanted(csv_dir, empty_session):
    # Only keep SPARK -> 3 SPARK issues in the sample (1001, 1002, 1003)
    n = load_issues(csv_dir / "issues.csv", ["SPARK"], session=empty_session)
    assert n == 3
    keys = {k for (k,) in empty_session.execute(select(JiraIssue.key))}
    assert keys == {"SPARK-1001", "SPARK-1002", "SPARK-1003"}


def test_chunked_equals_full(csv_dir):
    """Chunked load (size 3) yields the same rows as a single-chunk load."""
    eng_a = create_engine("sqlite:///:memory:")
    eng_b = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng_a)
    Base.metadata.create_all(eng_b)
    projects = [
        "SPARK",
        "HADOOP",
        "HDFS",
        "FLINK",
        "KAFKA",
        "HIVE",
        "CASSANDRA",
        "HBASE",
        "ZOOKEEPER",
        "YARN",
    ]
    with Session(eng_a) as sa, Session(eng_b) as sb:
        n_full = load_issues(csv_dir / "issues.csv", projects, chunksize=10_000, session=sa)
        n_chunked = load_issues(csv_dir / "issues.csv", projects, chunksize=3, session=sb)
        assert n_full == n_chunked == 14


def test_timestamps_parsed(csv_dir, empty_session):
    load_issues(csv_dir / "issues.csv", ["KAFKA"], session=empty_session)
    issue = empty_session.get(JiraIssue, "KAFKA-4001")
    assert issue.created_at is not None and issue.resolved_at is not None


def test_enricher_builds_context(session):
    comments = enrich_issue_with_comments(session, "SPARK-1001")
    assert any(c.contains_stacktrace for c in comments)
    ctx = build_issue_context(session, "SPARK-1001")
    assert ctx["key"] == "SPARK-1001"

    # SPARK-1002 is a link source pointing at SPARK-1001 (a duplicate).
    ctx2 = build_issue_context(session, "SPARK-1002")
    assert ctx2["links"][0]["target"] == "SPARK-1001"
    assert ctx2["links"][0]["type"] == "duplicates"
    assert build_issue_context(session, "NOPE-1") == {}


def test_idempotent_load_skips_duplicates(csv_dir, empty_session):
    load_issues(csv_dir / "issues.csv", ["SPARK"], session=empty_session)
    again = load_issues(csv_dir / "issues.csv", ["SPARK"], session=empty_session)
    assert again == 0  # already present
    assert empty_session.scalar(select(func.count()).select_from(JiraIssue)) == 3
    _ = IssueComment  # imported for symmetry
