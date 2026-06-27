"""Issue link type distribution and blocker chains."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Issue Links", "Dependency and duplicate relationships between issues.")

dist = load_df(
    """
    SELECT link_type, COUNT(*) AS links
    FROM issue_links
    GROUP BY link_type
    ORDER BY links DESC
    """
)
if not empty_guard(dist, "No issue links ingested yet."):
    st.subheader("Link type distribution")
    st.bar_chart(dist.set_index("link_type")["links"])

    st.divider()
    st.subheader("Blocker / dependency chains")
    chains = load_df(
        """
        SELECT source_key AS source, link_type, target_key AS target, target_status AS target_status
        FROM issue_links
        WHERE link_type LIKE '%block%' OR link_type LIKE '%depend%' OR link_type LIKE '%duplicat%'
        ORDER BY source_key
        """
    )
    if not empty_guard(chains, "No blocker/dependency/duplicate links."):
        st.dataframe(chains, width="stretch", hide_index=True)
