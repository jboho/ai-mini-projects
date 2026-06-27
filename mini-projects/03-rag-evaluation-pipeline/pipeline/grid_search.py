"""Grid search orchestration across chunking x embedding x retrieval configs.

For each chunking config the pipeline parses + chunks the PDF once and generates
a dedicated synthetic QA dataset. BM25 is embedding-independent, so it is
computed once per chunking config and not repeated per embedding model.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import retriever as ret
from .chunker import create_chunks
from .config import CACHE_DIR, RESULTS_DIR, GridSearchConfig, RetrievalMethod
from .embedder import embed_batch, embed_chunks
from .evaluator import evaluate_retrieval
from .models import Chunk, ExperimentResult, MetricsResult, QAExample
from .parser import extract_full_text, parse_pdf
from .qa_generator import generate_qa_dataset
from .vectorstore import build_index

logger = logging.getLogger(__name__)
console = Console()


def _qa_cache_path(cache_key: str) -> Path:
    return CACHE_DIR / f"qa_{cache_key}.json"


def _load_or_generate_qa(
    chunks: list[Chunk], cache_key: str, num_questions: int, use_cache: bool
) -> list[QAExample]:
    path = _qa_cache_path(cache_key)
    if use_cache and path.exists():
        data = json.loads(path.read_text())
        logger.info("Loaded cached QA dataset: %s", path.name)
        return [QAExample(**item) for item in data]

    dataset = generate_qa_dataset(chunks, num_questions=num_questions)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([qa.model_dump() for qa in dataset], indent=2))
    return dataset


def _bm25_results(qa: list[QAExample], chunks: list[Chunk], k: int) -> list:
    bm25 = ret.build_bm25(chunks)
    return [ret.retrieve_bm25(ex.question, chunks, k, bm25=bm25) for ex in qa]


def _vector_results(qa, chunks, index, query_vecs, k):
    return [
        ret.retrieve_vector(ex.question, query_vecs[i], chunks, index, k) for i, ex in enumerate(qa)
    ]


def _hybrid_results(qa, chunks, index, query_vecs, k, alpha):
    bm25 = ret.build_bm25(chunks)
    return [
        ret.retrieve_hybrid(ex.question, query_vecs[i], chunks, index, k, alpha, bm25=bm25)
        for i, ex in enumerate(qa)
    ]


def run_grid_search(
    config: GridSearchConfig,
    pdf_path: str | Path,
    use_cache: bool = True,
    on_event=None,
) -> list[ExperimentResult]:
    """Run every (chunking, embedding, retrieval) experiment and return results.

    ``on_event`` is an optional ``callable(message: str)`` invoked at each stage
    (parse, chunk, QA, embed, retrieve) so a UI can stream progress.
    """

    def emit(msg: str) -> None:
        if on_event:
            on_event(msg)

    top_k = max(config.k_values)
    dataset = Path(pdf_path).stem
    results: list[ExperimentResult] = []

    for chunking in config.chunking_configs:
        # Cache key must include the source PDF; chunking.cache_key alone would
        # collide across documents that share a chunking config.
        cache_key = f"{dataset}_{chunking.cache_key}"
        emit(f"Parsing + chunking ({chunking.label})")
        pages = parse_pdf(pdf_path, parser=chunking.parser)
        text = extract_full_text(pages)
        chunks = create_chunks(text, chunking, pages)
        if not chunks:
            logger.warning("No chunks for %s; skipping", chunking.label)
            continue

        emit(f"Generating QA dataset ({chunking.label}, {len(chunks)} chunks)")
        qa = _load_or_generate_qa(chunks, cache_key, config.num_questions, use_cache)
        if not qa:
            logger.warning("No QA examples for %s; skipping", chunking.label)
            continue

        logger.info("Config %s: %d chunks, %d questions", chunking.label, len(chunks), len(qa))

        if RetrievalMethod.BM25 in config.retrieval_methods:
            emit(f"Retrieving + evaluating BM25 ({chunking.label})")
            metrics = evaluate_retrieval(qa, _bm25_results(qa, chunks, top_k), config.k_values)
            results.append(_make_result(chunking.label, "none", RetrievalMethod.BM25, metrics))

        for model in config.embedding_models:
            emit(f"Embedding ({chunking.label}, {model})")
            embeddings = embed_chunks(chunks, model, cache_key)
            index = build_index(embeddings)
            query_vecs = embed_batch([ex.question for ex in qa], model)

            if RetrievalMethod.VECTOR in config.retrieval_methods:
                emit(f"Retrieving + evaluating vector ({chunking.label}, {model})")
                metrics = evaluate_retrieval(
                    qa, _vector_results(qa, chunks, index, query_vecs, top_k), config.k_values
                )
                results.append(_make_result(chunking.label, model, RetrievalMethod.VECTOR, metrics))

            if RetrievalMethod.HYBRID in config.retrieval_methods:
                emit(f"Retrieving + evaluating hybrid ({chunking.label}, {model})")
                metrics = evaluate_retrieval(
                    qa,
                    _hybrid_results(qa, chunks, index, query_vecs, top_k, config.hybrid_alpha),
                    config.k_values,
                )
                results.append(_make_result(chunking.label, model, RetrievalMethod.HYBRID, metrics))

    return results


def _make_result(
    chunking_label: str, model: str, method: RetrievalMethod, metrics: MetricsResult
) -> ExperimentResult:
    return ExperimentResult(
        experiment_id=f"{chunking_label}__{model}__{method.value}",
        embedding_model=model,
        chunking_method=chunking_label,
        retrieval_method=method.value,
        metrics=metrics,
    )


def find_best_config(results: list[ExperimentResult], metric: str = "mrr") -> ExperimentResult:
    if not results:
        raise ValueError("no results to rank")
    return max(results, key=lambda r: getattr(r.metrics, metric))


def display_results_table(results: list[ExperimentResult], sort_by: str = "mrr") -> None:
    table = Table(title="RAG Grid Search Results (sorted by %s)" % sort_by.upper())
    table.add_column("Chunking", style="cyan", overflow="fold")
    table.add_column("Embedding", style="magenta")
    table.add_column("Retrieval", style="green")
    table.add_column("MRR", justify="right")
    table.add_column("MAP", justify="right")
    table.add_column("Recall@5", justify="right")
    table.add_column("NDCG@5", justify="right")
    table.add_column("ms", justify="right")

    ranked = sorted(results, key=lambda r: getattr(r.metrics, sort_by), reverse=True)
    for r in ranked:
        m = r.metrics
        table.add_row(
            r.chunking_method,
            r.embedding_model,
            r.retrieval_method,
            f"{m.mrr:.3f}",
            f"{m.map_score:.3f}",
            f"{m.recall_at_k.get('5', 0.0):.3f}",
            f"{m.ndcg_at_k.get('5', 0.0):.3f}",
            f"{m.avg_retrieval_time * 1000:.1f}",
        )
    console.print(table)


def save_results(results: list[ExperimentResult], path: str | Path | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(path) if path else RESULTS_DIR / "grid_search_results.json"
    payload = [r.model_dump() for r in results]
    path.write_text(json.dumps(payload, indent=2))
    logger.info("Saved %d results to %s", len(results), path)
    return path
