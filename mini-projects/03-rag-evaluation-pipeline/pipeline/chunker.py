"""Chunking strategies: fixed-size (word window), sentence, and semantic.

All strategies return :class:`Chunk` objects carrying char offsets and the
source page number, so retrieval results stay traceable to the document.

Sentence segmentation uses a deterministic regex by default (offline, stable
for tests). Semantic chunking uses spaCy sentence boundaries when the model is
available and falls back to the regex splitter otherwise.
"""

from __future__ import annotations

import logging
import re

from .config import ChunkingConfig, ChunkMethod
from .models import Chunk, PageText
from .parser import page_for_offset

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"\S+")
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$")

_SPACY_NLP = None


def _split_sentences(text: str) -> list[tuple[str, int]]:
    """Return ``(sentence, start_char)`` pairs using a deterministic regex."""
    sentences: list[tuple[str, int]] = []
    for match in _SENTENCE_RE.finditer(text):
        sentence = match.group().strip()
        if sentence:
            sentences.append((sentence, match.start()))
    return sentences


def _get_spacy():
    global _SPACY_NLP
    if _SPACY_NLP is None:
        try:
            import spacy

            _SPACY_NLP = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
        except (ImportError, OSError):
            logger.warning("spaCy model unavailable; semantic chunking uses regex fallback")
            _SPACY_NLP = False
    return _SPACY_NLP


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _make_chunk(
    text: str, start: int, end: int, index: int, pages: list[PageText], method: str
) -> Chunk:
    return Chunk(
        text=text,
        page_number=page_for_offset(pages, start),
        chunk_index=index,
        start_char=start,
        end_char=end,
        method=method,
    )


def chunk_fixed_size(
    text: str, chunk_size: int, overlap: int, pages: list[PageText]
) -> list[Chunk]:
    """Sliding window of ``chunk_size`` words with ``overlap`` words of carryover."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = list(_WORD_RE.finditer(text))
    if not words:
        return []

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    index = 0
    for window_start in range(0, len(words), step):
        window = words[window_start : window_start + chunk_size]
        if not window:
            break
        start = window[0].start()
        end = window[-1].end()
        chunks.append(
            _make_chunk(text[start:end], start, end, index, pages, ChunkMethod.FIXED_SIZE.value)
        )
        index += 1
        if window_start + chunk_size >= len(words):
            break
    return chunks


def chunk_by_sentence(
    text: str, sentences_per_chunk: int, overlap_sentences: int, pages: list[PageText]
) -> list[Chunk]:
    """Group ``sentences_per_chunk`` sentences with ``overlap_sentences`` carryover."""
    if overlap_sentences >= sentences_per_chunk:
        raise ValueError("overlap_sentences must be smaller than sentences_per_chunk")

    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: list[Chunk] = []
    step = sentences_per_chunk - overlap_sentences
    index = 0
    for group_start in range(0, len(sentences), step):
        group = sentences[group_start : group_start + sentences_per_chunk]
        if not group:
            break
        start = group[0][1]
        last_sentence, last_start = group[-1]
        end = last_start + len(last_sentence)
        chunks.append(
            _make_chunk(text[start:end], start, end, index, pages, ChunkMethod.SENTENCE.value)
        )
        index += 1
        if group_start + sentences_per_chunk >= len(sentences):
            break
    return chunks


def chunk_semantic(text: str, max_tokens: int, pages: list[PageText]) -> list[Chunk]:
    """Accumulate sentences up to ``max_tokens`` words, respecting boundaries."""
    nlp = _get_spacy()
    if nlp:
        doc = nlp(text)
        sentences = [
            (sent.text.strip(), sent.start_char) for sent in doc.sents if sent.text.strip()
        ]
    else:
        sentences = _split_sentences(text)

    if not sentences:
        return []

    chunks: list[Chunk] = []
    index = 0
    buffer: list[tuple[str, int]] = []
    buffer_tokens = 0

    def flush() -> None:
        nonlocal index, buffer, buffer_tokens
        if not buffer:
            return
        start = buffer[0][1]
        last_sentence, last_start = buffer[-1]
        end = last_start + len(last_sentence)
        chunks.append(
            _make_chunk(text[start:end], start, end, index, pages, ChunkMethod.SEMANTIC.value)
        )
        index += 1
        buffer = []
        buffer_tokens = 0

    for sentence, start in sentences:
        tokens = _word_count(sentence)
        if buffer and buffer_tokens + tokens > max_tokens:
            flush()
        buffer.append((sentence, start))
        buffer_tokens += tokens
    flush()
    return chunks


def create_chunks(text: str, config: ChunkingConfig, pages: list[PageText]) -> list[Chunk]:
    """Dispatch to the chunking strategy named by ``config.method``."""
    if config.method == ChunkMethod.FIXED_SIZE:
        return chunk_fixed_size(text, config.chunk_size, config.overlap, pages)
    if config.method == ChunkMethod.SENTENCE:
        return chunk_by_sentence(text, config.sentences_per_chunk, config.overlap_sentences, pages)
    if config.method == ChunkMethod.SEMANTIC:
        return chunk_semantic(text, config.max_tokens, pages)
    raise ValueError(f"Unknown chunk method: {config.method}")
