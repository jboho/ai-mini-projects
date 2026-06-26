"""Fixtures: in-memory SQLite seeded with the synthetic triage sample."""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from pipeline.db.sample_data import build_sample  # noqa: E402
from pipeline.db.tables import Base  # noqa: E402


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = Session(engine)
    build_sample(s)
    s.commit()
    yield s
    s.close()
