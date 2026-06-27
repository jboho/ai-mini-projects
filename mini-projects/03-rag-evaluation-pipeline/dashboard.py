"""Streamlit dashboard for the RAG evaluation pipeline.

Reference implementation of the shared dashboard kit (see
``mini-projects/_shared/dashboard_kit.py``): chrome, charts, and the progress
runner come from the kit; only the RAG-domain logic lives here.

Three tabs:
  Run              grid search with live per-stage progress
  Results          metric cards, MRR heatmap, per-config bars, sortable table
  Query Playground type a question -> top-k retrieved chunks (instant, cached)

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
    run_with_progress,
    setup_page,
)

from pipeline.chunker import create_chunks  # noqa: E402
from pipeline.config import (  # noqa: E402
    DATA_DIR,
    DEFAULT_CHUNKING_CONFIGS,
    EMBEDDING_MODELS,
    RESULTS_DIR,
    GridSearchConfig,
    RetrievalMethod,
)
from pipeline.embedder import embed_chunks, embed_query  # noqa: E402
from pipeline.grid_search import find_best_config, run_grid_search, save_results  # noqa: E402
from pipeline.parser import extract_full_text, parse_pdf  # noqa: E402
from pipeline.retriever import (  # noqa: E402
    build_bm25,
    retrieve_bm25,
    retrieve_hybrid,
    retrieve_vector,
)
from pipeline.vectorstore import build_index  # noqa: E402

setup_page(
    "RAG Evaluation Pipeline",
    icon="🔎",
    subtitle="Chunking × embedding × retrieval grid search over a PDF.",
)

LABEL_TO_CONFIG = {c.label: c for c in DEFAULT_CHUNKING_CONFIGS}
PDF_DIR = DATA_DIR / "pdf"
ALL_METHODS = [m.value for m in RetrievalMethod]


# --------------------------------------------------------------------------- #
# Domain data helpers
# --------------------------------------------------------------------------- #
def list_pdfs() -> list[str]:
    return sorted(str(p) for p in PDF_DIR.glob("*.pdf"))


def load_result_files() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for path in sorted(RESULTS_DIR.glob("*_results.json")):
        out[path.stem.removesuffix("_results")] = json.loads(path.read_text())
    return out


def results_to_df(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        m = r["metrics"]
        rows.append(
            {
                "chunking": r["chunking_method"],
                "embedding": r["embedding_model"],
                "retrieval": r["retrieval_method"],
                "MRR": round(m["mrr"], 3),
                "MAP": round(m["map_score"], 3),
                "Recall@5": round(m["recall_at_k"].get("5", 0.0), 3),
                "Precision@5": round(m["precision_at_k"].get("5", 0.0), 3),
                "NDCG@5": round(m["ndcg_at_k"].get("5", 0.0), 3),
                "ms": round(m["avg_retrieval_time"] * 1000, 1),
            }
        )
    return pd.DataFrame(rows)


@st.cache_resource(show_spinner=False)
def get_chunks(pdf_path: str, label: str):
    cfg = LABEL_TO_CONFIG[label]
    pages = parse_pdf(pdf_path, parser=cfg.parser)
    return create_chunks(extract_full_text(pages), cfg, pages)


@st.cache_resource(show_spinner=False)
def get_index(pdf_path: str, label: str, model: str):
    chunks = get_chunks(pdf_path, label)
    cache_key = f"{pathlib.Path(pdf_path).stem}_{LABEL_TO_CONFIG[label].cache_key}"
    embeddings = embed_chunks(chunks, model, cache_key)
    return build_index(embeddings)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.title("🔎 RAG Eval")
pdfs = list_pdfs()
if not pdfs:
    st.sidebar.error("No PDFs in data/pdf/. Add one to begin.")

sel_pdf = (
    st.sidebar.selectbox("PDF", pdfs, format_func=lambda p: p.split("/")[-1]) if pdfs else None
)
num_q = st.sidebar.slider("Questions per chunking config", 5, 30, 20, step=5)
sel_models = st.sidebar.multiselect("Embedding models", EMBEDDING_MODELS, default=EMBEDDING_MODELS)
sel_methods = st.sidebar.multiselect("Retrieval methods", ALL_METHODS, default=ALL_METHODS)
run_clicked = st.sidebar.button("▶ Run grid search", type="primary", use_container_width=True)
st.sidebar.caption(
    "A full run takes 15-25 min on the free QA model. For demos, use cached results."
)

tab_run, tab_results, tab_query = st.tabs(["Run", "Results", "Query Playground"])


# --------------------------------------------------------------------------- #
# Tab: Run
# --------------------------------------------------------------------------- #
with tab_run:
    st.subheader("Grid search")
    st.write(
        "Stages: **Parse → Chunk → Generate QA → Embed → Retrieve → Evaluate**, "
        "swept across chunking × embedding × retrieval."
    )
    if run_clicked and sel_pdf:
        config = GridSearchConfig(
            embedding_models=sel_models or EMBEDDING_MODELS,
            retrieval_methods=[RetrievalMethod(m) for m in (sel_methods or ALL_METHODS)],
            num_questions=num_q,
        )
        with run_with_progress("Running grid search…") as prog:
            results = run_grid_search(config, sel_pdf, on_event=prog.emit)
            if results:
                stem = sel_pdf.split("/")[-1].rsplit(".", 1)[0]
                save_results(results, RESULTS_DIR / f"{stem}_results.json")
                best = find_best_config(results)
                prog.complete(f"Done — {len(results)} experiments")
                st.success(f"Best by MRR: {best.experiment_id} (MRR={best.metrics.mrr:.3f})")
                st.caption("Saved. Open the Results tab.")
            else:
                prog.error("No results produced")
    elif run_clicked:
        st.warning("Add a PDF to data/pdf/ first.")
    else:
        st.info("Configure options in the sidebar and click **Run grid search**.")


# --------------------------------------------------------------------------- #
# Tab: Results
# --------------------------------------------------------------------------- #
with tab_results:
    files = load_result_files()
    if not files:
        st.info("No results yet. Run a grid search, or wait for a background run to finish.")
    else:
        c1, c2 = st.columns([3, 1])
        paper = c1.selectbox("Results file", list(files.keys()))
        if c2.button("↻ Refresh"):
            st.rerun()

        df = results_to_df(files[paper])
        best = df.loc[df["MRR"].idxmax()]

        metric_row(
            [
                ("Best MRR", f"{best['MRR']:.3f}"),
                ("Recall@5 (best)", f"{best['Recall@5']:.3f}"),
                ("Experiments", str(len(df))),
                ("Fastest (ms)", f"{df['ms'].min():.1f}"),
            ]
        )
        st.caption(
            f"Best → chunking **{best['chunking']}**, embedding **{best['embedding']}**, "
            f"retrieval **{best['retrieval']}**"
        )

        heat = df.groupby(["chunking", "retrieval"], as_index=False)["MRR"].mean()
        heatmap(heat, "retrieval", "chunking", "MRR", title="MRR — chunking × retrieval")

        df_sorted = df.sort_values("MRR", ascending=False)
        bar_chart(df_sorted, "MRR", "chunking", color="retrieval", title="MRR by configuration")
        results_table(
            df_sorted, highlight_cols=["MRR", "MAP", "Recall@5", "NDCG@5"], title="All experiments"
        )


# --------------------------------------------------------------------------- #
# Tab: Query Playground
# --------------------------------------------------------------------------- #
with tab_query:
    st.subheader("Query playground")
    st.caption("Type a question and retrieve top-k chunks live. Uses cached embeddings — instant.")
    if not sel_pdf:
        st.info("Add and select a PDF in the sidebar.")
    else:
        q1, q2, q3 = st.columns(3)
        label = q1.selectbox("Chunking", list(LABEL_TO_CONFIG.keys()))
        method = q2.selectbox("Retrieval", ALL_METHODS)
        model = q3.selectbox("Embedding model", EMBEDDING_MODELS)
        k = st.slider("Top-k", 1, 10, 5)
        alpha = (
            st.slider("Hybrid α (vector weight)", 0.0, 1.0, 0.5, step=0.1)
            if method == RetrievalMethod.HYBRID.value
            else 0.5
        )
        question = st.text_input(
            "Question", placeholder="e.g. What problem does this paper address?"
        )

        if st.button("Retrieve", type="primary") and question:
            try:
                chunks = get_chunks(sel_pdf, label)
                if method == RetrievalMethod.BM25.value:
                    result = retrieve_bm25(question, chunks, k, bm25=build_bm25(chunks))
                else:
                    index = get_index(sel_pdf, label, model)
                    qvec = embed_query(question, model)
                    if method == RetrievalMethod.VECTOR.value:
                        result = retrieve_vector(question, qvec, chunks, index, k)
                    else:
                        result = retrieve_hybrid(question, qvec, chunks, index, k, alpha)
            except FileNotFoundError:
                st.error("Embeddings not cached for this config yet. Run the grid search first.")
            else:
                by_id = {c.id: c for c in chunks}
                st.caption(
                    f"{len(result.retrieved_chunk_ids)} results in {result.time_taken * 1000:.1f} ms"
                )
                for rank, (cid, score) in enumerate(
                    zip(result.retrieved_chunk_ids, result.scores), start=1
                ):
                    chunk = by_id.get(cid)
                    if not chunk:
                        continue
                    with st.expander(
                        f"#{rank} · page {chunk.page_number} · score {score:.3f}",
                        expanded=rank <= 3,
                    ):
                        st.write(chunk.text)
