"""Tests for BM25, vector, and hybrid retrieval (offline, no API)."""

from __future__ import annotations

import numpy as np

from pipeline.models import Chunk
from pipeline.retriever import retrieve_bm25, retrieve_hybrid, retrieve_vector
from pipeline.vectorstore import build_index


def _chunks() -> list[Chunk]:
    return [
        Chunk(text="the cat sat on the mat", chunk_index=0),
        Chunk(text="python programming language tutorial", chunk_index=1),
        Chunk(text="machine learning models and data", chunk_index=2),
    ]


def test_bm25_returns_keyword_match_first():
    chunks = _chunks()
    result = retrieve_bm25("python language", chunks, k=3)
    assert result.retrieved_chunk_ids[0] == chunks[1].id
    assert result.method == "bm25"
    assert len(result.scores) == len(result.retrieved_chunk_ids)


def test_vector_returns_nearest_embedding():
    chunks = _chunks()
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype="float32")
    index = build_index(embeddings)

    result = retrieve_vector("q", np.array([0.0, 1.0]), chunks, index, k=2)
    assert result.retrieved_chunk_ids[0] == chunks[1].id
    assert result.method == "vector"


def test_hybrid_combines_both_signals():
    chunks = _chunks()
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype="float32")
    index = build_index(embeddings)

    # query embedding favors chunk 1; keyword 'python' also favors chunk 1
    result = retrieve_hybrid("python", np.array([0.0, 1.0]), chunks, index, k=3, alpha=0.5)
    assert result.method == "hybrid"
    assert result.retrieved_chunk_ids[0] == chunks[1].id
    assert len(result.retrieved_chunk_ids) == 3
