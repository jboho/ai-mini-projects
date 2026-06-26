"""Tests for the FAISS knowledge store."""

from __future__ import annotations

from core.vectorstore import KnowledgeStore


def test_build_and_search(sample_chunks):
    store = KnowledgeStore.build(sample_chunks)
    results = store.search("how does a neural network learn?", k=2)
    assert len(results) == 2
    # the neural-network chunk should rank first for this query
    assert results[0][0].chunk_id == "c0"
    assert -1.01 <= results[0][1] <= 1.01


def test_save_load_roundtrip(tmp_path, sample_chunks):
    store = KnowledgeStore.build(sample_chunks)
    store.save(tmp_path)
    loaded = KnowledgeStore.load(tmp_path)
    assert loaded.index.ntotal == 3
    assert [c.chunk_id for c in loaded.chunks] == [c.chunk_id for c in sample_chunks]
    assert loaded.search("hash table lookup", k=1)[0][0].chunk_id == "c1"
