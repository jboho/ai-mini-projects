"""Category distribution and classification confidence."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Classification", "Category distribution and confidence.")

dist = load_df(
    """
    SELECT classification AS category, COUNT(*) AS issues, ROUND(AVG(confidence), 2) AS avg_confidence
    FROM jira_issues
    WHERE classification != ''
    GROUP BY classification
    ORDER BY issues DESC
    """
)

if not empty_guard(dist, "No classified issues yet. Run --mode classify."):
    st.subheader("Category distribution")
    st.bar_chart(dist.set_index("category")["issues"])
    st.dataframe(dist, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Low-confidence issues (review)")
    low = load_df(
        """
        SELECT key, project_key AS project, classification, confidence, summary
        FROM jira_issues
        WHERE classification != '' AND confidence < 0.6
        ORDER BY confidence ASC
        LIMIT 25
        """
    )
    if not empty_guard(low, "No low-confidence classifications."):
        st.dataframe(low, width="stretch", hide_index=True)
