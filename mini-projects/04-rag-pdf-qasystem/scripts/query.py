"""CLI: interactive question answering over the downloaded corpus.

    python scripts/query.py                 # uses config/default.yaml
    python scripts/query.py --top-k 5

Requires a chat key (QA_PROVIDER/.env) for answer generation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console  # noqa: E402

from rag.config import load_default_config  # noqa: E402
from rag.loader import load_corpus  # noqa: E402
from rag.pipeline import RAGPipeline  # noqa: E402

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive RAG QA over the corpus")
    parser.add_argument(
        "--config", default=None, help="pipeline YAML (default: config/default.yaml)"
    )
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()

    config = load_default_config(args.config)
    if args.top_k:
        config.top_k = args.top_k

    documents = load_corpus()
    console.print(f"[bold]Indexing {len(documents)} papers ({config.label})...[/bold]")
    pipeline = RAGPipeline(config, documents)
    console.print("Ready. Ask a question (empty line to quit).\n")

    while True:
        try:
            question = console.input("[bold cyan]?[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        response = pipeline.answer(question)
        console.print(f"\n[bold green]Answer:[/bold green] {response.answer}\n")
        for cite in response.citations:
            snippet = cite.text[:120].replace("\n", " ")
            console.print(f"  [{cite.marker}] ({cite.doc_id}) {snippet}...")
        console.print()


if __name__ == "__main__":
    main()
