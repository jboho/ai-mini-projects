"""Abstract base classes for swappable RAG components.

Each concrete implementation lives in its module (chunkers.py, embedder.py,
retrievers.py, rerankers.py, generator.py) and is instantiated from YAML config
by that module's factory function.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .models import Chunk, Document, QAResponse, RetrievalResult


class BaseChunker(ABC):
    name: str = "base"

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Split a document into chunks carrying offset + section metadata."""


class BaseEmbedder(ABC):
    name: str = "base"

    @property
    @abstractmethod
    def dim(self) -> int:
        """Embedding dimensionality."""

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an ``(len(texts), dim)`` float32 array."""


class BaseRetriever(ABC):
    name: str = "base"

    @abstractmethod
    def retrieve(self, query: str, top_k: int) -> list[RetrievalResult]:
        """Return up to ``top_k`` ranked results for a query."""


class BaseReranker(ABC):
    name: str = "base"

    @abstractmethod
    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        """Re-score and reorder candidate results, returning the top ``top_k``."""


class BaseGenerator(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, question: str, chunks: list[Chunk]) -> QAResponse:
        """Generate an answer with citations from retrieved chunks."""
