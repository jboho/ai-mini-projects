"""Shared model evaluation: one evaluate_model() used for baseline and finetuned.

Computes the four core embedding metrics (margin, Cohen's d, FPR, HDBSCAN cluster
purity) plus threshold-0.5 classification metrics, with a per-category breakdown.
"""

from __future__ import annotations

import logging

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .models import DatingPair, EvaluationMetrics

logger = logging.getLogger(__name__)

THRESHOLD = 0.5


def _cosine_sims(model, pairs: list[DatingPair]) -> np.ndarray:
    """Per-pair cosine similarity between text_1 and text_2 embeddings."""
    emb1 = model.encode(
        [p.text_1 for p in pairs], normalize_embeddings=True, show_progress_bar=False
    )
    emb2 = model.encode(
        [p.text_2 for p in pairs], normalize_embeddings=True, show_progress_bar=False
    )
    return np.sum(np.asarray(emb1) * np.asarray(emb2), axis=1)


def _cluster_purity(model, pairs: list[DatingPair], labels: np.ndarray) -> float:
    import hdbscan

    emb1 = model.encode(
        [p.text_1 for p in pairs], normalize_embeddings=True, show_progress_bar=False
    )
    emb2 = model.encode(
        [p.text_2 for p in pairs], normalize_embeddings=True, show_progress_bar=False
    )
    points = np.hstack([np.asarray(emb1), np.asarray(emb2)]).astype("float64")

    cluster_ids = hdbscan.HDBSCAN(min_cluster_size=15).fit_predict(points)
    purities, weights = [], []
    for cid in set(cluster_ids):
        if cid == -1:
            continue
        mask = cluster_ids == cid
        lab = labels[mask]
        purities.append(max((lab == 1).sum(), (lab == 0).sum()) / len(lab))
        weights.append(len(lab))
    return float(np.average(purities, weights=weights)) if purities else 0.0


def _classification(sims: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    preds = (sims > THRESHOLD).astype(int)
    out = {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision_score(labels, preds, zero_division=0),
        "recall": recall_score(labels, preds, zero_division=0),
        "f1": f1_score(labels, preds, zero_division=0),
    }
    out["auc_roc"] = roc_auc_score(labels, sims) if len(set(labels)) > 1 else 0.0
    return {k: float(v) for k, v in out.items()}


def _core_metrics(sims: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    compat = sims[labels == 1]
    incompat = sims[labels == 0]
    if len(compat) == 0 or len(incompat) == 0:
        return {"margin": 0.0, "effect_size": 0.0, "false_positive_rate": 0.0}
    pooled_std = np.sqrt((np.std(compat) ** 2 + np.std(incompat) ** 2) / 2)
    return {
        "margin": float(np.mean(compat) - np.mean(incompat)),
        "effect_size": float((np.mean(compat) - np.mean(incompat)) / pooled_std)
        if pooled_std
        else 0.0,
        "false_positive_rate": float(np.mean(incompat > THRESHOLD)),
    }


def evaluate_model(model, pairs: list[DatingPair]) -> EvaluationMetrics:
    sims = _cosine_sims(model, pairs)
    labels = np.array([p.label for p in pairs])

    metrics = {**_core_metrics(sims, labels), **_classification(sims, labels)}
    metrics["cluster_purity"] = _cluster_purity(model, pairs, labels)

    per_category: dict[str, dict[str, float]] = {}
    for cat in sorted({p.category for p in pairs}):
        idx = np.array([p.category == cat for p in pairs])
        if idx.sum() >= 10 and len(set(labels[idx])) > 1:
            per_category[cat] = {
                **_core_metrics(sims[idx], labels[idx]),
                **_classification(sims[idx], labels[idx]),
            }

    logger.info(
        "eval: margin=%.3f d=%.3f FPR=%.3f purity=%.3f acc=%.3f",
        metrics["margin"],
        metrics["effect_size"],
        metrics["false_positive_rate"],
        metrics["cluster_purity"],
        metrics["accuracy"],
    )
    return EvaluationMetrics(**metrics, per_category=per_category)
