"""Streamlit dashboard for the resume-job synthetic data pipeline (project 02).

Uses the shared dashboard kit (mini-projects/_shared/dashboard_kit.py). Loads the
artifacts produced by run_pipeline.py from data/.

Three tabs:
  Results          headline metrics, failure-rate bars, fit-level heatmap
  Failure Analysis niche vs standard, by-template, rule-vs-judge eval gap
  Browse Pairs     inspect a resume-job pair with its labels and judge verdict

Run with:  streamlit run dashboard.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "_shared"))
from dashboard_kit import (  # noqa: E402
    bar_chart,
    heatmap,
    metric_row,
    results_table,
    setup_page,
)

DATA = pathlib.Path(__file__).resolve().parent / "data"

setup_page(
    "Resume-Job Pipeline",
    icon="📄",
    subtitle="Synthetic resume-job pairs: generate → label → judge → analyze fit and failure modes.",
)


def load_json(name: str) -> dict | None:
    path = DATA / name
    return json.loads(path.read_text()) if path.exists() else None


def load_jsonl(name: str) -> list[dict]:
    path = DATA / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def nested_to_long(nested: dict, group_col: str) -> pd.DataFrame:
    rows = []
    for group, modes in nested.items():
        for mode, rate in modes.items():
            rows.append({group_col: group, "failure_mode": mode, "rate": round(rate, 3)})
    return pd.DataFrame(rows)


summary = load_json("pipeline_summary.json")

st.sidebar.title("📄 Resume-Job")
st.sidebar.caption("Regenerate artifacts with:\n\n`python run_pipeline.py --mode all`")

tab_results, tab_analysis, tab_browse = st.tabs(["Results", "Failure Analysis", "Browse Pairs"])


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
with tab_results:
    if not summary:
        st.info("No pipeline_summary.json yet. Run `python run_pipeline.py --mode all`.")
    else:
        judge = summary.get("llm_judge", {})
        metric_row(
            [
                ("Overall failure rate", f"{summary['overall_failure_rate']:.0%}"),
                ("Avg skills overlap", f"{summary['avg_skills_overlap']:.0%}"),
                ("Valid pairs", str(summary["totals"]["valid_pairs"])),
                ("Avg quality (judge)", f"{judge.get('avg_quality_score', 0):.1f}/10"),
            ]
        )

        rates = summary.get("failure_rates", {})
        if rates:
            df_rates = pd.DataFrame(
                [{"failure_mode": k, "rate": round(v, 3)} for k, v in rates.items()]
            )
            bar_chart(df_rates, "rate", "failure_mode", title="Failure rate by mode")

        by_fit = summary.get("by_fit_level", {})
        if by_fit:
            heatmap(
                nested_to_long(by_fit, "fit_level"),
                "failure_mode",
                "fit_level",
                "rate",
                title="Failure rate — fit level × mode",
            )


# --------------------------------------------------------------------------- #
# Failure Analysis
# --------------------------------------------------------------------------- #
with tab_analysis:
    if not summary:
        st.info("No pipeline_summary.json yet.")
    else:
        niche = summary.get("niche_vs_standard", {})
        if niche:
            heatmap(
                nested_to_long(niche, "job_type"),
                "failure_mode",
                "job_type",
                "rate",
                title="Niche vs standard jobs",
                height=140,
            )

        by_tpl = summary.get("by_template", {})
        if by_tpl:
            heatmap(
                nested_to_long(by_tpl, "template"),
                "failure_mode",
                "template",
                "rate",
                title="Failure rate by writing template",
            )

        gap = summary.get("llm_judge", {}).get("gap_analysis", {})
        if gap:
            st.markdown("##### Rule-based vs LLM-judge agreement (eval gap)")
            rows = []
            for dim, counts in gap.items():
                rows.append(
                    {
                        "dimension": dim,
                        "rule_based_flags": counts.get("rule_based_flags", 0),
                        "judge_flags": counts.get("judge_flags", 0),
                        "both_agree": counts.get("both_agree", 0),
                    }
                )
            results_table(pd.DataFrame(rows))
            st.caption(
                "Divergence between rule-based labels and the LLM judge is the signal to "
                "close — where they disagree, either the heuristic or the judge needs work."
            )


# --------------------------------------------------------------------------- #
# Browse Pairs
# --------------------------------------------------------------------------- #
with tab_browse:
    pairs = load_jsonl("pairs.jsonl")
    labels = {row["pair_id"]: row for row in load_jsonl("labels.jsonl")}
    judges = {row["pair_id"]: row for row in load_jsonl("judge_results.jsonl")}
    if not pairs:
        st.info("No pairs.jsonl found.")
    else:
        idx = st.slider("Pair", 1, len(pairs), 1) - 1
        pair = pairs[idx]
        meta = pair.get("metadata", {})
        pid = meta.get("pair_id")
        resume = pair.get("resume", {})
        job = pair.get("job", {})

        name = resume.get("contact", {}).get("name", "(candidate)")
        st.markdown(f"### {name} → {job.get('title', '(role)')} @ {job.get('company', '')}")
        st.caption(
            f"fit level: **{meta.get('fit_level', '?')}**  ·  "
            f"writing style: **{meta.get('writing_style', '?')}**"
        )

        label = labels.get(pid, {})
        if label:
            flags = [f"{'🔴' if v else '🟢'} {k}" for k, v in label.items() if isinstance(v, bool)]
            st.write("  ·  ".join(flags))
            if "skills_overlap" in label:
                st.caption(f"skills overlap: {label['skills_overlap']:.0%}")

        judge = judges.get(pid, {})
        if judge:
            j1, j2, j3 = st.columns(3)
            j1.metric("Quality", f"{judge.get('quality_score', '?')}/10")
            j2.metric("Hallucination", f"{judge.get('hallucination_score', '?')}/5")
            j3.metric("Awkward language", f"{judge.get('awkward_language_score', '?')}/5")
            if judge.get("fit_assessment"):
                st.markdown(f"**Assessment:** {judge['fit_assessment']}")
            for rec in judge.get("recommendations", []):
                st.caption(f"• {rec}")

        with st.expander("Job description"):
            st.write(job.get("description", "(none)"))
