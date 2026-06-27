"""Error pattern frequency and stack-trace samples from comments."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if p.name == "dashboard")))

from _shared import empty_guard, load_df, page_header  # noqa: E402

page_header("Text Analysis", "Error signatures and comment-level error/fix signals.")

st.subheader("Top error signatures")
sigs = load_df(
    """
    SELECT pattern, classification, occurrence_count AS occurrences, first_issue_key AS first_seen
    FROM error_signatures
    ORDER BY occurrence_count DESC
    LIMIT 25
    """
)
if not empty_guard(sigs, "No error signatures registered yet."):
    st.dataframe(sigs, width="stretch", hide_index=True)

st.divider()
st.subheader("Comment signal counts")
signals = load_df(
    """
    SELECT
      SUM(CASE WHEN contains_error THEN 1 ELSE 0 END) AS errors,
      SUM(CASE WHEN contains_stacktrace THEN 1 ELSE 0 END) AS stacktraces,
      SUM(CASE WHEN contains_fix THEN 1 ELSE 0 END) AS fixes
    FROM issue_comments
    """
)
if not empty_guard(signals, "No comments ingested yet."):
    row = signals.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Comments with errors", int(row["errors"] or 0))
    c2.metric("With stack traces", int(row["stacktraces"] or 0))
    c3.metric("With fixes", int(row["fixes"] or 0))

st.divider()
st.subheader("Stack-trace samples")
samples = load_df(
    """
    SELECT issue_key, author, substr(body, 1, 300) AS excerpt
    FROM issue_comments
    WHERE contains_stacktrace = 1
    LIMIT 10
    """
)
if not empty_guard(samples, "No stack-trace comments found."):
    st.dataframe(samples, width="stretch", hide_index=True)
