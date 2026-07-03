"""Tests for text chunking."""

from __future__ import annotations

from core.chunker import chunk_text


def test_chunk_text_boundaries_and_metadata():
    text = " ".join(f"word{i}" for i in range(400))  # well over 500 chars
    chunks = chunk_text(text, source_topic="algorithms", source_field="computer science")
    assert len(chunks) >= 2
    assert all(len(c.content) <= 520 for c in chunks)  # ~chunk_size + slack
    assert all(c.source_field == "computer science" for c in chunks)
    assert chunks[0].chunk_id == "algorithms_0"
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_start_index_offsets():
    chunks = chunk_text("a " * 600, source_topic="t", start_index=10)
    assert chunks[0].chunk_index == 10
