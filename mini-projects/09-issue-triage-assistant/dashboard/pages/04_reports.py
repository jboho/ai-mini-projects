"""Generated report viewer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Reports", "Daily and weekly triage reports.")

reports = load_df(
    """
    SELECT id, report_type, title, project_key AS project, created_at
    FROM reports
    ORDER BY created_at DESC
    """
)

if not empty_guard(reports, "No reports generated yet. Run --mode report."):
    options = {f"#{r.id} {r.title} ({r.report_type})": r.id for r in reports.itertuples()}
    label = st.selectbox("Select a report", list(options.keys()))
    rid = options[label]
    detail = load_df("SELECT content, metrics_json FROM reports WHERE id = :id", {"id": int(rid)})
    if not detail.empty:
        st.markdown(detail.iloc[0]["content"] or "_No content._")
        try:
            metrics = json.loads(detail.iloc[0]["metrics_json"] or "{}")
        except json.JSONDecodeError:
            metrics = {}
        if metrics:
            st.subheader("Metrics")
            st.json(metrics)
