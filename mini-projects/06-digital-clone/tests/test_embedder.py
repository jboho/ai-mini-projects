"""Tests for the local embedder."""

from __future__ import annotations

import numpy as np

from core.embedder import embed_texts, embedding_dim


def test_embed_dims_and_normalization():
    vecs = embed_texts(["hello world", "a second sentence"])
    assert vecs.shape == (2, embedding_dim())
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-3)


def test_embed_empty():
    assert embed_texts([]).shape[0] == 0
