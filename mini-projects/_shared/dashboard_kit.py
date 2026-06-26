"""Shared Streamlit components for mini-project dashboards.

Domain-agnostic theme + widgets so every project's dashboard films with the same
look. Domain logic stays in each project's ``dashboard.py``; this module only
knows about DataFrames and (label, value) pairs.

Usage from a per-project dashboard.py:

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "_shared"))
    from dashboard_kit import setup_page, metric_row, heatmap, bar_chart, results_table, run_with_progress
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import contextmanager

import altair as alt
import pandas as pd
import streamlit as st

ACCENT = "#1f7a4d"
HEATMAP_SCHEME = "viridis"

_CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; }}
  h1 {{ letter-spacing: -0.02em; }}
  [data-testid="stMetricValue"] {{ color: {ACCENT}; font-weight: 700; }}
  [data-testid="stMetric"] {{
      background: rgba(31,122,77,0.06);
      border: 1px solid rgba(31,122,77,0.18);
      border-radius: 0.6rem;
      padding: 0.6rem 0.9rem;
  }}
  div[data-baseweb="tab-list"] button {{ font-weight: 600; }}
</style>
"""


def setup_page(title: str, icon: str = "📊", subtitle: str | None = None) -> None:
    """Set page config, inject the shared theme, and render the header."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title(f"{icon} {title}")
    if subtitle:
        st.caption(subtitle)


def metric_row(metrics: Sequence[tuple[str, str]]) -> None:
    """Render a row of metric cards from ``(label, value)`` pairs."""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)


def heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    value: str,
    title: str | None = None,
    fmt: str = ".2f",
    height: int = 220,
) -> None:
    """Render a labeled rectangular heatmap of ``value`` over ``x`` × ``y``."""
    if title:
        st.markdown(f"##### {title}")
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:N", title=x.replace("_", " ").title()),
        y=alt.Y(f"{y}:N", title=y.replace("_", " ").title()),
    )
    rect = base.mark_rect().encode(
        color=alt.Color(f"{value}:Q", scale=alt.Scale(scheme=HEATMAP_SCHEME)),
        tooltip=[x, y, value],
    )
    text = base.mark_text(baseline="middle").encode(
        text=alt.Text(f"{value}:Q", format=fmt), color=alt.value("white")
    )
    st.altair_chart((rect + text).properties(height=height), use_container_width=True)


def bar_chart(
    df: pd.DataFrame,
    value: str,
    category: str,
    color: str | None = None,
    title: str | None = None,
    height: int = 260,
) -> None:
    """Render a horizontal bar chart of ``value`` per ``category``."""
    if title:
        st.markdown(f"##### {title}")
    enc = {
        "x": alt.X(f"{value}:Q"),
        "y": alt.Y(f"{category}:N", sort="-x", title=None),
        "tooltip": list(df.columns),
    }
    if color:
        enc["color"] = alt.Color(f"{color}:N")
    st.altair_chart(
        alt.Chart(df).mark_bar().encode(**enc).properties(height=height),
        use_container_width=True,
    )


def results_table(
    df: pd.DataFrame, highlight_cols: Sequence[str] | None = None, title: str | None = None
) -> None:
    """Render a sortable table, optionally highlighting the max of given columns."""
    if title:
        st.markdown(f"##### {title}")
    styler = df.style
    if highlight_cols:
        present = [c for c in highlight_cols if c in df.columns]
        if present:
            styler = styler.highlight_max(subset=present, color=ACCENT)
    st.dataframe(styler, use_container_width=True, hide_index=True)


class Progress:
    """Streams stage messages into an ``st.status`` block (motion for video)."""

    def __init__(self, status, log) -> None:
        self._status = status
        self._log = log
        self._events: list[str] = []

    def emit(self, msg: str) -> None:
        self._events.append(msg)
        self._status.update(label=msg)
        self._log.write("\n".join(f"• {e}" for e in self._events[-12:]))

    def complete(self, msg: str) -> None:
        self._status.update(label=msg, state="complete")

    def error(self, msg: str) -> None:
        self._status.update(label=msg, state="error")


@contextmanager
def run_with_progress(label: str = "Running…"):
    """Context manager yielding a :class:`Progress` for streaming live stages."""
    with st.status(label, expanded=True) as status:
        log = st.empty()
        yield Progress(status, log)
