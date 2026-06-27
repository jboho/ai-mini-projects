"""Phase 4: Failure analysis — aggregate rates, heatmap, charts."""

from __future__ import annotations

import logging
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .models import FAILURE_MODES, PipelineRecord, RepairCategory

logger = logging.getLogger(__name__)

VISUALS_DIR = Path(__file__).resolve().parent.parent / "visuals"


def _ensure_visuals_dir() -> Path:
    VISUALS_DIR.mkdir(parents=True, exist_ok=True)
    return VISUALS_DIR


def _judged_records(records: list[PipelineRecord]) -> list[PipelineRecord]:
    return [r for r in records if r.judge_result is not None]


def build_failure_dataframe(
    records: list[PipelineRecord],
) -> pd.DataFrame:
    """Build a DataFrame with one row per judged item, columns for each mode."""
    rows = []
    for r in _judged_records(records):
        jr = r.judge_result
        row = {
            "trace_id": r.trace_id,
            "category": r.metadata.category.value,
        }
        for mode in FAILURE_MODES:
            row[mode] = getattr(jr, mode)
        row["overall_failure"] = jr.overall_failure
        row["failure_count"] = jr.failure_count
        rows.append(row)
    return pd.DataFrame(rows)


def per_mode_failure_rates(df: pd.DataFrame) -> dict[str, float]:
    """Return failure rate (0-1) for each mode."""
    return {mode: df[mode].mean() for mode in FAILURE_MODES}


def overall_failure_rate(df: pd.DataFrame) -> float:
    return df["overall_failure"].mean()


def failure_rates_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot: rows=categories, columns=failure modes, values=mean rate."""
    return df.groupby("category")[FAILURE_MODES].mean()


def shannon_entropy(counts: dict[str, int]) -> float:
    """Shannon entropy over a category distribution."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def category_coverage(df: pd.DataFrame) -> dict:
    """Category counts + Shannon entropy."""
    counts = df["category"].value_counts().to_dict()
    return {
        "counts": counts,
        "entropy": shannon_entropy(counts),
        "all_represented": set(counts.keys()) == {c.value for c in RepairCategory},
    }


def worst_items(df: pd.DataFrame, min_failures: int = 3) -> pd.DataFrame:
    """Items with >= min_failures simultaneous failure flags."""
    return df[df["failure_count"] >= min_failures].sort_values(
        "failure_count", ascending=False
    )


def confidence_interval(
    rate: float, n: int, z: float = 1.96
) -> tuple[float, float]:
    """Normal-approximation 95 % CI for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    se = math.sqrt(rate * (1 - rate) / n)
    return (max(0.0, rate - z * se), min(1.0, rate + z * se))


# ── Visualizations ──────────────────────────────────────────────────


def plot_cooccurrence_heatmap(
    df: pd.DataFrame, *, tag: str = "baseline"
) -> Path:
    """Failure mode co-occurrence matrix as a heatmap."""
    _ensure_visuals_dir()
    mode_df = df[FAILURE_MODES]
    corr = mode_df.T.dot(mode_df) / len(mode_df)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        xticklabels=[m.replace("_", "\n") for m in FAILURE_MODES],
        yticklabels=[m.replace("_", "\n") for m in FAILURE_MODES],
        ax=ax,
    )
    ax.set_title(f"Failure Co-occurrence ({tag})")
    fig.tight_layout()
    path = VISUALS_DIR / f"cooccurrence_{tag}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Saved heatmap: %s", path)
    return path


def plot_failure_by_category(
    df: pd.DataFrame, *, tag: str = "baseline"
) -> Path:
    """Stacked bar chart of failure rates by repair category."""
    _ensure_visuals_dir()
    cat_rates = failure_rates_by_category(df)

    fig, ax = plt.subplots(figsize=(10, 6))
    cat_rates.plot(kind="bar", stacked=True, ax=ax, colormap="Set2")
    ax.set_ylabel("Cumulative failure rate")
    ax.set_title(f"Failure Rates by Repair Category ({tag})")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    ax.legend(
        [m.replace("_", " ") for m in FAILURE_MODES],
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=8,
    )
    fig.tight_layout()
    path = VISUALS_DIR / f"failure_by_category_{tag}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Saved category chart: %s", path)
    return path


def plot_before_after(
    baseline_rates: dict[str, float],
    corrected_rates: dict[str, float],
) -> Path:
    """Grouped bar chart comparing per-mode failure rates."""
    _ensure_visuals_dir()
    modes = FAILURE_MODES
    x = np.arange(len(modes))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars_b = ax.bar(
        x - width / 2,
        [baseline_rates[m] for m in modes],
        width,
        label="Baseline",
        color="#e74c3c",
        alpha=0.8,
    )
    bars_c = ax.bar(
        x + width / 2,
        [corrected_rates[m] for m in modes],
        width,
        label="Corrected",
        color="#2ecc71",
        alpha=0.8,
    )

    ax.set_ylabel("Failure rate")
    ax.set_title("Before / After Comparison by Failure Mode")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [m.replace("_", "\n") for m in modes], fontsize=8
    )
    ax.legend()
    ax.set_ylim(0, 1.0)

    for bar in bars_b:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.02,
                f"{h:.0%}",
                ha="center",
                fontsize=7,
            )
    for bar in bars_c:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.02,
                f"{h:.0%}",
                ha="center",
                fontsize=7,
            )

    fig.tight_layout()
    path = VISUALS_DIR / "before_after_comparison.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Saved before/after chart: %s", path)
    return path


# ── Summary report ──────────────────────────────────────────────────


def generate_summary(
    records: list[PipelineRecord], *, tag: str = "baseline"
) -> dict:
    """Produce a summary dict for a single pipeline run."""
    df = build_failure_dataframe(records)
    if df.empty:
        return {"tag": tag, "error": "No judged records"}

    rates = per_mode_failure_rates(df)
    overall = overall_failure_rate(df)
    n = len(df)
    ci = confidence_interval(overall, n)
    coverage = category_coverage(df)
    worst = worst_items(df)

    return {
        "tag": tag,
        "total_generated": len(records),
        "passed_validation": sum(
            1 for r in records if r.metadata.passed_validation
        ),
        "judged": n,
        "overall_failure_rate": overall,
        "overall_failure_ci_95": ci,
        "per_mode_rates": rates,
        "category_coverage": coverage,
        "worst_items": worst[["trace_id", "category", "failure_count"]]
        .to_dict(orient="records")
        if not worst.empty
        else [],
    }
