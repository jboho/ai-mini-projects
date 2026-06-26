"""Shared eval helpers: metrics and an in-memory sample-backed store."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import jira_copilot  # noqa: E402, F401 -- sets OpenMP / telemetry guards
from jira_copilot.config import get_settings  # noqa: E402
from jira_copilot.db.models import Base, Issue  # noqa: E402
from jira_copilot.db.sample_data import build_sample  # noqa: E402
from jira_copilot.services.issue_service import IssueService  # noqa: E402
from jira_copilot.services.vector_store import (  # noqa: E402
    OpenAIEmbedder,
    StubEmbedder,
    make_vector_store,
)


def recall_at_k(retrieved: list[str], relevant: list[str], k: int = 5) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    hits = sum(1 for key in retrieved[:k] if key in rel)
    return hits / len(rel)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int = 5) -> float:
    if k <= 0:
        return 0.0
    rel = set(relevant)
    hits = sum(1 for key in retrieved[:k] if key in rel)
    return hits / k


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    rel = set(relevant)
    for rank, key in enumerate(retrieved, start=1):
        if key in rel:
            return 1.0 / rank
    return 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def default_embedder():
    """Real OpenAI embeddings when a key is configured, otherwise the offline stub."""
    return OpenAIEmbedder() if get_settings().openai_api_key else StubEmbedder()


def build_sample_env(embedder=None):
    """Return (session, issue_service, vector_store) backed by the synthetic sample."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    build_sample(session)
    session.commit()
    store = make_vector_store(embedder=embedder or default_embedder())
    store.index_issues(list(session.scalars(select(Issue))))
    return session, IssueService(session), store
