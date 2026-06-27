"""Retrieval methods: BM25 (lexical), vector (semantic), and hybrid fusion.

Retrievers are pure with respect to the embedding API: vector and hybrid take a
precomputed ``query_embedding`` so the embedding/network concern stays in
``embedder.py`` and these functions remain unit-testable offline.

Hybrid fusion min-max normalizes BM25 and cosine scores across the full chunk
set, then combines as ``alpha * vector + (1 - alpha) * bm25``.
"""

from __future__ import annotations

import re
import time

import numpy as np
from rank_bm25 import BM25Okapi

from .config import RetrievalMethod
from .models import Chunk, RetrievalResult
from .vectorstore import search_index

_TOKEN_RE = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def build_bm25(chunks: list[Chunk]) -> BM25Okapi:
    """Build a BM25 index over chunk texts (reusable across embedding models)."""
    return BM25Okapi([tokenize(chunk.text) for chunk in chunks])


def _min_max_normalize(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    lo, hi = float(scores.min()), float(scores.max())
    if hi - lo < 1e-12:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


def _top_k(chunks: list[Chunk], scores: np.ndarray, k: int) -> tuple[list[str], list[float]]:
    k = min(k, len(chunks))
    order = np.argsort(-scores)[:k]
    return [chunks[i].id for i in order], [float(scores[i]) for i in order]


def retrieve_bm25(
    query: str, chunks: list[Chunk], k: int, bm25: BM25Okapi | None = None
) -> RetrievalResult:
    start = time.perf_counter()
    bm25 = bm25 or build_bm25(chunks)
    scores = np.asarray(bm25.get_scores(tokenize(query)), dtype="float32")
    ids, top_scores = _top_k(chunks, scores, k)
    return RetrievalResult(
        query=query,
        retrieved_chunk_ids=ids,
        scores=top_scores,
        method=RetrievalMethod.BM25.value,
        time_taken=time.perf_counter() - start,
    )


def retrieve_vector(
    query: str, query_embedding: np.ndarray, chunks: list[Chunk], index, k: int
) -> RetrievalResult:
    start = time.perf_counter()
    scores, indices = search_index(index, query_embedding, k)
    ids = [chunks[i].id for i in indices if i >= 0]
    return RetrievalResult(
        query=query,
        retrieved_chunk_ids=ids,
        scores=[float(s) for s in scores[: len(ids)]],
        method=RetrievalMethod.VECTOR.value,
        time_taken=time.perf_counter() - start,
    )


def retrieve_hybrid(
    query: str,
    query_embedding: np.ndarray,
    chunks: list[Chunk],
    index,
    k: int,
    alpha: float = 0.5,
    bm25: BM25Okapi | None = None,
) -> RetrievalResult:
    start = time.perf_counter()

    bm25 = bm25 or build_bm25(chunks)
    bm25_scores = np.asarray(bm25.get_scores(tokenize(query)), dtype="float32")

    vec_scores = np.zeros(len(chunks), dtype="float32")
    scores, indices = search_index(index, query_embedding, len(chunks))
    for score, idx in zip(scores, indices):
        if idx >= 0:
            vec_scores[idx] = score

    combined = alpha * _min_max_normalize(vec_scores) + (1 - alpha) * _min_max_normalize(
        bm25_scores
    )
    ids, top_scores = _top_k(chunks, combined, k)
    return RetrievalResult(
        query=query,
        retrieved_chunk_ids=ids,
        scores=top_scores,
        method=RetrievalMethod.HYBRID.value,
        time_taken=time.perf_counter() - start,
    )
