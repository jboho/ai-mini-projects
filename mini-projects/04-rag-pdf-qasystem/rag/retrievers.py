"""Retrieval: dense (vector), BM25 (lexical), and hybrid fusion.

Dense uses the embedder + FAISS store; BM25 is lexical over chunk texts. Hybrid
min-max normalizes both score sets across the full chunk set and combines as
``alpha * dense + (1 - alpha) * bm25``.
"""

from __future__ import annotations

import re

import numpy as np
from rank_bm25 import BM25Okapi

from .config import ComponentConfig
from .interfaces import BaseEmbedder, BaseRetriever
from .models import Chunk, RetrievalResult
from .vector_store import VectorStore

_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _min_max(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    lo, hi = float(scores.min()), float(scores.max())
    if hi - lo < 1e-12:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


class DenseRetriever(BaseRetriever):
    name = "dense"

    def __init__(self, embedder: BaseEmbedder, store: VectorStore) -> None:
        self.embedder = embedder
        self.store = store

    def retrieve(self, query: str, top_k: int) -> list[RetrievalResult]:
        query_vec = self.embedder.embed([query])[0]
        return self.store.search(query_vec, top_k)


class BM25Retriever(BaseRetriever):
    name = "bm25"

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.bm25 = BM25Okapi([_tokenize(c.text) for c in chunks])

    def retrieve(self, query: str, top_k: int) -> list[RetrievalResult]:
        scores = np.asarray(self.bm25.get_scores(_tokenize(query)), dtype="float32")
        order = np.argsort(-scores)[:top_k]
        return [
            RetrievalResult(
                chunk_id=self.chunks[i].id,
                doc_id=self.chunks[i].doc_id,
                score=float(scores[i]),
                rank=rank,
                text=self.chunks[i].text,
                method="bm25",
            )
            for rank, i in enumerate(order, start=1)
        ]


class HybridRetriever(BaseRetriever):
    name = "hybrid"

    def __init__(
        self, embedder: BaseEmbedder, store: VectorStore, chunks: list[Chunk], alpha: float = 0.5
    ) -> None:
        self.chunks = chunks
        self.alpha = alpha
        self.embedder = embedder
        self.store = store
        self.bm25 = BM25Okapi([_tokenize(c.text) for c in chunks])

    def retrieve(self, query: str, top_k: int) -> list[RetrievalResult]:
        n = len(self.chunks)
        bm25_scores = np.asarray(self.bm25.get_scores(_tokenize(query)), dtype="float32")

        dense_scores = np.zeros(n, dtype="float32")
        id_to_pos = {c.id: i for i, c in enumerate(self.chunks)}
        for res in self.store.search(self.embedder.embed([query])[0], n):
            dense_scores[id_to_pos[res.chunk_id]] = res.score

        combined = self.alpha * _min_max(dense_scores) + (1 - self.alpha) * _min_max(bm25_scores)
        order = np.argsort(-combined)[:top_k]
        return [
            RetrievalResult(
                chunk_id=self.chunks[i].id,
                doc_id=self.chunks[i].doc_id,
                score=float(combined[i]),
                rank=rank,
                text=self.chunks[i].text,
                method="hybrid",
            )
            for rank, i in enumerate(order, start=1)
        ]


def get_retriever(
    config: ComponentConfig,
    embedder: BaseEmbedder,
    store: VectorStore,
    chunks: list[Chunk],
) -> BaseRetriever:
    if config.name == "dense":
        return DenseRetriever(embedder, store)
    if config.name == "bm25":
        return BM25Retriever(chunks)
    if config.name == "hybrid":
        return HybridRetriever(embedder, store, chunks, alpha=config.params.get("alpha", 0.5))
    raise ValueError(f"Unknown retriever: {config.name}")
