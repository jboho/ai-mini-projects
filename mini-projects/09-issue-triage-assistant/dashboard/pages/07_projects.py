"""Cross-project comparison matrix."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Projects", "Cross-project comparison by classification.")

matrix = load_df(
    """
    SELECT project_key AS project, classification AS category, COUNT(*) AS issues
    FROM jira_issues
    WHERE classification != ''
    GROUP BY project_key, classification
    """
)

if not empty_guard(matrix, "No classified issues to compare yet."):
    pivot = matrix.pivot_table(index="project", columns="category", values="issues", fill_value=0)
    st.subheader("Project x category matrix")
    st.dataframe(pivot, width="stretch")

    st.divider()
    st.subheader("Issues per project")
    totals = matrix.groupby("project")["issues"].sum()
    st.bar_chart(totals)
