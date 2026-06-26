"""FAISS knowledge store: embed chunks, search, persist.

Embeddings are L2-normalized so an inner-product index yields cosine similarity.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import faiss
import numpy as np

from .embedder import embed_texts
from .models import KnowledgeChunk

logger = logging.getLogger(__name__)
faiss.omp_set_num_threads(1)

RAG_DIR = Path(__file__).resolve().parent.parent / "data" / "rag"


def _normalize(vectors: np.ndarray) -> np.ndarray:
    array = np.asarray(vectors, dtype="float32")
    if array.ndim == 1:
        array = array.reshape(1, -1)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return array / norms


class KnowledgeStore:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: list[KnowledgeChunk] = []

    @classmethod
    def build(cls, chunks: list[KnowledgeChunk]) -> KnowledgeStore:
        embeddings = embed_texts([c.content for c in chunks])
        store = cls(embeddings.shape[1])
        store.index.add(_normalize(embeddings))
        store.chunks = chunks
        return store

    def search(self, query: str, k: int = 5) -> list[tuple[KnowledgeChunk, float]]:
        if self.index.ntotal == 0:
            return []
        query_vec = _normalize(embed_texts([query]))
        scores, indices = self.index.search(query_vec, min(k, self.index.ntotal))
        return [(self.chunks[i], float(s)) for s, i in zip(scores[0], indices[0]) if i >= 0]

    def save(self, directory: str | Path | None = None) -> Path:
        directory = Path(directory) if directory else RAG_DIR
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / "faiss_index.bin"))
        meta = {"dim": self.dim, "chunks": [c.model_dump() for c in self.chunks]}
        (directory / "chunks_metadata.json").write_text(json.dumps(meta))
        return directory

    @classmethod
    def load(cls, directory: str | Path | None = None) -> KnowledgeStore:
        directory = Path(directory) if directory else RAG_DIR
        meta = json.loads((directory / "chunks_metadata.json").read_text())
        store = cls(meta["dim"])
        store.index = faiss.read_index(str(directory / "faiss_index.bin"))
        store.chunks = [KnowledgeChunk(**c) for c in meta["chunks"]]
        return store
