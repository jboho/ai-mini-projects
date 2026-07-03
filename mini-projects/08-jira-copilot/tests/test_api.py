"""FastAPI endpoint tests with offline dependency overrides (stub embedder, no LLM)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from jira_copilot.api.app import create_app
from jira_copilot.api.deps import get_db, get_llm, get_vector_store
from jira_copilot.db.models import Base, Issue
from jira_copilot.db.sample_data import build_sample
from jira_copilot.services.vector_store import StubEmbedder, make_vector_store


@pytest.fixture
def client():
    # Shared in-memory DB usable across TestClient's worker thread (StaticPool).
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    seed = factory()
    build_sample(seed)
    seed.commit()
    store = make_vector_store(embedder=StubEmbedder())
    store.index_issues(list(seed.scalars(select(Issue))))
    seed.close()

    def _get_db():
        session = factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_llm] = lambda: None
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["issues_indexed"] == 6


def test_search(client):
    r = client.post("/search", json={"query": "oauth login", "limit": 3})
    assert r.status_code == 200
    body = r.json()
    assert body[0]["key"] == "APACHE-3"


def test_query_and_chat(client):
    r = client.post("/query", json={"text": "find open bugs in APACHE"})
    assert r.status_code == 200
    assert r.json()["intent"] == "search"

    r = client.post("/chat", json={"message": "find issues about oauth login"})
    assert r.status_code == 200
    assert isinstance(r.json()["result"], list)


def test_issue_detail_and_404(client):
    assert client.get("/issues/APACHE-1").json()["key"] == "APACHE-1"
    assert client.get("/issues/NOPE-1").status_code == 404


def test_issue_search_and_subresources(client):
    bugs = client.get("/issues/search", params={"type": "Bug"}).json()
    assert len(bugs) == 3
    assert len(client.get("/issues/APACHE-1/comments").json()) == 1
    links = client.get("/issues/APACHE-5/links").json()
    assert any(link["key"] == "APACHE-2" for link in links)
    assert client.get("/issues/APACHE-1/changes").json() == []


def test_context(client):
    ctx = client.get("/context/APACHE-4").json()
    assert ctx["components"] == ["storage"]
    assert any(link["key"] == "APACHE-3" for link in ctx["linked_issues"])
    deep = client.get("/context/APACHE-4/deep").json()
    assert "issue" in deep and "linked" in deep


def test_suggestions(client):
    pri = client.post("/suggest/APACHE-5/priority").json()
    assert pri["suggested"] == "Critical"
    full = client.post("/suggest/APACHE-5", json={}).json()
    assert full["issue_key"] == "APACHE-5"
    assert len(full["suggestions"]) >= 2


def test_sprint(client):
    plan = client.post("/sprint/plan", json={"project_key": "APACHE"}).json()
    assert plan["capacity"] == 13.0
    assert {r["key"] for r in plan["recommended"]} == {"APACHE-4", "APACHE-5"}

    health = client.get("/sprint/1/health").json()
    assert health["total_issues"] == 3
    assert len(client.get("/sprint/1/issues").json()) == 3

    vel = client.get("/velocity/APACHE").json()
    assert vel[0]["completed_points"] == 13.0
    recs = client.get("/sprint/1/recommendations", params={"project_key": "APACHE"}).json()
    assert isinstance(recs, list)


def test_write_workflow(client):
    op = client.post(
        "/write/update",
        json={"issue_key": "APACHE-4", "field": "priority", "new_value": "Critical"},
    ).json()
    assert op["status"] == "pending"
    assert client.get("/issues/APACHE-4").json()["priority"] != "Critical"  # not yet applied

    pending = client.get("/write/pending").json()
    assert len(pending) == 1

    client.post("/write/execute", json={"operation_ids": [op["id"]]})
    assert client.get("/issues/APACHE-4").json()["priority"] == "Critical"
    assert client.get("/write/pending").json() == []


def test_write_invalid_field(client):
    r = client.post(
        "/write/update", json={"issue_key": "APACHE-4", "field": "nope", "new_value": "x"}
    )
    assert r.status_code == 400


def test_write_bulk_and_discard(client):
    ops = client.post(
        "/write/bulk", json={"issue_keys": ["APACHE-4", "APACHE-5"], "sprint_id": 2}
    ).json()
    assert len(ops) == 2
    r = client.post("/write/discard", json={"operation_ids": [o["id"] for o in ops]})
    assert r.json()["discarded"] == 2


def test_analytics(client):
    client.post("/suggest/APACHE-5", json={})  # logs suggestions
    history = client.get("/analytics/suggestions").json()
    assert history
    sid = history[0]["id"]

    fb = client.post("/analytics/feedback", json={"suggestion_id": sid, "accepted": True})
    assert fb.status_code == 200

    metrics = client.get("/analytics/metrics").json()
    assert metrics["total_suggestions"] >= 1
    assert metrics["total_feedback"] == 1
    rates = client.get("/analytics/acceptance").json()
    assert rates  # at least one type with feedback


def test_docs_release_notes(client):
    notes = client.post("/docs/release-notes", json={"sprint_id": 1}).json()
    assert "Bug Fixes" in notes["sections"]
    assert "Features" in notes["sections"]
