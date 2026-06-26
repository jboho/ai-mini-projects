"""Retrieval evaluation: Recall@5, Precision@5, MRR for semantic-only vs hybrid.

    python eval/eval_retrieval.py            # uses real embeddings if OPENAI_API_KEY set
    python eval/eval_retrieval.py --stub     # force the offline stub embedder

Writes eval/results_retrieval.json so demos ship with populated numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.common import (  # noqa: E402
    StubEmbedder,
    build_sample_env,
    default_embedder,
    mean,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
QUERIES_PATH = EVAL_DIR / "test_queries.json"
RESULTS_PATH = EVAL_DIR / "results_retrieval.json"


def _score(keys_for_query, queries, k: int = 5) -> dict:
    recalls, precisions, rrs = [], [], []
    for q in queries:
        retrieved = keys_for_query(q["query"])
        recalls.append(recall_at_k(retrieved, q["relevant"], k))
        precisions.append(precision_at_k(retrieved, q["relevant"], k))
        rrs.append(reciprocal_rank(retrieved, q["relevant"]))
    return {
        "recall@5": round(mean(recalls), 4),
        "precision@5": round(mean(precisions), 4),
        "mrr": round(mean(rrs), 4),
    }


def run_eval(embedder=None, k: int = 5) -> dict:
    queries = json.loads(QUERIES_PATH.read_text())["queries"]
    embedder = embedder or default_embedder()
    _session, _issues, store = build_sample_env(embedder)

    semantic = _score(lambda q: [r["key"] for r in store.semantic_search(q, limit=k)], queries, k)
    hybrid = _score(lambda q: [r["key"] for r in store.hybrid_search(q, limit=k)], queries, k)

    base = semantic["recall@5"] or 1e-9
    improvement = round(100 * (hybrid["recall@5"] - semantic["recall@5"]) / base, 2)
    return {
        "embedder": type(embedder).__name__,
        "n_queries": len(queries),
        "semantic": semantic,
        "hybrid": hybrid,
        "hybrid_recall_improvement_pct": improvement,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality.")
    parser.add_argument("--stub", action="store_true", help="Force the offline stub embedder.")
    args = parser.parse_args()

    results = run_eval(embedder=StubEmbedder() if args.stub else None)
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")

    print(f"Embedder: {results['embedder']}  ({results['n_queries']} queries)")
    print(f"  semantic: {results['semantic']}")
    print(f"  hybrid:   {results['hybrid']}")
    print(f"  hybrid recall improvement: {results['hybrid_recall_improvement_pct']}%")
    print(f"Wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
