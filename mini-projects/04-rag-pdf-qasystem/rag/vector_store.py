"""FAISS vector store holding chunk metadata, with save/load.

Embeddings are expected L2-normalized (see embedder.py), so an inner-product
index returns cosine similarity. The store keeps the chunks alongside the index
so a search returns fully-populated RetrievalResults.
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from .models import Chunk, RetrievalResult

# Single-threaded faiss avoids the OpenMP segfault when run after torch on macOS.
faiss.omp_set_num_threads(1)


def _normalize(vectors: np.ndarray) -> np.ndarray:
    array = np.asarray(vectors, dtype="float32")
    if array.ndim == 1:
        array = array.reshape(1, -1)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return array / norms


class VectorStore:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: list[Chunk] = []

    @classmethod
    def from_embeddings(cls, embeddings: np.ndarray, chunks: list[Chunk]) -> VectorStore:
        store = cls(embeddings.shape[1])
        store.add(embeddings, chunks)
        return store

    def add(self, embeddings: np.ndarray, chunks: list[Chunk]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must be the same length")
        self.index.add(_normalize(embeddings))
        self.chunks.extend(chunks)

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[RetrievalResult]:
        if self.index.ntotal == 0:
            return []
        top_k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(_normalize(query_embedding), top_k)
        results: list[RetrievalResult] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
            if idx < 0:
                continue
            chunk = self.chunks[idx]
            results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    doc_id=chunk.doc_id,
                    score=float(score),
                    rank=rank,
                    text=chunk.text,
                    method="dense",
                )
            )
        return results

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path.with_suffix(".faiss")))
        meta = {"dim": self.dim, "chunks": [c.model_dump() for c in self.chunks]}
        path.with_suffix(".json").write_text(json.dumps(meta))

    @classmethod
    def load(cls, path: str | Path) -> VectorStore:
        path = Path(path)
        meta = json.loads(path.with_suffix(".json").read_text())
        store = cls(meta["dim"])
        store.index = faiss.read_index(str(path.with_suffix(".faiss")))
        store.chunks = [Chunk(**c) for c in meta["chunks"]]
        return store
