"""Streamlit dashboard for the DIY-repair synthetic data pipeline (project 01).

Uses the shared dashboard kit (mini-projects/_shared/dashboard_kit.py) for a
consistent look. Loads the artifacts produced by run_pipeline.py from data/.

Three tabs:
  Results          before/after failure rates, per-mode improvement
  Failure Analysis category coverage, worst items, per-mode table
  Browse Examples  inspect generated Q&A items with their judge verdicts

Run with:  streamlit run dashboard.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "_shared"))
from dashboard_kit import (  # noqa: E402
    bar_chart,
    metric_row,
    results_table,
    setup_page,
)

DATA = pathlib.Path(__file__).resolve().parent / "data"

setup_page(
    "Synthetic Data Pipeline — DIY Repair QA",
    icon="🛠️",
    subtitle="Generate → validate → LLM-judge → correct, with before/after failure analysis.",
)


def load_json(name: str) -> dict | None:
    path = DATA / name
    return json.loads(path.read_text()) if path.exists() else None


def load_jsonl(name: str) -> list[dict]:
    path = DATA / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


comparison = load_json("comparison.json")
baseline = load_json("baseline_summary.json")
corrected = load_json("corrected_summary.json")

st.sidebar.title("🛠️ DIY Repair QA")
st.sidebar.caption("Regenerate artifacts with:\n\n`python run_pipeline.py --mode all`")

tab_results, tab_analysis, tab_browse = st.tabs(["Results", "Failure Analysis", "Browse Examples"])


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
with tab_results:
    if not comparison:
        st.info("No comparison.json yet. Run `python run_pipeline.py --mode all`.")
    else:
        passed = str(comparison.get("pass")).lower() in ("true", "1")
        metric_row(
            [
                ("Baseline failure rate", f"{comparison['baseline_overall']:.0%}"),
                ("Corrected failure rate", f"{comparison['corrected_overall']:.0%}"),
                ("Improvement", f"{comparison['improvement']:.0%}"),
                ("Target met (>80%)", "✓ Yes" if passed else "✗ No"),
            ]
        )
        ci_b = comparison.get("baseline_ci_95")
        ci_c = comparison.get("corrected_ci_95")
        if ci_b and ci_c:
            st.caption(
                f"95% CI — baseline [{ci_b[0]:.2f}, {ci_b[1]:.2f}], "
                f"corrected [{ci_c[0]:.2f}, {ci_c[1]:.2f}]; "
                f"non-overlapping: {comparison.get('ci_overlap') == 'False'}"
            )

        per_mode = []
        for mode, rate in comparison["per_mode_baseline"].items():
            per_mode.append({"failure_mode": mode, "rate": rate, "phase": "baseline"})
        for mode, rate in comparison["per_mode_corrected"].items():
            per_mode.append({"failure_mode": mode, "rate": rate, "phase": "corrected"})
        df_mode = pd.DataFrame(per_mode)

        st.markdown("##### Failure rate by mode — baseline vs corrected")
        chart = (
            alt.Chart(df_mode)
            .mark_bar()
            .encode(
                x=alt.X("rate:Q", title="Failure rate"),
                y=alt.Y("failure_mode:N", sort="-x", title=None),
                yOffset="phase:N",
                color=alt.Color("phase:N", scale=alt.Scale(range=["#b04632", "#1f7a4d"])),
                tooltip=["failure_mode", "phase", "rate"],
            )
            .properties(height=280)
        )
        st.altair_chart(chart, use_container_width=True)


# --------------------------------------------------------------------------- #
# Failure Analysis
# --------------------------------------------------------------------------- #
with tab_analysis:
    if not baseline:
        st.info("No baseline_summary.json yet.")
    else:
        cov = baseline.get("category_coverage", {}).get("counts", {})
        if cov:
            df_cov = pd.DataFrame(
                [{"category": k, "items": v} for k, v in cov.items()]
            ).sort_values("items", ascending=False)
            bar_chart(df_cov, "items", "category", title="Category coverage (baseline)")

        worst = baseline.get("worst_items", [])
        if worst:
            st.markdown("##### Worst items (baseline)")
            results_table(pd.DataFrame(worst))

        if corrected:
            rows = []
            for mode in baseline["per_mode_rates"]:
                rows.append(
                    {
                        "failure_mode": mode,
                        "baseline": baseline["per_mode_rates"][mode],
                        "corrected": corrected["per_mode_rates"].get(mode, 0.0),
                    }
                )
            results_table(pd.DataFrame(rows), title="Per-mode failure rates")


# --------------------------------------------------------------------------- #
# Browse Examples
# --------------------------------------------------------------------------- #
with tab_browse:
    which = st.radio("Dataset", ["baseline", "corrected"], horizontal=True)
    items = load_jsonl(f"{which}.jsonl")
    if not items:
        st.info(f"No {which}.jsonl found.")
    else:
        idx = st.slider("Item", 1, len(items), 1) - 1
        record = items[idx]
        item = record.get("item", {})
        st.markdown(f"**Q:** {item.get('question', '(no question)')}")
        with st.expander("Answer", expanded=True):
            st.write(item.get("answer", "(no answer)"))

        judge = record.get("judge_result", {})
        if judge:
            st.markdown("##### Judge verdict")
            flags, notes = [], []
            for key, val in judge.items():
                if isinstance(val, bool):
                    flags.append(f"{'🔴' if val else '🟢'} {key}")
                else:
                    notes.append((key, val))
            if flags:
                st.write("  ·  ".join(flags))
            for key, val in notes:
                st.caption(f"**{key}:** {val}")
