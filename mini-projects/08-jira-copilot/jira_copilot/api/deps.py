"""FastAPI dependencies: DB session, vector store, engines, and services.

FastAPI caches sub-dependency results within a request, so every service below that
depends on ``get_db`` shares a single session per request. Tests override ``get_db``,
``get_vector_store``, and ``get_llm`` to run fully offline.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from ..agents.crew import JiraCopilotCrew
from ..config import get_settings
from ..db.engine import get_engine
from ..services.analytics import Analytics
from ..services.issue_service import IssueService
from ..services.issue_writer import IssueWriter
from ..services.query_parser import _openai_llm
from ..services.vector_store import VectorStore, make_vector_store

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = make_vector_store(persist_path=get_settings().chromadb_path)
    return _vector_store


def get_llm() -> Callable[[str], str] | None:
    return _openai_llm if get_settings().openai_api_key else None


def get_db() -> Session:
    factory = sessionmaker(bind=get_engine())
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_issue_service(session: Session = Depends(get_db)) -> IssueService:
    return IssueService(session)


def get_writer(session: Session = Depends(get_db)) -> IssueWriter:
    return IssueWriter(session)


def get_analytics(session: Session = Depends(get_db)) -> Analytics:
    return Analytics(session)


def get_crew(
    session: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
    llm: Callable[[str], str] | None = Depends(get_llm),
) -> JiraCopilotCrew:
    return JiraCopilotCrew(session, vector_store, llm=llm)
