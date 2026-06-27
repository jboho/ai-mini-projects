"""FAISS vector index build/search/persist.

Embeddings are L2-normalized and stored in an inner-product index, so the
returned scores are cosine similarities in ``[-1, 1]`` (≈ ``[0, 1]`` for these
embedding models). This keeps hybrid score fusion simple and bounded.
"""

from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np


def normalize(embeddings: np.ndarray) -> np.ndarray:
    """Return a float32 copy with each row L2-normalized (zero rows left as-is)."""
    array = np.asarray(embeddings, dtype="float32")
    if array.ndim != 2:
        raise ValueError("embeddings must be a 2D array")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return array / norms


def build_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Build a cosine-similarity index from chunk embeddings."""
    normalized = normalize(embeddings)
    index = faiss.IndexFlatIP(normalized.shape[1])
    index.add(normalized)
    return index


def search_index(
    index: faiss.IndexFlatIP, query_embedding: np.ndarray, k: int
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(scores, indices)`` for the top-``k`` matches to the query."""
    query = normalize(np.asarray(query_embedding, dtype="float32").reshape(1, -1))
    k = min(k, index.ntotal)
    scores, indices = index.search(query, k)
    return scores[0], indices[0]


def save_index(index: faiss.IndexFlatIP, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))


def load_index(path: str | Path) -> faiss.IndexFlatIP:
    return faiss.read_index(str(path))
