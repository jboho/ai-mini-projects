"""Per-project bug counts and open/resolved ratios."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Project Status", "Bug volume and resolution ratio per project.")

df = load_df(
    """
    SELECT project_key AS project,
           COUNT(*) AS total,
           SUM(CASE WHEN issuetype = 'Bug' THEN 1 ELSE 0 END) AS bugs,
           SUM(CASE WHEN status != 'Closed' THEN 1 ELSE 0 END) AS open,
           SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS resolved
    FROM jira_issues
    GROUP BY project_key
    ORDER BY total DESC
    """
)

if not empty_guard(df):
    df["resolved_ratio"] = (df["resolved"] / df["total"]).round(2)
    st.dataframe(df, width="stretch", hide_index=True)
    st.bar_chart(df.set_index("project")[["open", "resolved"]])
