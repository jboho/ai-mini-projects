"""Fixtures: in-memory SQLite seeded with TAWOS-shaped sample data."""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from jira_copilot.db.models import Base  # noqa: E402
from jira_copilot.db.sample_data import build_sample  # noqa: E402


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = Session(engine)
    build_sample(s)
    s.commit()
    yield s
    s.close()


@pytest.fixture
def vector_store(session):
    """In-memory ChromaDB store seeded with the sample issues, offline stub embedder."""
    from sqlalchemy import select

    from jira_copilot.db.models import Issue
    from jira_copilot.services.vector_store import StubEmbedder, make_vector_store

    store = make_vector_store(embedder=StubEmbedder())
    issues = list(session.scalars(select(Issue)))
    store.index_issues(issues)
    return store
