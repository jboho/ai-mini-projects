"""Tests for the embedder (dims, normalization, caching) and FAISS vector store."""

from __future__ import annotations

import numpy as np

from rag.embedder import embed_chunks, get_embedder
from rag.vector_store import VectorStore


def test_vector_store_search_returns_nearest(sample_embeddings, sample_chunks):
    store = VectorStore.from_embeddings(sample_embeddings, sample_chunks)
    results = store.search(np.array([0.0, 1.0]), top_k=2)
    assert results[0].chunk_id == sample_chunks[1].id
    assert results[0].method == "dense"
    assert results[0].rank == 1
    assert all(-1.01 <= r.score <= 1.01 for r in results)


def test_vector_store_save_load_roundtrip(tmp_path, sample_embeddings, sample_chunks):
    store = VectorStore.from_embeddings(sample_embeddings, sample_chunks)
    store.save(tmp_path / "idx")
    loaded = VectorStore.load(tmp_path / "idx")
    assert loaded.index.ntotal == 3
    assert [c.id for c in loaded.chunks] == [c.id for c in sample_chunks]
    assert loaded.search(np.array([1.0, 0.0]), top_k=1)[0].chunk_id == sample_chunks[0].id


def test_embedder_dims_and_normalization():
    emb = get_embedder("sentence-transformers/all-MiniLM-L6-v2")
    vecs = emb.embed(["hello world", "a second sentence"])
    assert vecs.shape == (2, emb.dim)
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)


def test_embed_chunks_caches(tmp_path, sample_chunks):
    emb = get_embedder("sentence-transformers/all-MiniLM-L6-v2")
    first = embed_chunks(emb, sample_chunks, cache_key="k1", cache_dir=tmp_path)
    cache_files = list(tmp_path.glob("*.npz"))
    assert len(cache_files) == 1
    second = embed_chunks(emb, sample_chunks, cache_key="k1", cache_dir=tmp_path)
    assert np.array_equal(first, second)
