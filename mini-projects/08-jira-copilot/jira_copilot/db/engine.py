"""SQLAlchemy engine + session factory."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .models import Base

_engine = None
_Session = None


def get_engine(url: str | None = None):
    global _engine, _Session
    if url is not None:
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        return engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url)
        _Session = sessionmaker(bind=_engine)
    return _engine


def init_db(engine=None) -> None:
    Base.metadata.create_all(engine or get_engine())


def make_session_factory(engine):
    return sessionmaker(bind=engine)


@contextmanager
def get_session(engine=None):
    global _Session
    if engine is not None:
        factory = sessionmaker(bind=engine)
    else:
        get_engine()
        factory = _Session
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
