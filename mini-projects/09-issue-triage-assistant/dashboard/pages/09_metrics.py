"""System KPIs derived from the database, plus the latest evaluation results."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header, scalar  # noqa: E402

page_header("Metrics", "System KPIs and the most recent evaluation run.")

total = scalar("SELECT COUNT(*) FROM jira_issues")
classified = scalar("SELECT COUNT(*) FROM jira_issues WHERE classification != ''")
dup_signatures = scalar("SELECT COUNT(*) FROM error_signatures WHERE occurrence_count > 1")
kb_entries = scalar("SELECT COUNT(*) FROM knowledge_base")
avg_res_conf = scalar("SELECT ROUND(AVG(confidence), 2) FROM resolutions", default=0.0)

coverage = round(classified / total, 2) if total else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Classification coverage", f"{coverage:.0%}")
c2.metric("Duplicate signatures", int(dup_signatures))
c3.metric("KB entries", int(kb_entries))
c4.metric("Avg resolution confidence", f"{float(avg_res_conf):.2f}")

st.divider()
st.subheader("Latest evaluation results")

results_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "evaluation",
    "results.json",
)
if os.path.exists(results_path):
    with open(results_path) as fh:
        try:
            results = json.load(fh)
        except json.JSONDecodeError:
            results = {}
    if results:
        st.json(results)
    else:
        st.info("evaluation/results.json is empty.")
else:
    st.info("No evaluation results yet. Run --mode evaluate to generate evaluation/results.json.")

st.divider()
st.subheader("Confidence distribution")
conf = load_df("SELECT confidence FROM jira_issues WHERE classification != ''")
if not empty_guard(conf, "No classified issues yet."):
    st.bar_chart(conf["confidence"].value_counts().sort_index())
