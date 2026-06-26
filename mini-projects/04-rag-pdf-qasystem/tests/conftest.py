"""Shared test fixtures and the faiss/torch OpenMP guard."""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from rag.models import Chunk, Document, Section  # noqa: E402


@pytest.fixture
def sample_document() -> Document:
    text = (
        "Introduction. Retrieval augmented generation combines retrieval with "
        "generation. Methods. We embed chunks and search with FAISS. "
        "Results. Hybrid retrieval outperforms dense alone on these papers."
    )
    sections = [
        Section(index=0, title="Introduction", start_char=0, end_char=70),
        Section(index=1, title="Methods", start_char=70, end_char=130),
        Section(index=2, title="Results", start_char=130, end_char=len(text)),
    ]
    return Document(doc_id="paper-1", text=text, title="A Test Paper", sections=sections)


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    return [
        Chunk(
            doc_id="paper-1",
            text="retrieval augmented generation",
            chunk_index=0,
            section_indices=[0],
        ),
        Chunk(
            doc_id="paper-1",
            text="embed chunks and search with faiss",
            chunk_index=1,
            section_indices=[1],
        ),
        Chunk(
            doc_id="paper-1",
            text="hybrid retrieval outperforms dense",
            chunk_index=2,
            section_indices=[2],
        ),
    ]


@pytest.fixture
def sample_embeddings() -> np.ndarray:
    return np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype="float32")
