"""Tests for citation extraction (offline, no API)."""

from __future__ import annotations

from rag.generator import build_context, extract_citations
from rag.models import Chunk


def _chunks() -> list[Chunk]:
    return [
        Chunk(doc_id="d", text="first passage about cats", chunk_index=0, page_number=1),
        Chunk(doc_id="d", text="second passage about dogs", chunk_index=1, page_number=2),
        Chunk(doc_id="d", text="third passage about birds", chunk_index=2, page_number=3),
    ]


def test_extract_citations_maps_markers():
    chunks = _chunks()
    cites = extract_citations("Cats sleep a lot [1]. Dogs bark [2].", chunks)
    assert [c.marker for c in cites] == [1, 2]
    assert cites[0].chunk_id == chunks[0].id
    assert cites[1].doc_id == "d" and cites[1].page_number == 2


def test_extract_citations_dedupes_and_orders():
    chunks = _chunks()
    cites = extract_citations("A [2] B [1] C [2] again", chunks)
    assert [c.marker for c in cites] == [2, 1]


def test_extract_citations_ignores_out_of_range():
    chunks = _chunks()
    cites = extract_citations("Claim [9] and [0] and [2]", chunks)
    assert [c.marker for c in cites] == [2]


def test_extract_citations_none():
    assert extract_citations("No citations here.", _chunks()) == []


def test_build_context_numbers_chunks():
    ctx = build_context(_chunks())
    assert ctx.startswith("[1] first passage")
    assert "[2] second passage" in ctx
    assert "[3] third passage" in ctx
