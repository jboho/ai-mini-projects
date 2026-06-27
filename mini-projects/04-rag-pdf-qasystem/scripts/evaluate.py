"""CLI: run the experiment grid from a YAML config and report IR metrics.

python scripts/evaluate.py                          # baseline grid
python scripts/evaluate.py --experiment config/experiments/baseline.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console  # noqa: E402
from rich.logging import RichHandler  # noqa: E402

from rag.config import RESULTS_DIR, load_experiment_grid  # noqa: E402
from rag.experiments import (  # noqa: E402
    display_results_table,
    find_best,
    run_grid,
    save_results,
)

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RAG experiment grid")
    parser.add_argument("--experiment", default=None, help="experiment YAML path")
    parser.add_argument("--sort-by", default="mrr")
    parser.add_argument("--output", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )

    configs = load_experiment_grid(args.experiment)
    console.print(
        f"[bold]Running {len(configs)} configurations over the downloaded corpus...[/bold]"
    )
    results = run_grid(configs, on_event=lambda m: console.print(f"  {m}"))
    display_results_table(results, args.sort_by)
    path = save_results(results, args.output or RESULTS_DIR / "experiment_results.json")
    best = find_best(results, args.sort_by)
    console.print(
        f"\n[bold green]Best by {args.sort_by.upper()}:[/bold green] {best.experiment_id} "
        f"(MRR={best.metrics.mrr:.3f}, R@5={best.metrics.recall_at_k.get('5', 0.0):.3f})"
    )
    console.print(f"Saved to {path}")


if __name__ == "__main__":
    main()
