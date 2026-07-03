"""Streamlit app for the dating compatibility pipeline.

Three tabs:
  Data Quality          the 5-dimension quality report + gate
  Results               baseline vs fine-tuned metrics + visualizations
  Compatibility Checker type two profiles, see the model score their match

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
VISUALS = ROOT / "visuals"
MODEL_DIR = ROOT / "models" / "finetuned-minilm"
BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
ACCENT = "#1f7a4d"
CORE = ["margin", "effect_size", "false_positive_rate", "cluster_purity", "accuracy", "auc_roc"]

st.set_page_config(page_title="Dating Compatibility", page_icon="💞", layout="wide")
st.markdown(
    f"<style>[data-testid='stMetricValue']{{color:{ACCENT};font-weight:700}}</style>",
    unsafe_allow_html=True,
)
st.title("💞 Dating Compatibility")
st.caption("Fine-tuning all-MiniLM with CosineSimilarityLoss to tell compatible from incompatible.")


def load_json(name: str):
    path = REPORTS / name
    return json.loads(path.read_text()) if path.exists() else None


@st.cache_resource(show_spinner="Loading model…")
def load_model(path: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(path, device=os.environ.get("EMBED_DEVICE", "cpu"))


def cosine(model, a: str, b: str) -> float:
    import numpy as np

    e = model.encode([a, b], normalize_embeddings=True, show_progress_bar=False)
    return float(np.dot(e[0], e[1]))


tab_quality, tab_results, tab_checker = st.tabs(
    ["Data Quality", "Results", "Compatibility Checker"]
)


# --------------------------------------------------------------------------- #
with tab_quality:
    report = load_json("data_quality_report.json")
    if not report:
        st.info("No quality report yet. Run `python run_pipeline.py --mode quality`.")
    else:
        status = "PASS ✅" if report["passed"] else "FAIL ❌"
        cols = st.columns(len(report["dimensions"]) + 1)
        cols[0].metric("Overall", f"{report['overall_score']:.0f}/100", status)
        for col, d in zip(cols[1:], report["dimensions"]):
            col.metric(d["dimension"].replace("_", " ").title(), f"{d['score']:.0f}")
        st.caption(f"Training gate: ≥ {report['threshold']:.0f}/100")
        st.json({d["dimension"]: d["details"] for d in report["dimensions"]}, expanded=False)


# --------------------------------------------------------------------------- #
with tab_results:
    comp = load_json("comparison_report.json")
    if not comp:
        st.info("No comparison yet. Run `python run_pipeline.py --mode all`.")
    else:
        b, f = comp["baseline"], comp["finetuned"]
        st.markdown("##### Baseline vs fine-tuned")
        import pandas as pd

        rows = [
            {
                "metric": m,
                "baseline": round(b[m], 3),
                "fine-tuned": round(f[m], 3),
                "Δ%": round(comp["improvements"][m], 1),
                "target met": "✓" if comp["targets_met"][m] else "✗",
            }
            for m in CORE
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        n_met = sum(comp["targets_met"].values())
        st.success(f"{n_met}/{len(comp['targets_met'])} targets met")

        for img in [
            "metric_comparison.png",
            "similarity_distributions.png",
            "roc_curves.png",
            "umap_projection.png",
            "category_fpr.png",
        ]:
            path = VISUALS / img
            if path.exists():
                st.image(str(path), use_container_width=True)


# --------------------------------------------------------------------------- #
with tab_checker:
    st.subheader("Will they match?")
    st.caption("Enter two dating profiles; the fine-tuned model scores their compatibility.")
    if not MODEL_DIR.exists():
        st.info("No fine-tuned model yet. Run `python run_pipeline.py --mode train`.")
    else:
        examples = {
            "Compatible (both sober)": (
                "I'm a woman who is completely sober and does not drink. I want a partner who shares a sober lifestyle.",
                "I'm a man who is completely sober and does not drink.",
            ),
            "Incompatible (kids)": (
                "I'm a man who definitely wants to have children someday. My ideal match wants kids in the future.",
                "I'm a woman who is child-free by choice and certain about it.",
            ),
        }
        preset = st.selectbox("Try an example", ["(write your own)"] + list(examples))
        d1, d2 = examples.get(preset, ("", ""))
        c1, c2 = st.columns(2)
        text_a = c1.text_area("Profile A", value=d1, height=120)
        text_b = c2.text_area("Profile B", value=d2, height=120)

        if st.button("Check compatibility", type="primary") and text_a and text_b:
            fine = load_model(str(MODEL_DIR))
            base = load_model(BASE_MODEL)
            sf = cosine(fine, text_a, text_b)
            sb = cosine(base, text_a, text_b)
            verdict = "💚 Compatible" if sf > 0.5 else "💔 Not compatible"
            st.markdown(f"### {verdict}  ·  {sf * 100:.0f}%")
            st.progress(max(0.0, min(1.0, sf)))
            m1, m2 = st.columns(2)
            m1.metric("Fine-tuned score", f"{sf:.3f}")
            m2.metric("Baseline score", f"{sb:.3f}", f"{sf - sb:+.3f}")
            st.caption(
                "The fine-tuned model pushes incompatible pairs toward 0 and compatible toward 1."
            )
