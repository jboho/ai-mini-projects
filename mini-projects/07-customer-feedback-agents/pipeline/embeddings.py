"""Batch OpenAI embeddings with L2 normalization and a content-hash disk cache."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

import numpy as np

from .config import DATA_DIR

logger = logging.getLogger(__name__)


def _embedding_model() -> str:
    return os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")


def _normalize(vectors: np.ndarray) -> np.ndarray:
    array = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return array / norms


def embed_texts(texts: list[str], model: str | None = None, use_cache: bool = True) -> np.ndarray:
    """Return L2-normalized embeddings (cosine via dot product), cached by content."""
    if not texts:
        return np.empty((0, 0), dtype="float32")
    model = model or _embedding_model()
    key = hashlib.sha256(("|".join(texts) + model).encode()).hexdigest()[:16]
    cache = DATA_DIR / f"embeddings_{key}.npz"
    if use_cache and cache.exists():
        return np.load(cache)["embeddings"]

    from .client import get_openai_client

    client = get_openai_client()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), 2048):
        resp = client.embeddings.create(model=model, input=texts[i : i + 2048])
        vectors.extend(item.embedding for item in resp.data)
    embeddings = _normalize(np.asarray(vectors, dtype="float32"))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(cache, embeddings=embeddings)
    return embeddings


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity between rows of a and b (assumed normalized)."""
    if a.size == 0 or b.size == 0:
        return np.zeros((len(a), len(b)), dtype="float32")
    return np.asarray(a, dtype="float32") @ np.asarray(b, dtype="float32").T


def to_path(name: str) -> Path:
    return DATA_DIR / name
