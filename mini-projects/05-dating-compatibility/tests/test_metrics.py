"""Known-answer tests for the core metric and classification computations."""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.evaluator import _classification, _core_metrics


def test_core_metrics_known_values():
    sims = np.array([0.9, 0.8, 0.2, 0.1])
    labels = np.array([1, 1, 0, 0])
    core = _core_metrics(sims, labels)
    assert core["margin"] == pytest.approx(0.85 - 0.15)
    assert core["false_positive_rate"] == 0.0
    assert core["effect_size"] > 0


def test_core_metrics_with_false_positives():
    sims = np.array([0.9, 0.6, 0.7, 0.1])  # one incompatible (0.7) above threshold
    labels = np.array([1, 1, 0, 0])
    assert _core_metrics(sims, labels)["false_positive_rate"] == 0.5


def test_classification_perfect():
    sims = np.array([0.9, 0.8, 0.2, 0.1])
    labels = np.array([1, 1, 0, 0])
    m = _classification(sims, labels)
    assert m["accuracy"] == 1.0
    assert m["f1"] == 1.0
    assert m["auc_roc"] == 1.0


def test_classification_thresholding():
    sims = np.array([0.9, 0.4, 0.6, 0.1])  # pred = [1,0,1,0]
    labels = np.array([1, 1, 0, 0])
    m = _classification(sims, labels)
    assert m["accuracy"] == 0.5
