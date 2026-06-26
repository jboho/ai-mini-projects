"""Tests for chunking strategies: boundaries, overlap, page mapping."""

from __future__ import annotations

from pipeline.chunker import (
    chunk_by_sentence,
    chunk_fixed_size,
    chunk_semantic,
    create_chunks,
)
from pipeline.config import ChunkingConfig, ChunkMethod
from pipeline.models import PageText


def _single_page(text: str) -> list[PageText]:
    return [PageText(page_number=1, text=text, start_char=0, end_char=len(text))]


def test_fixed_size_word_window_and_overlap():
    text = " ".join(f"w{i}" for i in range(10))
    pages = _single_page(text)
    chunks = chunk_fixed_size(text, chunk_size=4, overlap=1, pages=pages)

    assert len(chunks) == 3
    assert chunks[0].text.split() == ["w0", "w1", "w2", "w3"]
    # overlap of 1: last word of chunk 0 is first word of chunk 1
    assert chunks[0].text.split()[-1] == chunks[1].text.split()[0]
    assert all(c.page_number == 1 for c in chunks)
    assert all(c.method == ChunkMethod.FIXED_SIZE.value for c in chunks)


def test_fixed_size_rejects_bad_overlap():
    pages = _single_page("a b c")
    try:
        chunk_fixed_size("a b c", chunk_size=2, overlap=2, pages=pages)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_sentence_chunking_counts_and_overlap():
    text = "Alpha one. Beta two. Gamma three. Delta four. Epsilon five."
    pages = _single_page(text)
    chunks = chunk_by_sentence(text, sentences_per_chunk=2, overlap_sentences=1, pages=pages)

    assert len(chunks) == 4
    assert "Alpha" in chunks[0].text and "Beta" in chunks[0].text
    # overlapping sentence appears in consecutive chunks
    assert "Beta" in chunks[1].text


def test_semantic_chunking_respects_token_budget():
    text = "One two three. Four five six. Seven eight nine. Ten eleven twelve."
    pages = _single_page(text)
    chunks = chunk_semantic(text, max_tokens=6, pages=pages)

    assert chunks
    assert all(c.text.strip() for c in chunks)
    assert all(c.text in text for c in chunks)


def test_create_chunks_dispatch():
    text = " ".join(f"word{i}" for i in range(20))
    pages = _single_page(text)
    cfg = ChunkingConfig(method=ChunkMethod.FIXED_SIZE, chunk_size=5, overlap=0)
    chunks = create_chunks(text, cfg, pages)
    assert chunks
    assert chunks[0].method == ChunkMethod.FIXED_SIZE.value
