"""Resolution suggestions, approval queue, and execution history."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Resolutions", "Suggested resolutions and the approval workflow.")

st.subheader("Suggested resolutions")
res = load_df(
    """
    SELECT r.id, r.title, r.confidence, i.severity, i.source_project AS project
    FROM resolutions r
    JOIN incidents i ON i.id = r.incident_id
    ORDER BY r.confidence DESC
    """
)
if not empty_guard(res, "No resolutions suggested yet."):
    st.dataframe(res, width="stretch", hide_index=True)

st.divider()
st.subheader("Approval queue")
pending = load_df(
    """
    SELECT ra.id, ra.action_type, ra.impact_level, r.title AS resolution
    FROM resolution_actions ra
    JOIN resolutions r ON r.id = ra.resolution_id
    WHERE ra.status = 'PENDING'
    ORDER BY ra.impact_level DESC, ra.created_at DESC
    """
)
if not empty_guard(pending, "Approval queue is empty."):
    st.dataframe(pending, width="stretch", hide_index=True)

st.divider()
st.subheader("Execution history")
history = load_df(
    """
    SELECT ra.action_type, ra.impact_level, ra.status, ra.approved_by, ra.executed_at
    FROM resolution_actions ra
    WHERE ra.status IN ('APPROVED', 'EXECUTING', 'COMPLETED', 'REJECTED')
    ORDER BY ra.executed_at DESC NULLS LAST, ra.id DESC
    """
)
if not empty_guard(history, "No action history yet."):
    st.dataframe(history, width="stretch", hide_index=True)
