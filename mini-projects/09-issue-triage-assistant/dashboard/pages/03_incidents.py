"""Incident list with severity, root cause, and status filters."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Incidents", "Triaged incidents with root cause and severity.")

base = load_df(
    """
    SELECT id, title, severity, status, source_project AS project,
           classification, root_cause, jira_issue_key AS issue, created_at
    FROM incidents
    ORDER BY created_at DESC
    """
)

if not empty_guard(base):
    severities = sorted(base["severity"].dropna().unique().tolist())
    statuses = sorted(base["status"].dropna().unique().tolist())
    c1, c2 = st.columns(2)
    sev = c1.multiselect("Severity", severities, default=severities)
    sta = c2.multiselect("Status", statuses, default=statuses)

    view = base[base["severity"].isin(sev) & base["status"].isin(sta)]
    st.caption(f"{len(view)} of {len(base)} incidents")
    st.dataframe(view, width="stretch", hide_index=True)
