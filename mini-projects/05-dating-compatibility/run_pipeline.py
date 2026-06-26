"""CLI entrypoint for the dating compatibility pipeline.

Modes: explore | quality | baseline | train | evaluate | compare | all

    python run_pipeline.py --mode all
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from pipeline.data_loader import load_dataset, log_distribution
from pipeline.data_quality import evaluate_quality
from pipeline.evaluator import evaluate_model
from pipeline.models import TARGETS, ComparisonReport, EvaluationMetrics
from pipeline.trainer import BASE_MODEL, train_model

console = Console()
ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
MODEL_DIR = ROOT / "models" / "finetuned-minilm"


def _load_model(path_or_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(path_or_name, device=os.environ.get("EMBED_DEVICE", "cpu"))


def _save_report(obj, name: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / name).write_text(obj.model_dump_json(indent=2))


def mode_explore() -> None:
    train, eval_ = load_dataset()
    log_distribution(train, "train")
    log_distribution(eval_, "eval")


def mode_quality(gate: bool = False) -> bool:
    train, _ = load_dataset()
    report = evaluate_quality(train)
    _save_report(report, "data_quality_report.json")
    table = Table(title=f"Data Quality — overall {report.overall_score:.1f}/100")
    table.add_column("Dimension")
    table.add_column("Score", justify="right")
    for d in report.dimensions:
        table.add_row(d.dimension, f"{d.score:.1f}")
    console.print(table)
    status = "[green]PASS[/green]" if report.passed else "[red]FAIL[/red]"
    console.print(f"Gate (>= {report.threshold:.0f}): {status}")
    if gate and not report.passed:
        console.print("[red]Quality gate failed; aborting before training.[/red]")
    return report.passed


def mode_baseline() -> EvaluationMetrics:
    _, eval_ = load_dataset()
    console.print("[bold]Evaluating baseline model...[/bold]")
    metrics = evaluate_model(_load_model(BASE_MODEL), eval_)
    _save_report(metrics, "baseline_metrics.json")
    return metrics


def mode_train() -> Path:
    train, _ = load_dataset()
    console.print("[bold]Fine-tuning... (this takes a while)[/bold]")
    return train_model(train, MODEL_DIR)


def mode_evaluate() -> EvaluationMetrics:
    _, eval_ = load_dataset()
    if not MODEL_DIR.exists():
        raise FileNotFoundError("No fine-tuned model; run --mode train first.")
    console.print("[bold]Evaluating fine-tuned model...[/bold]")
    metrics = evaluate_model(_load_model(str(MODEL_DIR)), eval_)
    _save_report(metrics, "finetuned_metrics.json")
    return metrics


def _improvement(metric: str, base: float, fine: float) -> float:
    if metric == "false_positive_rate":  # lower is better
        return (base - fine) / base * 100 if base else 0.0
    return (fine - base) / abs(base) * 100 if base else 0.0


def mode_compare(make_visuals: bool = True) -> ComparisonReport:
    base = EvaluationMetrics(**json.loads((REPORTS_DIR / "baseline_metrics.json").read_text()))
    fine = EvaluationMetrics(**json.loads((REPORTS_DIR / "finetuned_metrics.json").read_text()))

    improvements, targets_met = {}, {}
    for m, target in TARGETS.items():
        improvements[m] = _improvement(m, getattr(base, m), getattr(fine, m))
        fv = getattr(fine, m)
        targets_met[m] = fv <= target if m == "false_positive_rate" else fv >= target

    report = ComparisonReport(
        baseline=base, finetuned=fine, improvements=improvements, targets_met=targets_met
    )
    _save_report(report, "comparison_report.json")

    table = Table(title="Baseline vs Fine-tuned")
    for col in ("Metric", "Baseline", "Fine-tuned", "Δ%", "Target"):
        table.add_column(col, justify="right")
    for m in TARGETS:
        mark = "[green]✓[/green]" if targets_met[m] else "[red]✗[/red]"
        table.add_row(
            m,
            f"{getattr(base, m):.3f}",
            f"{getattr(fine, m):.3f}",
            f"{improvements[m]:+.1f}",
            mark,
        )
    console.print(table)

    if make_visuals:
        _generate_visuals(base, fine)
    return report


def _generate_visuals(base: EvaluationMetrics, fine: EvaluationMetrics) -> None:
    from pipeline import visualizer

    _, eval_ = load_dataset()
    bmodel, fmodel = _load_model(BASE_MODEL), _load_model(str(MODEL_DIR))
    console.print("[bold]Generating visualizations...[/bold]")
    visualizer.plot_similarity_distributions(bmodel, fmodel, eval_)
    visualizer.plot_metric_comparison(base, fine)
    visualizer.plot_category_fpr(base, fine)
    visualizer.plot_roc(bmodel, fmodel, eval_)
    visualizer.plot_umap(bmodel, fmodel, eval_)


def mode_all() -> None:
    if not mode_quality(gate=True):
        return
    mode_baseline()
    mode_train()
    mode_evaluate()
    mode_compare()


def main() -> None:
    parser = argparse.ArgumentParser(description="Dating compatibility pipeline")
    parser.add_argument(
        "--mode",
        choices=["explore", "quality", "baseline", "train", "evaluate", "compare", "all"],
        default="all",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )

    dispatch = {
        "explore": mode_explore,
        "quality": mode_quality,
        "baseline": mode_baseline,
        "train": mode_train,
        "evaluate": mode_evaluate,
        "compare": mode_compare,
        "all": mode_all,
    }
    dispatch[args.mode]()


if __name__ == "__main__":
    main()
