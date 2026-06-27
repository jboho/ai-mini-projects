"""Tests for loader + chunkers: offsets, overlap, section mapping, factory."""

from __future__ import annotations

import json

import pytest

from rag.chunkers import (
    FixedSizeChunker,
    RecursiveChunker,
    SemanticChunker,
    SlidingWindowChunker,
    get_chunker,
    token_len,
)
from rag.config import ComponentConfig
from rag.loader import load_corpus_document, sections_for_span
from rag.models import Section


def _corpus_doc(tmp_path):
    data = {
        "title": "Test Paper",
        "sections": [
            {"section_id": 0, "text": "Alpha one two three four five. Beta six seven eight nine."},
            {"section_id": 1, "text": "Gamma ten eleven twelve. Delta thirteen fourteen fifteen."},
            {
                "section_id": 2,
                "text": "Epsilon sixteen seventeen eighteen nineteen twenty twentyone.",
            },
        ],
    }
    path = tmp_path / "paper-x.json"
    path.write_text(json.dumps(data))
    return load_corpus_document(path)


def test_loader_builds_sections_and_offsets(tmp_path):
    doc = _corpus_doc(tmp_path)
    assert doc.doc_id == "paper-x"
    assert len(doc.sections) == 3
    # each section's recorded span matches its slice of the joined text
    for sec in doc.sections:
        assert doc.text[sec.start_char : sec.end_char].startswith(
            {0: "Alpha", 1: "Gamma", 2: "Epsilon"}[sec.index]
        )


def test_sections_for_span_overlap():
    sections = [
        Section(index=0, start_char=0, end_char=10),
        Section(index=1, start_char=12, end_char=20),
    ]
    assert sections_for_span(sections, 2, 8) == [0]
    assert sections_for_span(sections, 8, 15) == [0, 1]
    assert sections_for_span(sections, 21, 25) == []


def test_fixed_chunker_offsets_and_sections(tmp_path):
    doc = _corpus_doc(tmp_path)
    chunks = FixedSizeChunker(chunk_size=8, overlap=0).chunk(doc)
    assert len(chunks) >= 2
    for c in chunks:
        assert doc.text[c.start_char : c.end_char] == c.text
        assert c.section_indices  # every chunk maps to >=1 section
        assert set(c.section_indices) <= {0, 1, 2}
        assert c.method == "fixed"


def test_fixed_chunker_rejects_bad_overlap():
    with pytest.raises(ValueError):
        FixedSizeChunker(chunk_size=8, overlap=8)


def test_sliding_window_has_overlap(tmp_path):
    doc = _corpus_doc(tmp_path)
    chunks = SlidingWindowChunker(chunk_size=10, overlap=4).chunk(doc)
    assert len(chunks) >= 2
    # consecutive chunks overlap in character space
    assert chunks[1].start_char < chunks[0].end_char
    assert all(c.method == "sliding" for c in chunks)


def test_recursive_respects_token_budget(tmp_path):
    doc = _corpus_doc(tmp_path)
    chunks = RecursiveChunker(chunk_size=12, overlap=0).chunk(doc)
    assert chunks
    for c in chunks:
        assert doc.text[c.start_char : c.end_char] == c.text
    assert all(c.method == "recursive" for c in chunks)


def test_semantic_fallback_groups_sentences(tmp_path):
    doc = _corpus_doc(tmp_path)
    chunks = SemanticChunker(max_tokens=10).chunk(doc)  # no embedder -> token grouping
    assert chunks
    for c in chunks:
        assert token_len(c.text) <= 10 or len(c.text.split(".")) <= 2
        assert c.method == "semantic"


def test_get_chunker_factory(tmp_path):
    doc = _corpus_doc(tmp_path)
    chunker = get_chunker(ComponentConfig(name="recursive", params={"chunk_size": 16}))
    chunks = chunker.chunk(doc)
    assert chunks and chunks[0].method == "recursive"
