"""Issue Triage Assistant -- Streamlit dashboard Home page.

Run: streamlit run dashboard/app.py
Sub-pages live in dashboard/pages/ and are auto-discovered by Streamlit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header, scalar  # noqa: E402

st.set_page_config(page_title="Issue Triage Assistant", page_icon="🛠", layout="wide")

page_header(
    "Issue Triage Assistant",
    "Multi-agent triage over Apache JIRA issues -- classification, deduplication, "
    "resolution, and approval workflow.",
)

total_issues = scalar("SELECT COUNT(*) FROM jira_issues")
open_bugs = scalar(
    "SELECT COUNT(*) FROM jira_issues WHERE issuetype = 'Bug' AND status != 'Closed'"
)
incidents = scalar("SELECT COUNT(*) FROM incidents")
pending_actions = scalar("SELECT COUNT(*) FROM resolution_actions WHERE status = 'PENDING'")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total issues", f"{total_issues:,}")
c2.metric("Open bugs", f"{open_bugs:,}")
c3.metric("Incidents", f"{incidents:,}")
c4.metric("Actions awaiting approval", f"{pending_actions:,}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Project health")
    health = load_df(
        """
        SELECT project_key AS project,
               COUNT(*) AS issues,
               SUM(CASE WHEN status != 'Closed' THEN 1 ELSE 0 END) AS open,
               SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS resolved
        FROM jira_issues
        GROUP BY project_key
        ORDER BY issues DESC
        """
    )
    if not empty_guard(health):
        st.dataframe(health, width="stretch", hide_index=True)

with right:
    st.subheader("Recent incidents")
    recent = load_df(
        """
        SELECT title, severity, classification, source_project AS project, status
        FROM incidents
        ORDER BY created_at DESC
        LIMIT 15
        """
    )
    if not empty_guard(recent, "No incidents recorded yet."):
        st.dataframe(recent, width="stretch", hide_index=True)

st.divider()
st.subheader("Actions requiring approval")
approvals = load_df(
    """
    SELECT ra.id, ra.action_type, ra.impact_level, ra.status, r.title AS resolution
    FROM resolution_actions ra
    JOIN resolutions r ON r.id = ra.resolution_id
    WHERE ra.status = 'PENDING'
    ORDER BY ra.created_at DESC
    """
)
if not empty_guard(approvals, "No actions awaiting approval."):
    st.dataframe(approvals, width="stretch", hide_index=True)
