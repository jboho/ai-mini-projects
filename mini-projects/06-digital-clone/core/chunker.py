"""Text chunking for the RAG knowledge base (500 chars, 50 overlap)."""

from __future__ import annotations

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .models import KnowledgeChunk

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    source_topic: str = "",
    source_field: str = "",
    chunk_size: int = 500,
    overlap: int = 50,
    start_index: int = 0,
) -> list[KnowledgeChunk]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks: list[KnowledgeChunk] = []
    for i, piece in enumerate(splitter.split_text(text)):
        idx = start_index + i
        chunks.append(
            KnowledgeChunk(
                chunk_id=f"{source_topic or 'doc'}_{idx}",
                content=piece,
                source_topic=source_topic,
                source_field=source_field,
                chunk_index=idx,
            )
        )
    return chunks


def load_textbook_chunks(
    field: str = "computer science",
    target_chunks: int = 900,
    dataset: str = "open-phi/textbooks",
) -> list[KnowledgeChunk]:
    """Stream textbooks of a given field and chunk until target_chunks reached."""
    from datasets import load_dataset

    logger.info("Streaming %s (field=%s)...", dataset, field)
    stream = load_dataset(dataset, split="train", streaming=True)
    chunks: list[KnowledgeChunk] = []
    for record in stream:
        if field and str(record.get("field", "")).lower() != field.lower():
            continue
        text = record.get("markdown") or record.get("text") or record.get("content") or ""
        topic = str(record.get("topic") or record.get("title") or "topic")
        chunks.extend(
            chunk_text(text, source_topic=topic, source_field=field, start_index=len(chunks))
        )
        if len(chunks) >= target_chunks:
            break
    logger.info("Built %d knowledge chunks", len(chunks))
    return chunks[:target_chunks]
