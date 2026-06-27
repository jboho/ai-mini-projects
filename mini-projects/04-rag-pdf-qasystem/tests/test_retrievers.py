"""Tests for dense, BM25, and hybrid retrievers (offline, fake embedder)."""

from __future__ import annotations

import numpy as np

from rag.config import ComponentConfig
from rag.interfaces import BaseEmbedder
from rag.models import Chunk
from rag.retrievers import BM25Retriever, DenseRetriever, HybridRetriever, get_retriever
from rag.vector_store import VectorStore


class FakeEmbedder(BaseEmbedder):
    """Deterministic 2D embedder: maps known keywords to fixed vectors."""

    name = "fake"
    _MAP = {"cat": [1.0, 0.0], "python": [0.0, 1.0], "machine": [1.0, 1.0]}

    @property
    def dim(self) -> int:
        return 2

    def embed(self, texts: list[str]) -> np.ndarray:
        out = []
        for t in texts:
            vec = [0.1, 0.1]
            for key, v in self._MAP.items():
                if key in t.lower():
                    vec = v
            out.append(vec)
        return np.asarray(out, dtype="float32")


def _chunks() -> list[Chunk]:
    return [
        Chunk(doc_id="d", text="the cat sat on the mat", chunk_index=0),
        Chunk(doc_id="d", text="python programming language", chunk_index=1),
        Chunk(doc_id="d", text="machine learning models", chunk_index=2),
    ]


def test_bm25_keyword_match():
    chunks = _chunks()
    res = BM25Retriever(chunks).retrieve("python language", top_k=3)
    assert res[0].chunk_id == chunks[1].id
    assert res[0].method == "bm25"


def test_dense_nearest():
    chunks = _chunks()
    emb = FakeEmbedder()
    store = VectorStore.from_embeddings(emb.embed([c.text for c in chunks]), chunks)
    res = DenseRetriever(emb, store).retrieve("python", top_k=2)
    assert res[0].chunk_id == chunks[1].id
    assert res[0].method == "dense"


def test_hybrid_combines():
    chunks = _chunks()
    emb = FakeEmbedder()
    store = VectorStore.from_embeddings(emb.embed([c.text for c in chunks]), chunks)
    res = HybridRetriever(emb, store, chunks, alpha=0.5).retrieve("python", top_k=3)
    assert res[0].chunk_id == chunks[1].id
    assert len(res) == 3
    assert res[0].method == "hybrid"


def test_get_retriever_factory():
    chunks = _chunks()
    emb = FakeEmbedder()
    store = VectorStore.from_embeddings(emb.embed([c.text for c in chunks]), chunks)
    r = get_retriever(ComponentConfig(name="bm25"), emb, store, chunks)
    assert isinstance(r, BM25Retriever)
