"""CLI entrypoint for the RAG evaluation grid search.

Modes:
  full        Run the complete grid search (parse -> chunk -> QA -> embed -> retrieve -> eval)
  parse-only  Parse the PDF and print extraction + chunking stats only (no API calls)
  evaluate    Re-run the grid search reusing cached QA datasets and embeddings
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from pipeline.chunker import create_chunks
from pipeline.config import DEFAULT_CHUNKING_CONFIGS, RESULTS_DIR, GridSearchConfig
from pipeline.grid_search import (
    display_results_table,
    find_best_config,
    run_grid_search,
    save_results,
)
from pipeline.parser import extract_full_text, parse_pdf

console = Console()


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )


def _parse_only(pdf_path: str) -> None:
    pages = parse_pdf(pdf_path)
    text = extract_full_text(pages)
    console.print(f"[bold]Pages:[/bold] {len(pages)}    [bold]Chars:[/bold] {len(text)}")
    for cfg in DEFAULT_CHUNKING_CONFIGS:
        chunks = create_chunks(text, cfg, pages)
        sizes = [len(c.text.split()) for c in chunks]
        avg = sum(sizes) / len(sizes) if sizes else 0
        console.print(f"  {cfg.label:<45} chunks={len(chunks):>4}  avg_words={avg:6.1f}")


def _run(pdf_path: str, num_questions: int, use_cache: bool) -> None:
    config = GridSearchConfig(num_questions=num_questions)
    console.print(
        f"[bold]Grid:[/bold] up to {config.total_experiments} experiments "
        f"({len(config.chunking_configs)} chunking x {len(config.embedding_models)} "
        f"embedding x {len(config.retrieval_methods)} retrieval); "
        "BM25 is embedding-independent and computed once per chunking config"
    )
    results = run_grid_search(config, pdf_path, use_cache=use_cache)
    if not results:
        console.print("[red]No results produced. Check the PDF and API configuration.[/red]")
        return

    display_results_table(results)
    stem = Path(pdf_path).stem
    save_results(results, RESULTS_DIR / f"{stem}_results.json")
    best = find_best_config(results, metric="mrr")
    console.print(
        f"\n[bold green]Best by MRR:[/bold green] {best.experiment_id} "
        f"(MRR={best.metrics.mrr:.3f}, Recall@5={best.metrics.recall_at_k.get('5', 0.0):.3f})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG evaluation grid search")
    parser.add_argument("--mode", choices=["full", "parse-only", "evaluate"], default="full")
    parser.add_argument("--pdf", required=True, help="Path to the input PDF")
    parser.add_argument("--num-questions", type=int, default=20)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    _configure_logging(args.verbose)

    if args.mode == "parse-only":
        _parse_only(args.pdf)
    else:
        _run(args.pdf, args.num_questions, use_cache=args.mode == "evaluate")


if __name__ == "__main__":
    main()
