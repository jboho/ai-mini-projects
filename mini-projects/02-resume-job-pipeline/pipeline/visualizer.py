"""Five required visualizations + one bonus chart.

All charts use non-interactive Agg backend to work in headless/CI environments.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .analyzer import BOOL_METRICS

logger = logging.getLogger(__name__)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    logger.info("Saved chart: %s", path)


def plot_failure_correlation_matrix(df: pd.DataFrame, visuals_dir: Path) -> Path:
    """Chart 1: Heatmap of co-occurrence (correlation) across 6 failure metrics."""
    corr = df[BOOL_METRICS].astype(float).corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Failure Mode Correlation Matrix", fontsize=14, pad=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
    path = visuals_dir / "01_failure_correlation_matrix.png"
    _save(fig, path)
    return path


def plot_failure_rates_by_fit_level(df: pd.DataFrame, visuals_dir: Path) -> Path:
    """Chart 2: Grouped bar chart of failure rates per FitLevel."""
    fit_order = ["Excellent", "Good", "Partial", "Poor", "Mismatch"]
    present = [lvl for lvl in fit_order if lvl in df["fit_level"].unique()]
    grouped = (
        df[["fit_level"] + BOOL_METRICS]
        .groupby("fit_level")
        .mean()
        .reindex(present)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(grouped))
    width = 0.15
    for i, metric in enumerate(BOOL_METRICS):
        ax.bar(x + i * width, grouped[metric], width, label=metric.replace("_", " "))
    ax.set_xticks(x + width * (len(BOOL_METRICS) - 1) / 2)
    ax.set_xticklabels(grouped.index, fontsize=10)
    ax.set_ylabel("Failure Rate")
    ax.set_title("Failure Rates by Fit Level", fontsize=14, pad=12)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8, loc="upper left")
    path = visuals_dir / "02_failure_by_fit_level.png"
    _save(fig, path)
    return path


def plot_failure_rates_by_template(df: pd.DataFrame, visuals_dir: Path) -> Path:
    """Chart 3: Grouped bar chart of failure rates per writing template."""
    grouped = (
        df[["writing_style"] + BOOL_METRICS]
        .groupby("writing_style")
        .mean()
    )
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(grouped))
    width = 0.15
    for i, metric in enumerate(BOOL_METRICS):
        ax.bar(x + i * width, grouped[metric], width, label=metric.replace("_", " "))
    ax.set_xticks(x + width * (len(BOOL_METRICS) - 1) / 2)
    ax.set_xticklabels(grouped.index, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Failure Rate")
    ax.set_title("Failure Rates by Writing Template", fontsize=14, pad=12)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8, loc="upper right")
    path = visuals_dir / "03_failure_by_template.png"
    _save(fig, path)
    return path


def plot_niche_vs_standard(df: pd.DataFrame, visuals_dir: Path) -> Path:
    """Chart 4: Side-by-side comparison of niche vs. standard roles."""
    niche_df = df[df["is_niche"]][BOOL_METRICS].mean()
    std_df = df[~df["is_niche"]][BOOL_METRICS].mean()
    comparison = pd.DataFrame({"niche": niche_df, "standard": std_df})

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(BOOL_METRICS))
    ax.bar(x - 0.2, comparison["niche"], 0.4, label="Niche", color="#e07b54")
    ax.bar(x + 0.2, comparison["standard"], 0.4, label="Standard", color="#5486e0")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [m.replace("_", " ") for m in BOOL_METRICS], rotation=20, ha="right"
    )
    ax.set_ylabel("Failure Rate")
    ax.set_title("Failure Rates: Niche vs. Standard Roles", fontsize=14, pad=12)
    ax.set_ylim(0, 1)
    ax.legend()
    path = visuals_dir / "04_niche_vs_standard.png"
    _save(fig, path)
    return path


def plot_schema_validation_heatmap(
    field_failures: dict[str, int], visuals_dir: Path
) -> Path:
    """Chart 5: Horizontal bar chart showing which fields fail validation most."""
    if not field_failures:
        logger.info("No validation failures to plot")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No validation failures recorded", ha="center", va="center")
        path = visuals_dir / "05_schema_validation_heatmap.png"
        _save(fig, path)
        return path

    top_n = dict(list(field_failures.items())[:15])
    labels = list(top_n.keys())
    values = list(top_n.values())

    fig, ax = plt.subplots(figsize=(9, max(4, len(labels) * 0.4)))
    y_pos = np.arange(len(labels))
    ax.barh(y_pos, values, color="#5c85d6")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Failures")
    ax.set_title("Schema Validation Failures by Field", fontsize=14, pad=12)
    path = visuals_dir / "05_schema_validation_heatmap.png"
    _save(fig, path)
    return path


def plot_hallucination_by_seniority(df: pd.DataFrame, visuals_dir: Path) -> Path:
    """Chart 6 (bonus): Stacked bar of hallucination + seniority mismatch by fit level.
    """
    fit_order = ["Excellent", "Good", "Partial", "Poor", "Mismatch"]
    present = [lvl for lvl in fit_order if lvl in df["fit_level"].unique()]
    grouped = (
        df[["fit_level", "hallucinated_skills", "seniority_mismatch"]]
        .groupby("fit_level")
        .mean()
        .reindex(present)
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(grouped))
    ax.bar(
        x, grouped["hallucinated_skills"], label="Hallucinated Skills", color="#d65c5c"
    )
    ax.bar(
        x, grouped["seniority_mismatch"],
        bottom=grouped["hallucinated_skills"],
        label="Seniority Mismatch",
        color="#d6a05c",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(grouped.index)
    ax.set_ylabel("Rate")
    ax.set_title("Hallucination & Seniority Mismatch by Fit Level", fontsize=13, pad=12)
    ax.set_ylim(0, 1)
    ax.legend()
    path = visuals_dir / "06_hallucination_by_fit_level.png"
    _save(fig, path)
    return path


def generate_all_charts(
    df: pd.DataFrame,
    field_failures: dict[str, int],
    visuals_dir: Path,
) -> list[Path]:
    """Generate all 6 charts and return their paths."""
    visuals_dir.mkdir(parents=True, exist_ok=True)
    charts = [
        plot_failure_correlation_matrix(df, visuals_dir),
        plot_failure_rates_by_fit_level(df, visuals_dir),
        plot_failure_rates_by_template(df, visuals_dir),
        plot_niche_vs_standard(df, visuals_dir),
        plot_schema_validation_heatmap(field_failures, visuals_dir),
        plot_hallucination_by_seniority(df, visuals_dir),
    ]
    return charts
