"""Shared helpers for the Streamlit dashboard.

All pages query the same SQLite database via SQLAlchemy. Helpers are cached so the
engine is created once per session, and every query degrades gracefully when the
database is empty or has not been created yet.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Allow `import pipeline...` when Streamlit runs this file from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.db.engine import get_engine  # noqa: E402


@st.cache_resource
def engine():
    return get_engine()


def load_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run a read query and return a DataFrame; empty frame if the table is absent."""
    try:
        return pd.read_sql(text(sql), engine(), params=params or {})
    except OperationalError:
        return pd.DataFrame()


def scalar(sql: str, default=0):
    df = load_df(sql)
    if df.empty:
        return default
    value = df.iloc[0, 0]
    return default if value is None else value


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def empty_guard(
    df: pd.DataFrame, message: str = "No data yet. Run the pipeline to populate the database."
) -> bool:
    """Show an info banner and return True when there is nothing to display."""
    if df.empty:
        st.info(message)
        return True
    return False
