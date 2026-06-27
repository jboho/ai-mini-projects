"""Experiment orchestration: run RunConfig cells and evaluate against qrels.

Ground truth: a chunk is relevant to a query if its doc_id matches the qrel's
doc_id and the qrel section index is among the chunk's overlapping sections.
Retrieval IR metrics need no API; only the optional LLM judge does.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .chunkers import get_chunker
from .config import DATA_DIR, RESULTS_DIR, RunConfig
from .embedder import embed_chunks, get_embedder
from .loader import load_corpus
from .metrics import evaluate_retrieval
from .models import Chunk, Document, ExperimentResult
from .rerankers import get_reranker
from .retrievers import get_retriever
from .vector_store import VectorStore

logger = logging.getLogger(__name__)
console = Console()


def load_eval_set(data_dir: Path | None = None) -> tuple[dict, dict]:
    """Return (queries, qrels) dicts from the downloaded metadata."""
    data_dir = data_dir or DATA_DIR
    queries = json.loads((data_dir / "queries.json").read_text())
    qrels = json.loads((data_dir / "qrels.json").read_text())
    return queries, qrels


def _relevant_chunk_ids(qrel: dict, chunks_by_doc: dict[str, list[Chunk]]) -> set[str]:
    doc_id = qrel["doc_id"]
    section_id = qrel["section_id"]
    return {c.id for c in chunks_by_doc.get(doc_id, []) if section_id in c.section_indices}


def run_experiment(
    config: RunConfig,
    documents: list[Document],
    queries: dict,
    qrels: dict,
) -> ExperimentResult:
    """Run one configuration end-to-end and compute IR metrics."""
    embedder = get_embedder(config.embedder)
    # Grid chunking uses the fast token-budget semantic path; the embedding-
    # breakpoint mode (slow per config) stays available for single-query use.
    chunker = get_chunker(config.chunker)

    chunks: list[Chunk] = []
    chunks_by_doc: dict[str, list[Chunk]] = {}
    for doc in documents:
        doc_chunks = chunker.chunk(doc)
        chunks.extend(doc_chunks)
        chunks_by_doc[doc.doc_id] = doc_chunks

    embeddings = embed_chunks(embedder, chunks, config.cache_key)
    store = VectorStore.from_embeddings(embeddings, chunks)
    retriever = get_retriever(config.retriever, embedder, store, chunks)
    reranker = get_reranker(config.reranker)
    candidate_k = config.top_k if reranker is None else max(config.top_k * 3, 20)

    doc_ids = set(chunks_by_doc)
    eval_qids = [qid for qid, rel in qrels.items() if rel["doc_id"] in doc_ids]

    per_query, times = [], []
    for qid in eval_qids:
        relevant = _relevant_chunk_ids(qrels[qid], chunks_by_doc)
        if not relevant:
            continue
        t0 = time.perf_counter()
        retrieved = retriever.retrieve(queries[qid]["query"], candidate_k)
        if reranker is not None:
            retrieved = reranker.rerank(queries[qid]["query"], retrieved, config.top_k)
        else:
            retrieved = retrieved[: config.top_k]
        times.append(time.perf_counter() - t0)
        per_query.append((relevant, [r.chunk_id for r in retrieved]))

    metrics = evaluate_retrieval(per_query, config.k_values, times)
    logger.info("%s -> MRR=%.3f over %d queries", config.label, metrics.mrr, metrics.total_queries)
    return ExperimentResult(
        experiment_id=config.label,
        config=config.model_dump(),
        metrics=metrics,
        num_queries=metrics.total_queries,
    )


def run_grid(
    configs: list[RunConfig], documents: list[Document] | None = None, on_event=None
) -> list[ExperimentResult]:
    documents = documents if documents is not None else load_corpus()
    queries, qrels = load_eval_set()
    results = []
    for i, cfg in enumerate(configs, start=1):
        if on_event:
            on_event(f"[{i}/{len(configs)}] {cfg.label}")
        results.append(run_experiment(cfg, documents, queries, qrels))
    return results


def find_best(results: list[ExperimentResult], metric: str = "mrr") -> ExperimentResult:
    if not results:
        raise ValueError("no results to rank")
    return max(results, key=lambda r: getattr(r.metrics, metric))


def display_results_table(results: list[ExperimentResult], sort_by: str = "mrr") -> None:
    table = Table(title=f"RAG Experiments (sorted by {sort_by.upper()})")
    for col in ("Config", "MRR", "MAP", "P@5", "R@5", "NDCG@5", "Q"):
        table.add_column(col, overflow="fold")
    for r in sorted(results, key=lambda r: getattr(r.metrics, sort_by), reverse=True):
        m = r.metrics
        table.add_row(
            r.experiment_id,
            f"{m.mrr:.3f}",
            f"{m.map_score:.3f}",
            f"{m.precision_at_k.get('5', 0.0):.3f}",
            f"{m.recall_at_k.get('5', 0.0):.3f}",
            f"{m.ndcg_at_k.get('5', 0.0):.3f}",
            str(r.num_queries),
        )
    console.print(table)


def save_results(results: list[ExperimentResult], path: str | Path | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(path) if path else RESULTS_DIR / "experiment_results.json"
    path.write_text(json.dumps([r.model_dump() for r in results], indent=2))
    logger.info("Saved %d results to %s", len(results), path)
    return path
