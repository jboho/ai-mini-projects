"""CLI orchestrator for the resume-job synthetic data pipeline.

Usage:
    python run_pipeline.py --mode generate
    python run_pipeline.py --mode validate
    python run_pipeline.py --mode label
    python run_pipeline.py --mode correct
    python run_pipeline.py --mode analyze
    python run_pipeline.py --mode all

Modes:
    generate  — generate jobs and resumes, write JSONL to data/
    validate  — validate existing pairs, write valid/invalid splits
    correct   — run correction loop on invalid pairs
    label     — compute 6 failure metrics on valid pairs
    analyze   — build pipeline_summary.json and 6 charts
    all       — run all phases end-to-end

Output files (all in data/):
    jobs.jsonl               — generated job descriptions
    pairs.jsonl              — all resume-job pairs
    valid_pairs.jsonl        — pairs that passed validation
    invalid_pairs.jsonl      — pairs that failed validation
    corrected_pairs.jsonl    — pairs fixed by the correction loop
    labels.jsonl             — FailureLabels per pair
    pipeline_summary.json    — aggregate statistics

Charts (in visuals/):
    01_failure_correlation_matrix.png
    02_failure_by_fit_level.png
    03_failure_by_template.png
    04_niche_vs_standard.png
    05_schema_validation_heatmap.png
    06_hallucination_by_fit_level.png
"""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from pathlib import Path

from pipeline.analyzer import (
    build_labels_dataframe,
    build_pipeline_summary,
    save_pipeline_summary,
    schema_field_failure_rates,
)
from pipeline.client import get_instructor_client
from pipeline.config import get_settings
from pipeline.corrector import CorrectionStats, run_correction_loop
from pipeline.generator import generate_jobs, generate_resumes_for_job
from pipeline.judge import judge_pair
from pipeline.labeler import label_pair
from pipeline.schemas import FailureLabels, JobDescription, ResumeJobPair
from pipeline.schemas.pair import PairMetadata
from pipeline.schemas.validation import ValidationResult
from pipeline.validator import validate_pair
from pipeline.visualizer import generate_all_charts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _write_jsonl(records: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for rec in records:
            if hasattr(rec, "model_dump_json"):
                fh.write(rec.model_dump_json() + "\n")
            else:
                fh.write(json.dumps(rec) + "\n")
    logger.info("Wrote %d records to %s", len(records), path)


def _read_jsonl(path: Path, model_cls) -> list:
    if not path.exists():
        return []
    records = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(model_cls.model_validate_json(line))
    return records


# ── Phase runners ─────────────────────────────────────────────────────────────

def run_generate(settings, client) -> tuple[list[JobDescription], list[ResumeJobPair]]:
    logger.info("=== GENERATE: %d jobs × %d resumes ===",
                settings.batch_size, settings.resumes_per_job)

    jobs = generate_jobs(settings, client)
    _write_jsonl(jobs, settings.data_dir / "jobs.jsonl")

    all_pairs: list[ResumeJobPair] = []
    for job in jobs:
        resume_results = generate_resumes_for_job(job, settings, client)
        for resume, fit_level, style in resume_results:
            pair = ResumeJobPair(
                resume=resume,
                job=job,
                metadata=PairMetadata(
                    pair_id=str(uuid.uuid4()),
                    fit_level=fit_level,
                    writing_style=style,
                ),
            )
            all_pairs.append(pair)

    _write_jsonl(all_pairs, settings.data_dir / "pairs.jsonl")
    logger.info("Generated %d pairs total", len(all_pairs))
    return jobs, all_pairs


def run_validate(
    pairs: list[ResumeJobPair],
) -> tuple[list[ResumeJobPair], list[ResumeJobPair], dict[str, ValidationResult]]:
    logger.info("=== VALIDATE: %d pairs ===", len(pairs))
    valid, invalid = [], []
    validations: dict[str, ValidationResult] = {}

    for pair in pairs:
        result = validate_pair(pair)
        validations[pair.metadata.pair_id] = result
        if result.is_valid:
            valid.append(pair)
        else:
            invalid.append(pair)

    logger.info("Valid: %d  Invalid: %d", len(valid), len(invalid))
    return valid, invalid, validations


def run_correct(
    invalid_pairs: list[ResumeJobPair],
    validations: dict[str, ValidationResult],
    settings,
    client,
) -> tuple[list[ResumeJobPair], list[ResumeJobPair]]:
    if not invalid_pairs:
        logger.info("=== CORRECT: no invalid pairs to process ===")
        return [], []

    logger.info("=== CORRECT: %d invalid pairs ===", len(invalid_pairs))
    corrected, permanently_failed, stats = run_correction_loop(
        invalid_pairs, validations, settings, client
    )
    logger.info(
        "Correction rate: %.1f%% (%d/%d)",
        stats.correction_rate * 100,
        stats.corrected_pairs,
        stats.total_pairs,
    )
    return corrected, permanently_failed


def run_label(
    pairs: list[ResumeJobPair], settings
) -> tuple[list[FailureLabels], list]:

    logger.info("=== LABEL: %d pairs ===", len(pairs))
    labels = []
    judge_results = []

    for i, pair in enumerate(pairs):
        lbl = label_pair(pair)
        labels.append(lbl)
        if settings.enable_judge:
            result = judge_pair(pair, settings)
            if result:
                judge_results.append(result)
            logger.info(
                "Judge %d/%d pair %s",
                i + 1, len(pairs), pair.metadata.pair_id[:8],
            )

    _write_jsonl(labels, settings.data_dir / "labels.jsonl")
    if judge_results:
        _write_jsonl(judge_results, settings.data_dir / "judge_results.jsonl")
        logger.info("Saved %d judge results", len(judge_results))

    return labels, judge_results


def run_analyze(
    all_pairs: list[ResumeJobPair],
    valid_pairs: list[ResumeJobPair],
    invalid_pairs: list[ResumeJobPair],
    labels: list[FailureLabels],
    validations: dict[str, ValidationResult],
    correction_stats: CorrectionStats,
    settings,
    judge_results: list | None = None,
) -> None:

    logger.info("=== ANALYZE ===")
    df = build_labels_dataframe(valid_pairs, labels)
    if df.empty:
        logger.warning("No labeled pairs — skipping analysis")
        return

    field_failures = schema_field_failure_rates(list(validations.values()))
    summary = build_pipeline_summary(
        all_pairs, valid_pairs, invalid_pairs,
        labels, list(validations.values()),
        correction_stats, df,
        judge_results=judge_results or [],
    )
    save_pipeline_summary(summary, settings.data_dir)
    generate_all_charts(df, field_failures, settings.visuals_dir)
    logger.info("Analysis complete")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Resume-Job Pipeline")
    parser.add_argument(
        "--mode",
        choices=["generate", "validate", "correct", "label", "analyze", "all"],
        default="all",
        help="Pipeline stage to run (default: all)",
    )
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_dirs()
    client = get_instructor_client(settings)

    if args.mode in ("generate", "all"):
        jobs, all_pairs = run_generate(settings, client)
    else:
        all_pairs = _read_jsonl(settings.data_dir / "pairs.jsonl", ResumeJobPair)
        logger.info("Loaded %d pairs from disk", len(all_pairs))

    if args.mode in ("validate", "all"):
        valid_pairs, invalid_pairs, validations = run_validate(all_pairs)
        _write_jsonl(valid_pairs, settings.data_dir / "valid_pairs.jsonl")
        _write_jsonl(invalid_pairs, settings.data_dir / "invalid_pairs.jsonl")
    else:
        valid_pairs = _read_jsonl(
            settings.data_dir / "valid_pairs.jsonl", ResumeJobPair
        )
        invalid_pairs = _read_jsonl(
            settings.data_dir / "invalid_pairs.jsonl", ResumeJobPair
        )
        validations = {p.metadata.pair_id: validate_pair(p) for p in invalid_pairs}

    if args.mode in ("correct", "all"):
        corrected, permanently_failed = run_correct(
            invalid_pairs, validations, settings, client
        )
        _write_jsonl(corrected, settings.data_dir / "corrected_pairs.jsonl")
        correction_stats = CorrectionStats(
            total_pairs=len(invalid_pairs),
            corrected_pairs=len(corrected),
            permanently_failed=len(permanently_failed),
        )
        valid_pairs = valid_pairs + corrected
    else:
        corrected = _read_jsonl(
            settings.data_dir / "corrected_pairs.jsonl", ResumeJobPair
        )
        correction_stats = CorrectionStats()

    if args.mode in ("label", "all"):
        labels, judge_results = run_label(valid_pairs, settings)
    else:
        labels = _read_jsonl(settings.data_dir / "labels.jsonl", FailureLabels)
        from pipeline.schemas import JudgeResult
        judge_results = _read_jsonl(
            settings.data_dir / "judge_results.jsonl", JudgeResult
        )

    if args.mode in ("analyze", "all"):
        run_analyze(
            all_pairs, valid_pairs, invalid_pairs,
            labels, validations, correction_stats, settings,
            judge_results=judge_results,
        )

    logger.info("Pipeline complete. Mode: %s", args.mode)


if __name__ == "__main__":
    main()
