#!/usr/bin/env python3
"""CLI entrypoint for the DIY Repair Synthetic Data Pipeline.

Usage:
    python run_pipeline.py --mode baseline [--num-items 50]
    python run_pipeline.py --mode corrected [--num-items 50]
    python run_pipeline.py --mode compare
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from pipeline.analyzer import (
    build_failure_dataframe,
    confidence_interval,
    generate_summary,
    overall_failure_rate,
    per_mode_failure_rates,
    plot_before_after,
    plot_cooccurrence_heatmap,
    plot_failure_by_category,
)
from pipeline.client import get_model_name
from pipeline.corrector import CORRECTION_LOG, get_corrected_prompts
from pipeline.generator import BASELINE_PROMPTS, generate_items
from pipeline.judge import judge_records
from pipeline.models import FAILURE_MODES, PipelineRecord
from pipeline.validator import validate_generation_results

DATA_DIR = Path(__file__).resolve().parent / "data"

logger = logging.getLogger("pipeline")


def _save_records(records: list[PipelineRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for rec in records:
            f.write(rec.model_dump_json() + "\n")
    logger.info("Saved %d records to %s", len(records), path)


def _load_records(path: Path) -> list[PipelineRecord]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(PipelineRecord.model_validate_json(line))
    logger.info("Loaded %d records from %s", len(records), path)
    return records


def _print_summary(summary: dict) -> None:
    tag = summary["tag"]
    total = summary["total_generated"]
    valid = summary["passed_validation"]
    judged = summary["judged"]
    overall = summary["overall_failure_rate"]
    ci = summary["overall_failure_ci_95"]
    rates = summary["per_mode_rates"]
    coverage = summary["category_coverage"]

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE SUMMARY — {tag.upper()}")
    print(f"{'=' * 60}")
    print(f"  Generated:       {total}")
    print(f"  Passed validation: {valid}/{total} ({valid/total*100:.1f}%)")
    print(f"  Judged:          {judged}")
    print(f"  Overall failure: {overall:.1%}  (95% CI: {ci[0]:.1%} – {ci[1]:.1%})")
    print()
    print("  Per-mode failure rates:")
    for mode in FAILURE_MODES:
        r = rates[mode]
        print(f"    {mode:30s} {r:.1%}")
    print()
    print(f"  Category coverage: {'ALL 5 represented' if coverage['all_represented'] else 'MISSING categories!'}")
    for cat, cnt in coverage["counts"].items():
        print(f"    {cat:15s} {cnt}")
    print(f"  Shannon entropy:   {coverage['entropy']:.2f}")

    worst = summary.get("worst_items", [])
    if worst:
        print(f"\n  Worst items (3+ failures):")
        for w in worst:
            print(f"    {w['trace_id']} [{w['category']}] — {w['failure_count']} failures")
    print()


def run_generation_pipeline(
    num_items: int,
    *,
    prompts: dict | None = None,
    prompt_version: str = "baseline",
    tag: str = "baseline",
) -> list[PipelineRecord]:
    """Phases 1-3: generate, validate, judge."""
    model_name = get_model_name()

    print(f"\n--- Phase 1: Generating {num_items} items ({tag}) ---")
    results = generate_items(
        num_items, prompts=prompts, prompt_version=prompt_version
    )

    print(f"\n--- Phase 2: Structural validation ---")
    records = validate_generation_results(
        results, prompt_version=prompt_version, model_name=model_name
    )

    print(f"\n--- Phase 3: LLM-as-Judge evaluation ---")
    records = judge_records(records)

    return records


def cmd_baseline(args: argparse.Namespace) -> None:
    records = run_generation_pipeline(
        args.num_items,
        prompts=BASELINE_PROMPTS,
        prompt_version="baseline",
        tag="baseline",
    )

    path = DATA_DIR / "baseline.jsonl"
    _save_records(records, path)

    print("\n--- Phase 4: Failure analysis ---")
    df = build_failure_dataframe(records)
    if df.empty:
        print("  No judged items to analyze.")
        return

    summary = generate_summary(records, tag="baseline")
    _print_summary(summary)

    report_path = DATA_DIR / "baseline_summary.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Summary saved to {report_path}")

    plot_cooccurrence_heatmap(df, tag="baseline")
    plot_failure_by_category(df, tag="baseline")
    print("  Charts saved to visuals/")


def cmd_corrected(args: argparse.Namespace) -> None:
    corrected_prompts = get_corrected_prompts()

    print("\n--- Correction log ---")
    for entry in CORRECTION_LOG:
        print(f"  [{entry['failure_mode']}] {entry['change']}")
        print(f"    Reason: {entry['reason']}")

    records = run_generation_pipeline(
        args.num_items,
        prompts=corrected_prompts,
        prompt_version="corrected",
        tag="corrected",
    )

    path = DATA_DIR / "corrected.jsonl"
    _save_records(records, path)

    df = build_failure_dataframe(records)
    if df.empty:
        print("  No judged items to analyze.")
        return

    summary = generate_summary(records, tag="corrected")
    _print_summary(summary)

    report_path = DATA_DIR / "corrected_summary.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Summary saved to {report_path}")

    plot_cooccurrence_heatmap(df, tag="corrected")
    plot_failure_by_category(df, tag="corrected")
    print("  Charts saved to visuals/")


def cmd_compare(args: argparse.Namespace) -> None:
    baseline_path = DATA_DIR / "baseline.jsonl"
    corrected_path = DATA_DIR / "corrected.jsonl"

    for p in [baseline_path, corrected_path]:
        if not p.exists():
            print(f"ERROR: {p} not found. Run --mode baseline and --mode corrected first.")
            sys.exit(1)

    baseline_records = _load_records(baseline_path)
    corrected_records = _load_records(corrected_path)

    df_b = build_failure_dataframe(baseline_records)
    df_c = build_failure_dataframe(corrected_records)

    if df_b.empty or df_c.empty:
        print("ERROR: One or both datasets have no judged records.")
        sys.exit(1)

    rates_b = per_mode_failure_rates(df_b)
    rates_c = per_mode_failure_rates(df_c)
    overall_b = overall_failure_rate(df_b)
    overall_c = overall_failure_rate(df_c)
    ci_b = confidence_interval(overall_b, len(df_b))
    ci_c = confidence_interval(overall_c, len(df_c))

    if overall_b > 0:
        improvement = (overall_b - overall_c) / overall_b
    else:
        improvement = 0.0

    print(f"\n{'=' * 72}")
    print("  BEFORE / AFTER COMPARISON")
    print(f"{'=' * 72}")
    print(f"  {'Failure Mode':30s} {'Baseline':>10s} {'Corrected':>10s} {'Reduction':>10s}")
    print(f"  {'-' * 62}")

    for mode in FAILURE_MODES:
        b = rates_b[mode]
        c = rates_c[mode]
        if b > 0:
            red = (b - c) / b
        else:
            red = 0.0
        print(f"  {mode:30s} {b:>9.1%} {c:>10.1%} {red:>10.1%}")

    print(f"  {'-' * 62}")
    print(f"  {'OVERALL':30s} {overall_b:>9.1%} {overall_c:>10.1%} {improvement:>10.1%}")
    print()
    print(f"  Baseline  95% CI: {ci_b[0]:.1%} – {ci_b[1]:.1%}  (n={len(df_b)})")
    print(f"  Corrected 95% CI: {ci_c[0]:.1%} – {ci_c[1]:.1%}  (n={len(df_c)})")

    overlap = ci_b[0] <= ci_c[1] and ci_c[0] <= ci_b[1]
    if overlap:
        print("  WARNING: Confidence intervals overlap — improvement may not be statistically significant.")

    print()
    if improvement >= 0.80:
        print(f"  RESULT: PASS — {improvement:.1%} improvement (target: >= 80%)")
    else:
        print(f"  RESULT: FAIL — {improvement:.1%} improvement (target: >= 80%)")

    plot_before_after(rates_b, rates_c)
    print("  Before/after chart saved to visuals/before_after_comparison.png")

    comparison = {
        "baseline_overall": overall_b,
        "corrected_overall": overall_c,
        "improvement": improvement,
        "baseline_ci_95": ci_b,
        "corrected_ci_95": ci_c,
        "ci_overlap": overlap,
        "per_mode_baseline": rates_b,
        "per_mode_corrected": rates_c,
        "pass": improvement >= 0.80,
    }
    report_path = DATA_DIR / "comparison.json"
    with open(report_path, "w") as f:
        json.dump(comparison, f, indent=2, default=str)
    print(f"  Comparison report saved to {report_path}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DIY Repair Synthetic Data Pipeline",
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "corrected", "compare"],
        required=True,
        help="Pipeline mode to run.",
    )
    parser.add_argument(
        "--num-items",
        type=int,
        default=50,
        help="Number of Q&A pairs to generate (default: 50).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.mode == "baseline":
        cmd_baseline(args)
    elif args.mode == "corrected":
        cmd_corrected(args)
    elif args.mode == "compare":
        cmd_compare(args)


if __name__ == "__main__":
    main()
