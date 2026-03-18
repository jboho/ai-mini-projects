"""Aggregate pipeline statistics and pipeline summary JSON."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .corrector import CorrectionStats
from .schemas.labels import FailureLabels, JudgeResult
from .schemas.pair import FitLevel, ResumeJobPair, WritingStyle
from .schemas.validation import ValidationResult

logger = logging.getLogger(__name__)

BOOL_METRICS = [
    "experience_mismatch",
    "seniority_mismatch",
    "missing_core_skills",
    "hallucinated_skills",
    "awkward_language",
]
ALL_METRICS = ["skills_overlap"] + BOOL_METRICS


def build_labels_dataframe(
    pairs: list[ResumeJobPair],
    labels: list[FailureLabels],
) -> pd.DataFrame:
    """Join pair metadata with failure labels into a flat DataFrame."""
    label_index = {lbl.pair_id: lbl for lbl in labels}
    rows: list[dict[str, Any]] = []

    for pair in pairs:
        lbl = label_index.get(pair.metadata.pair_id)
        if lbl is None:
            continue
        row: dict[str, Any] = {
            "pair_id": pair.metadata.pair_id,
            "fit_level": pair.metadata.fit_level.value,
            "writing_style": pair.metadata.writing_style.value,
            "is_niche": pair.job.metadata.is_niche_role,
            "skills_overlap": lbl.skills_overlap,
        }
        for metric in BOOL_METRICS:
            row[metric] = int(getattr(lbl, metric))
        row["any_failure"] = int(lbl.any_failure)
        row["failure_count"] = lbl.failure_count
        rows.append(row)

    return pd.DataFrame(rows)


def failure_rates_by_fit_level(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for level in FitLevel:
        subset = df[df["fit_level"] == level.value]
        if subset.empty:
            continue
        result[level.value] = {m: float(subset[m].mean()) for m in BOOL_METRICS}
    return result


def failure_rates_by_template(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for style in WritingStyle:
        subset = df[df["writing_style"] == style.value]
        if subset.empty:
            continue
        result[style.value] = {m: float(subset[m].mean()) for m in BOOL_METRICS}
    return result


def niche_vs_standard_rates(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for is_niche, label in [(True, "niche"), (False, "standard")]:
        subset = df[df["is_niche"] == is_niche]
        if subset.empty:
            continue
        out[label] = {m: float(subset[m].mean()) for m in BOOL_METRICS}
    return out


def schema_field_failure_rates(
    validations: list[ValidationResult],
) -> dict[str, int]:
    """Count how many times each field path appears in validation errors."""
    counts: dict[str, int] = {}
    for v in validations:
        for err in v.errors:
            counts[err.field_path] = counts.get(err.field_path, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def build_judge_summary(
    judge_results: list[JudgeResult],
    labels: list[FailureLabels],
) -> dict[str, Any]:
    """Aggregate judge scores and compare against rule-based flags (gap analysis)."""
    if not judge_results:
        return {}

    label_index = {lbl.pair_id: lbl for lbl in labels}
    scores = {
        "avg_quality_score": round(
            sum(j.quality_score for j in judge_results) / len(judge_results), 2
        ),
        "avg_hallucination_score": round(
            sum(j.hallucination_score for j in judge_results) / len(judge_results), 2
        ),
        "avg_awkward_language_score": round(
            sum(j.awkward_language_score for j in judge_results) / len(judge_results), 2
        ),
        "total_judged": len(judge_results),
    }

    # Gap analysis: cases where judge and rule-based labels disagree
    rule_flags_hallucination = 0
    judge_flags_hallucination = 0
    both_flag_hallucination = 0

    rule_flags_awkward = 0
    judge_flags_awkward = 0
    both_flag_awkward = 0

    for j in judge_results:
        lbl = label_index.get(j.pair_id)
        if lbl is None:
            continue

        rule_hall = lbl.hallucinated_skills
        judge_hall = j.hallucination_score >= 3

        rule_awk = lbl.awkward_language
        judge_awk = j.awkward_language_score >= 3

        if rule_hall:
            rule_flags_hallucination += 1
        if judge_hall:
            judge_flags_hallucination += 1
        if rule_hall and judge_hall:
            both_flag_hallucination += 1

        if rule_awk:
            rule_flags_awkward += 1
        if judge_awk:
            judge_flags_awkward += 1
        if rule_awk and judge_awk:
            both_flag_awkward += 1

    scores["gap_analysis"] = {
        "hallucination": {
            "rule_based_flags": rule_flags_hallucination,
            "judge_flags": judge_flags_hallucination,
            "both_agree": both_flag_hallucination,
        },
        "awkward_language": {
            "rule_based_flags": rule_flags_awkward,
            "judge_flags": judge_flags_awkward,
            "both_agree": both_flag_awkward,
        },
    }

    return scores


def build_pipeline_summary(
    pairs: list[ResumeJobPair],
    valid_pairs: list[ResumeJobPair],
    invalid_pairs: list[ResumeJobPair],
    labels: list[FailureLabels],
    validations: list[ValidationResult],
    correction_stats: CorrectionStats,
    df: pd.DataFrame,
    judge_results: list[JudgeResult] | None = None,
) -> dict[str, Any]:
    total = len(pairs)
    overall_failure_rate = float(df["any_failure"].mean()) if not df.empty else 0.0

    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "pairs_generated": total,
            "valid_pairs": len(valid_pairs),
            "invalid_pairs": len(invalid_pairs),
        },
        "correction": {
            "correction_rate": round(correction_stats.correction_rate, 3),
            "corrected": correction_stats.corrected_pairs,
            "permanently_failed": correction_stats.permanently_failed,
            "attempts_histogram": correction_stats.attempts_histogram,
        },
        "failure_rates": {
            metric: round(float(df[metric].mean()), 3) if not df.empty else 0.0
            for metric in BOOL_METRICS
        },
        "overall_failure_rate": round(overall_failure_rate, 3),
        "avg_skills_overlap": (
            round(float(df["skills_overlap"].mean()), 3) if not df.empty else 0.0
        ),
        "by_fit_level": failure_rates_by_fit_level(df),
        "by_template": failure_rates_by_template(df),
        "niche_vs_standard": niche_vs_standard_rates(df),
        "schema_field_failures": schema_field_failure_rates(validations),
    }

    if judge_results:
        summary["llm_judge"] = build_judge_summary(judge_results, labels)

    return summary


def save_pipeline_summary(summary: dict[str, Any], data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "pipeline_summary.json"
    path.write_text(json.dumps(summary, indent=2))
    logger.info("Pipeline summary saved to %s", path)
    return path
