"""Embedding with OpenAI or local sentence-transformers, plus on-disk caching.

The backend is chosen by model name: any ``text-embedding-*`` model goes through
the OpenAI API; anything else is loaded as a local sentence-transformers model
(CPU, no key). This lets the grid mix API and local embedding axes.

Chunk embeddings are cached to ``cache/{cache_key}_{model}.npz`` keyed by the
chunking-config hash and model name. Delete the cache file to recompute.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .config import CACHE_DIR
from .models import Chunk

logger = logging.getLogger(__name__)

_LOCAL_MODELS: dict[str, object] = {}


def _is_openai_model(model: str) -> bool:
    return model.startswith("text-embedding")


def _embed_openai_batch(texts: list[str], model: str) -> list[list[float]]:
    from .client import get_openai_client

    response = get_openai_client().embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def _embed_openai(texts: list[str], model: str, batch_size: int, max_workers: int) -> np.ndarray:
    batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(lambda batch: _embed_openai_batch(batch, model), batches))
    vectors = [vec for batch in results for vec in batch]
    return np.asarray(vectors, dtype="float32")


def _get_local_model(model: str):
    if model not in _LOCAL_MODELS:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading local embedding model %s", model)
        _LOCAL_MODELS[model] = SentenceTransformer(model)
    return _LOCAL_MODELS[model]


def _embed_local(texts: list[str], model: str, batch_size: int) -> np.ndarray:
    encoder = _get_local_model(model)
    vectors = encoder.encode(
        texts, batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False
    )
    return np.asarray(vectors, dtype="float32")


def embed_batch(
    texts: list[str], model: str, batch_size: int = 100, max_workers: int = 4
) -> np.ndarray:
    """Embed ``texts`` with the backend implied by ``model``, preserving order."""
    if not texts:
        return np.empty((0, 0), dtype="float32")
    if _is_openai_model(model):
        return _embed_openai(texts, model, batch_size, max_workers)
    return _embed_local(texts, model, batch_size)


def _cache_path(cache_key: str, model: str) -> Path:
    safe_model = re.sub(r"[^A-Za-z0-9_.-]", "_", model)
    return CACHE_DIR / f"{cache_key}_{safe_model}.npz"


def embed_chunks(
    chunks: list[Chunk], model: str, cache_key: str, cache_dir: Path | None = None
) -> np.ndarray:
    """Return chunk embeddings, loading from / writing to the npz cache."""
    cache_dir = cache_dir or CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / _cache_path(cache_key, model).name

    if path.exists():
        cached = np.load(path)
        if int(cached["count"]) == len(chunks):
            logger.info("Loaded cached embeddings: %s", path.name)
            return cached["embeddings"]
        logger.warning("Cache size mismatch for %s; recomputing", path.name)

    logger.info("Embedding %d chunks with %s", len(chunks), model)
    embeddings = embed_batch([chunk.text for chunk in chunks], model)
    np.savez(path, embeddings=embeddings, count=len(chunks))
    return embeddings


def embed_query(query: str, model: str) -> np.ndarray:
    return embed_batch([query], model)[0]
