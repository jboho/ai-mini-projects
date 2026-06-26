"""CLI for the customer feedback pipeline.

python run_pipeline.py --mode full [--sample-size 3000] [--source all|amazon|yelp|app_store]
python run_pipeline.py --mode full --crew          # CrewAI orchestration
python run_pipeline.py --mode ingest-only          # just load + normalize
python run_pipeline.py --mode sentiment-only       # ingest + sentiment
"""

from __future__ import annotations

import argparse
import logging

from rich.console import Console

from pipeline.config import load_config
from pipeline.crew import run_crew
from pipeline.orchestrator import run_pipeline, save_output
from pipeline.report import generate_reports

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Customer feedback multi-agent pipeline")
    parser.add_argument("--mode", choices=["full", "ingest-only", "sentiment-only"], default="full")
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--source", choices=["all", "amazon", "yelp", "app_store"], default="all")
    parser.add_argument("--crew", action="store_true", help="use CrewAI orchestration")
    parser.add_argument("-r", "--roadmap", default=None)
    parser.add_argument("--no-visuals", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s"
    )

    config = load_config()
    sources = None if args.source == "all" else [args.source]
    runner = run_crew if args.crew else run_pipeline

    output = runner(
        config,
        sources=sources,
        sample_size=args.sample_size,
        roadmap_path=args.roadmap,
        stop_after=args.mode,
        on_event=lambda m: console.print(f"  [dim]{m}[/dim]"),
    )
    path = save_output(output)
    console.print(f"[green]Saved pipeline output -> {path.name}[/green]")

    if args.mode == "full" and not args.no_visuals:
        md, html = generate_reports(output)
        console.print(f"[green]Reports: {md.name}, {html.name}[/green]")
        gaps = [g for g in output.gaps if not g.has_coverage]
        console.print("\n[bold]Top unaddressed needs:[/bold]")
        for g in gaps[:5]:
            console.print(
                f"  • {g.theme_name} (priority {g.priority_score:.2f}, {g.feedback_count} reviews)"
            )


if __name__ == "__main__":
    main()
