"""Local sentence-transformers embedding with L2 normalization and npz caching.

Embeddings are L2-normalized so a FAISS inner-product index yields cosine
similarity directly. Chunk embeddings are cached to
``data/indices/{cache_key}_{model}.npz`` keyed by the chunking-config hash and
model name, so changing only the retrieval method does not re-embed.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np

from .config import INDICES_DIR
from .interfaces import BaseEmbedder
from .models import Chunk

logger = logging.getLogger(__name__)

_MODELS: dict[str, object] = {}


class SentenceTransformerEmbedder(BaseEmbedder):
    """BaseEmbedder backed by a local sentence-transformers model."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.name = model_name

    @property
    def _model(self):
        if self.name not in _MODELS:
            import os

            from sentence_transformers import SentenceTransformer

            # Default to CPU: the MPS (Apple Metal) backend crashes on some models
            # (e.g. mpnet) during batch embedding. Override with EMBED_DEVICE.
            device = os.environ.get("EMBED_DEVICE", "cpu")
            logger.info("Loading embedding model %s on %s", self.name, device)
            _MODELS[self.name] = SentenceTransformer(self.name, device=device)
        return _MODELS[self.name]

    @property
    def dim(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype="float32")
        vectors = self._model.encode(
            texts,
            batch_size=64,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype="float32")


def get_embedder(model_name: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(model_name)


def _cache_path(cache_key: str, model_name: str, cache_dir: Path) -> Path:
    safe_model = re.sub(r"[^A-Za-z0-9_.-]", "_", model_name)
    return cache_dir / f"{cache_key}_{safe_model}.npz"


def embed_chunks(
    embedder: BaseEmbedder,
    chunks: list[Chunk],
    cache_key: str,
    cache_dir: Path | None = None,
) -> np.ndarray:
    """Return chunk embeddings, loading from / writing to the npz cache."""
    cache_dir = cache_dir or INDICES_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_key, embedder.name, cache_dir)

    if path.exists():
        cached = np.load(path)
        if int(cached["count"]) == len(chunks):
            logger.info("Loaded cached embeddings: %s", path.name)
            return cached["embeddings"]
        logger.warning("Cache size mismatch for %s; recomputing", path.name)

    logger.info("Embedding %d chunks with %s", len(chunks), embedder.name)
    embeddings = embedder.embed([c.text for c in chunks])
    np.savez(path, embeddings=embeddings, count=len(chunks))
    return embeddings
