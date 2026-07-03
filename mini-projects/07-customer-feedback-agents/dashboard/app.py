"""Streamlit dashboard for the customer feedback pipeline (4 tabs)."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from pipeline.config import DATA_DIR  # noqa: E402
from pipeline.orchestrator import PipelineOutput, load_output  # noqa: E402

st.set_page_config(page_title="Customer Feedback", page_icon="📣", layout="wide")
st.title("📣 Customer Feedback Analysis")

if not (DATA_DIR / "pipeline_output.json").exists():
    st.info("No pipeline output yet. Run `python run_pipeline.py --mode full`.")
    st.stop()

out: PipelineOutput = load_output()
sent_by_id = {s.feedback_id: s for s in out.sentiments}

tab_overview, tab_themes, tab_gaps, tab_explorer = st.tabs(
    ["Overview", "Themes", "Gaps", "Explorer"]
)

with tab_overview:
    pains = [s.pain_intensity for s in out.sentiments]
    avg_pain = sum(pains) / len(pains) if pains else 0.0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Feedback", len(out.feedback))
    c2.metric("Avg pain", f"{avg_pain:.2f}")
    c3.metric("Themes", len(out.themes))
    c4.metric("Gaps", sum(1 for g in out.gaps if not g.has_coverage))

    if out.sentiments:
        counts = pd.Series([s.sentiment for s in out.sentiments]).value_counts().reset_index()
        counts.columns = ["sentiment", "count"]
        col_a, col_b = st.columns(2)
        col_a.plotly_chart(
            px.pie(counts, names="sentiment", values="count", title="Sentiment mix"),
            use_container_width=True,
        )
        col_b.plotly_chart(
            px.histogram(pd.DataFrame({"pain": pains}), x="pain", nbins=20, title="Pain intensity"),
            use_container_width=True,
        )

with tab_themes:
    if out.themes:
        df = pd.DataFrame(
            [
                {"theme": t.name, "feedback": len(t.feedback_ids), "avg_pain": t.avg_pain}
                for t in out.themes
            ]
        ).sort_values("feedback")
        st.plotly_chart(
            px.bar(df, x="feedback", y="theme", orientation="h", title="Theme frequency"),
            use_container_width=True,
        )
        for t in out.themes:
            with st.expander(f"{t.name} · {len(t.feedback_ids)} reviews · pain {t.avg_pain:.2f}"):
                st.write(t.description)
                st.caption("Keywords: " + ", ".join(t.keywords))

with tab_gaps:
    if out.gaps:
        gdf = pd.DataFrame(
            [
                {
                    "theme": g.theme_name,
                    "feedback": g.feedback_count,
                    "avg_pain": g.avg_pain,
                    "priority": g.priority_score,
                    "covered": "covered" if g.has_coverage else "gap",
                }
                for g in out.gaps
            ]
        )
        st.plotly_chart(
            px.scatter(
                gdf,
                x="feedback",
                y="avg_pain",
                size="priority",
                color="covered",
                hover_name="theme",
                title="Priority matrix (size = priority)",
            ),
            use_container_width=True,
        )
        for g in out.gaps:
            if g.has_coverage:
                continue
            with st.expander(f"⚠️ {g.theme_name} — priority {g.priority_score:.2f}"):
                st.caption(f"{g.feedback_count} reviews · avg pain {g.avg_pain:.2f}")
                for rec in g.recommendations:
                    st.write(f"• {rec}")

with tab_explorer:
    rows = []
    for f in out.feedback:
        s = sent_by_id.get(f.id)
        rows.append(
            {
                "source": f.source,
                "rating": f.rating,
                "sentiment": s.sentiment if s else None,
                "pain": s.pain_intensity if s else None,
                "text": f.text[:200],
            }
        )
    fdf = pd.DataFrame(rows)
    src = st.multiselect(
        "Source", sorted(fdf["source"].unique()), default=list(fdf["source"].unique())
    )
    sent = st.multiselect("Sentiment", ["positive", "neutral", "negative"], default=["negative"])
    view = fdf[fdf["source"].isin(src)]
    if sent and view["sentiment"].notna().any():
        view = view[view["sentiment"].isin(sent)]
    st.dataframe(view, use_container_width=True, hide_index=True)
