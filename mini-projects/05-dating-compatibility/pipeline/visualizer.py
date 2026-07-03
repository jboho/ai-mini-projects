"""Visualizations for baseline vs fine-tuned comparison (headless, saved to visuals/)."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import roc_curve  # noqa: E402

from .evaluator import _cosine_sims  # noqa: E402
from .models import DatingPair, EvaluationMetrics  # noqa: E402

logger = logging.getLogger(__name__)

VISUALS_DIR = Path(__file__).resolve().parent.parent / "visuals"
_CORE = ["margin", "effect_size", "cluster_purity", "accuracy", "f1", "auc_roc"]


def _embed_points(model, pairs: list[DatingPair]) -> np.ndarray:
    e1 = model.encode([p.text_1 for p in pairs], normalize_embeddings=True, show_progress_bar=False)
    e2 = model.encode([p.text_2 for p in pairs], normalize_embeddings=True, show_progress_bar=False)
    return np.hstack([np.asarray(e1), np.asarray(e2)])


def plot_similarity_distributions(baseline, finetuned, pairs, out=None) -> Path:
    out = Path(out) if out else VISUALS_DIR / "similarity_distributions.png"
    labels = np.array([p.label for p in pairs])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, model, title in [(axes[0], baseline, "Baseline"), (axes[1], finetuned, "Fine-tuned")]:
        sims = _cosine_sims(model, pairs)
        ax.hist(sims[labels == 1], bins=40, alpha=0.6, label="compatible", color="#1f7a4d")
        ax.hist(sims[labels == 0], bins=40, alpha=0.6, label="incompatible", color="#b04632")
        ax.axvline(0.5, ls="--", color="gray")
        ax.set_title(f"{title} cosine similarity")
        ax.set_xlabel("cosine similarity")
        ax.legend()
    _save(fig, out)
    return out


def plot_metric_comparison(
    baseline: EvaluationMetrics, finetuned: EvaluationMetrics, out=None
) -> Path:
    out = Path(out) if out else VISUALS_DIR / "metric_comparison.png"
    x = np.arange(len(_CORE))
    b = [getattr(baseline, m) for m in _CORE]
    f = [getattr(finetuned, m) for m in _CORE]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - 0.2, b, 0.4, label="baseline", color="#9aa0a6")
    ax.bar(x + 0.2, f, 0.4, label="fine-tuned", color="#1f7a4d")
    ax.set_xticks(x)
    ax.set_xticklabels(_CORE, rotation=20)
    ax.set_title("Baseline vs fine-tuned metrics")
    ax.legend()
    _save(fig, out)
    return out


def plot_umap(baseline, finetuned, pairs, out=None) -> Path:
    import umap

    out = Path(out) if out else VISUALS_DIR / "umap_projection.png"
    labels = np.array([p.label for p in pairs])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, model, title in [(axes[0], baseline, "Baseline"), (axes[1], finetuned, "Fine-tuned")]:
        coords = umap.UMAP(n_components=2, random_state=42).fit_transform(
            _embed_points(model, pairs)
        )
        for lab, color, name in [(1, "#1f7a4d", "compatible"), (0, "#b04632", "incompatible")]:
            m = labels == lab
            ax.scatter(coords[m, 0], coords[m, 1], s=5, alpha=0.5, color=color, label=name)
        ax.set_title(f"{title} (UMAP)")
        ax.legend()
    _save(fig, out)
    return out


def plot_category_fpr(baseline: EvaluationMetrics, finetuned: EvaluationMetrics, out=None) -> Path:
    out = Path(out) if out else VISUALS_DIR / "category_fpr.png"
    cats = sorted(set(baseline.per_category) | set(finetuned.per_category))
    data = np.array(
        [
            [baseline.per_category.get(c, {}).get("false_positive_rate", 0) for c in cats],
            [finetuned.per_category.get(c, {}).get("false_positive_rate", 0) for c in cats],
        ]
    )
    fig, ax = plt.subplots(figsize=(max(6, len(cats) * 1.2), 3))
    im = ax.imshow(data, cmap="Reds", aspect="auto", vmin=0, vmax=max(0.1, data.max()))
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=20)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["baseline", "fine-tuned"])
    ax.set_title("False positive rate by category")
    fig.colorbar(im, ax=ax)
    _save(fig, out)
    return out


def plot_roc(baseline, finetuned, pairs, out=None) -> Path:
    out = Path(out) if out else VISUALS_DIR / "roc_curves.png"
    labels = np.array([p.label for p in pairs])
    fig, ax = plt.subplots(figsize=(6, 6))
    for model, name, color in [
        (baseline, "baseline", "#9aa0a6"),
        (finetuned, "fine-tuned", "#1f7a4d"),
    ]:
        fpr, tpr, _ = roc_curve(labels, _cosine_sims(model, pairs))
        ax.plot(fpr, tpr, label=name, color=color)
    ax.plot([0, 1], [0, 1], ls="--", color="gray")
    ax.set_xlabel("FPR")
    ax.set_ylabel("TPR")
    ax.set_title("ROC curves")
    ax.legend()
    _save(fig, out)
    return out


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    logger.info("Saved %s", path.name)
