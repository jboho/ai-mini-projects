"""Chunking strategies: fixed, sliding, recursive, semantic.

All chunkers operate on the document's character offsets (so every chunk maps
back to its source sections) and size chunks by tiktoken token count. Section
ids are assigned by span overlap for qrel ground-truth matching.
"""

from __future__ import annotations

import re

import tiktoken

from .config import ComponentConfig
from .interfaces import BaseChunker
from .loader import sections_for_span
from .models import Chunk, Document

_ENC = tiktoken.get_encoding("cl100k_base")
_WORD_RE = re.compile(r"\S+")
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$")


def token_len(text: str) -> int:
    return len(_ENC.encode(text))


def _word_spans(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in _WORD_RE.finditer(text)]


def _sentence_spans(text: str) -> list[tuple[str, int, int]]:
    out = []
    for m in _SENTENCE_RE.finditer(text):
        s = m.group().strip()
        if s:
            start = m.start() + (len(m.group()) - len(m.group().lstrip()))
            out.append((s, start, start + len(s)))
    return out


class _BaseOffsetChunker(BaseChunker):
    """Shared chunk construction with section assignment."""

    def _make(self, document: Document, text: str, start: int, end: int, index: int) -> Chunk:
        return Chunk(
            doc_id=document.doc_id,
            text=text,
            chunk_index=index,
            start_char=start,
            end_char=end,
            section_indices=sections_for_span(document.sections, start, end),
            method=self.name,
        )


class FixedSizeChunker(_BaseOffsetChunker):
    """Token-sized windows over words, with optional token overlap."""

    name = "fixed"

    def __init__(self, chunk_size: int = 256, overlap: int = 0) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> list[Chunk]:
        words = _word_spans(document.text)
        if not words:
            return []
        tok = [token_len(w) for w, _, _ in words]

        chunks: list[Chunk] = []
        i = 0
        index = 0
        n = len(words)
        while i < n:
            j, budget = i, 0
            while j < n and budget < self.chunk_size:
                budget += tok[j]
                j += 1
            start = words[i][1]
            end = words[j - 1][2]
            chunks.append(self._make(document, document.text[start:end], start, end, index))
            index += 1
            if j >= n:
                break
            i = self._advance(i, j, tok)
        return chunks

    def _advance(self, i: int, j: int, tok: list[int]) -> int:
        if self.overlap <= 0:
            return j
        back, budget = j, 0
        while back > i + 1 and budget < self.overlap:
            back -= 1
            budget += tok[back]
        return back


class SlidingWindowChunker(FixedSizeChunker):
    """Fixed windows with a non-zero overlap (a sliding window)."""

    name = "sliding"

    def __init__(self, chunk_size: int = 256, overlap: int = 64) -> None:
        super().__init__(chunk_size=chunk_size, overlap=max(1, overlap))


class RecursiveChunker(_BaseOffsetChunker):
    """Greedy packing that prefers to break on sentence then word boundaries."""

    name = "recursive"

    def __init__(self, chunk_size: int = 512, overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> list[Chunk]:
        sentences = _sentence_spans(document.text)
        if not sentences:
            return []

        chunks: list[Chunk] = []
        index = 0
        buf: list[tuple[str, int, int]] = []
        budget = 0
        for sent, start, end in sentences:
            stoks = token_len(sent)
            if buf and budget + stoks > self.chunk_size:
                index = self._flush(document, buf, index, chunks)
                buf, budget = self._carry(buf), 0
                budget = sum(token_len(s) for s, _, _ in buf)
            buf.append((sent, start, end))
            budget += stoks
        if buf:
            self._flush(document, buf, index, chunks)
        return chunks

    def _carry(self, buf: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
        if self.overlap <= 0:
            return []
        carried: list[tuple[str, int, int]] = []
        budget = 0
        for item in reversed(buf):
            if budget >= self.overlap:
                break
            carried.insert(0, item)
            budget += token_len(item[0])
        return carried

    def _flush(self, document: Document, buf, index: int, chunks: list[Chunk]) -> int:
        start = buf[0][1]
        end = buf[-1][2]
        chunks.append(self._make(document, document.text[start:end], start, end, index))
        return index + 1


class SemanticChunker(_BaseOffsetChunker):
    """Group sentences up to a token budget (sentence-boundary semantic units).

    When an embedder is supplied, breakpoints are placed where adjacent-sentence
    cosine similarity dips; otherwise it falls back to token-budget grouping.
    """

    name = "semantic"

    def __init__(
        self, max_tokens: int = 384, embedder=None, breakpoint_percentile: int = 25
    ) -> None:
        self.max_tokens = max_tokens
        self.embedder = embedder
        self.breakpoint_percentile = breakpoint_percentile

    def chunk(self, document: Document) -> list[Chunk]:
        sentences = _sentence_spans(document.text)
        if not sentences:
            return []
        breakpoints = self._breakpoints(sentences) if self.embedder else set()

        chunks: list[Chunk] = []
        index = 0
        buf: list[tuple[str, int, int]] = []
        budget = 0
        for pos, (sent, start, end) in enumerate(sentences):
            stoks = token_len(sent)
            over_budget = buf and budget + stoks > self.max_tokens
            if over_budget or (pos in breakpoints and buf):
                index = self._flush(document, buf, index, chunks)
                buf, budget = [], 0
            buf.append((sent, start, end))
            budget += stoks
        if buf:
            self._flush(document, buf, index, chunks)
        return chunks

    def _breakpoints(self, sentences) -> set[int]:
        import numpy as np

        vecs = self.embedder.embed([s for s, _, _ in sentences])
        sims = [float(np.dot(vecs[i], vecs[i + 1])) for i in range(len(vecs) - 1)]
        if not sims:
            return set()
        threshold = float(np.percentile(sims, self.breakpoint_percentile))
        return {i + 1 for i, s in enumerate(sims) if s < threshold}

    def _flush(self, document: Document, buf, index: int, chunks: list[Chunk]) -> int:
        start = buf[0][1]
        end = buf[-1][2]
        chunks.append(self._make(document, document.text[start:end], start, end, index))
        return index + 1


_CHUNKERS = {
    "fixed": FixedSizeChunker,
    "sliding": SlidingWindowChunker,
    "recursive": RecursiveChunker,
    "semantic": SemanticChunker,
}


def get_chunker(config: ComponentConfig, embedder=None) -> BaseChunker:
    """Instantiate a chunker from config; pass ``embedder`` for semantic mode."""
    cls = _CHUNKERS.get(config.name)
    if cls is None:
        raise ValueError(f"Unknown chunker: {config.name}")
    params = dict(config.params)
    if config.name == "semantic" and embedder is not None:
        params["embedder"] = embedder
    return cls(**params)
