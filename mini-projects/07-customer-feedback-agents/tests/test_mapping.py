"""Tests for cosine similarity and theme->roadmap alignment."""

from __future__ import annotations

import numpy as np

from pipeline.agents.mapping import align_from_matrix
from pipeline.embeddings import cosine_matrix


def test_cosine_matrix():
    a = np.array([[1.0, 0.0], [0.0, 1.0]])
    b = np.array([[1.0, 0.0]])
    sim = cosine_matrix(a, b)
    assert sim.shape == (2, 1)
    assert sim[0, 0] == 1.0 and sim[1, 0] == 0.0


def test_align_above_and_below_threshold(sample_themes, roadmap_items):
    # T1->R1 strong, T2->R2 strong, T3 -> weak (no match)
    sim = np.array([[0.9, 0.1], [0.2, 0.85], [0.3, 0.2]], dtype="float32")
    results = align_from_matrix(sample_themes, roadmap_items, sim, threshold=0.75)
    assert results[0].aligned and results[0].roadmap_item_id == "R1"
    assert results[1].aligned and results[1].roadmap_item_id == "R2"
    assert not results[2].aligned and results[2].roadmap_item_id is None


def test_align_no_roadmap(sample_themes):
    results = align_from_matrix(sample_themes, [], np.zeros((3, 0)), threshold=0.75)
    assert all(not r.aligned for r in results)
