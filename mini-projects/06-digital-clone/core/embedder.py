"""SentenceTransformers embedding wrapper (local, L2-normalized)."""

from __future__ import annotations

import logging
import os

import numpy as np

from .client import get_embedding_model_name

logger = logging.getLogger(__name__)

_MODELS: dict[str, object] = {}


def get_embedding_model(name: str | None = None):
    name = name or get_embedding_model_name()
    if name not in _MODELS:
        from sentence_transformers import SentenceTransformer

        device = os.environ.get("EMBED_DEVICE", "cpu")
        logger.info("Loading embedding model %s on %s", name, device)
        _MODELS[name] = SentenceTransformer(name, device=device)
    return _MODELS[name]


def embed_texts(texts: list[str], model_name: str | None = None) -> np.ndarray:
    if not texts:
        model = get_embedding_model(model_name)
        return np.empty((0, model.get_sentence_embedding_dimension()), dtype="float32")
    model = get_embedding_model(model_name)
    vectors = model.encode(
        texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
    )
    return np.asarray(vectors, dtype="float32")


def embedding_dim(model_name: str | None = None) -> int:
    return int(get_embedding_model(model_name).get_sentence_embedding_dimension())
