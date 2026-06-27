"""Streamlit QA app for the RAG PDF system.

Pick a configuration, index a slice of the corpus, ask a question, and see the
generated answer with inline citations and the source chunks.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from rag.config import ComponentConfig, RunConfig
from rag.loader import load_corpus
from rag.pipeline import RAGPipeline

st.set_page_config(page_title="RAG PDF QA", page_icon="📚", layout="wide")
st.title("📚 RAG PDF QA")
st.caption("Retrieval-augmented answers with citations over arXiv papers (Vectara benchmark).")

_CHUNKER_PARAMS = {
    "fixed": {"chunk_size": 256},
    "sliding": {"chunk_size": 256, "overlap": 64},
    "recursive": {"chunk_size": 512, "overlap": 64},
    "semantic": {"max_tokens": 384},
}
_EMBEDDERS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2",
]
_RERANKERS = ["none", "cross_encoder", "cohere"]


@st.cache_resource(show_spinner="Indexing corpus…")
def build_pipeline(chunker, embedder, retriever, reranker, top_k, n_docs):
    config = RunConfig(
        chunker=ComponentConfig(name=chunker, params=_CHUNKER_PARAMS[chunker]),
        embedder=embedder,
        retriever=ComponentConfig(name=retriever, params={"alpha": 0.5}),
        reranker=None if reranker == "none" else reranker,
        top_k=top_k,
    )
    documents = load_corpus()[:n_docs]
    return RAGPipeline(config, documents), len(documents)


st.sidebar.header("Configuration")
chunker = st.sidebar.selectbox("Chunking", list(_CHUNKER_PARAMS))
embedder = st.sidebar.selectbox("Embedding", _EMBEDDERS)
retriever = st.sidebar.selectbox("Retrieval", ["hybrid", "dense", "bm25"])
reranker = st.sidebar.selectbox("Reranker", _RERANKERS)
top_k = st.sidebar.slider("Top-k", 1, 10, 5)
n_docs = st.sidebar.slider("Papers to index", 5, 40, 20, step=5)

pipeline, n = build_pipeline(chunker, embedder, retriever, reranker, top_k, n_docs)
st.sidebar.success(f"Indexed {n} papers")

mode = st.radio("Mode", ["Answer (LLM)", "Retrieve only"], horizontal=True)
question = st.text_input(
    "Question", placeholder="e.g. What challenges arise in inverter-based grids?"
)

if st.button("Run", type="primary") and question:
    if mode == "Retrieve only":
        results = pipeline.retrieve(question)
        st.caption(f"{len(results)} chunks")
        for r in results:
            with st.expander(f"#{r.rank} · {r.doc_id} · score {r.score:.3f}"):
                st.write(r.text)
    else:
        with st.spinner("Generating…"):
            response = pipeline.answer(question)
        st.markdown(f"### Answer\n{response.answer}")
        if response.citations:
            st.markdown("##### Citations")
            for c in response.citations:
                with st.expander(f"[{c.marker}] {c.doc_id}"):
                    st.write(c.text)
        with st.expander("All retrieved chunks"):
            for r in response.retrieved:
                st.markdown(f"**#{r.rank} · {r.doc_id} · {r.score:.3f}**")
                st.caption(r.text[:300])
