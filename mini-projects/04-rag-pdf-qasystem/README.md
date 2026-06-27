# 04 — RAG PDF QA System

A modular Retrieval-Augmented Generation system over arXiv papers, evaluated on
the [Vectara Open RAG Benchmark](https://huggingface.co/datasets/vectara/open_ragbench)
(1,000 papers, 3,045 QA pairs with ground truth). Chunking, embedding,
retrieval, and reranking are all swappable through abstract base classes and
YAML config, with rigorous IR evaluation, an LLM-as-Judge, CLI tools, and a
Streamlit UI.

## Quickstart

```bash
cd mini-projects/04-rag-pdf-qasystem
pip install -r requirements.txt
cp .env.example .env                 # add a chat key (OpenRouter/OpenAI/Anthropic)

python scripts/download_dataset.py --limit 50     # fetch metadata + 50 corpus papers
python scripts/evaluate.py                         # run the 24-config IR grid
python scripts/query.py                            # interactive QA with citations
streamlit run app.py                               # web UI
```

The benchmark ships **pre-parsed corpus JSON per paper**, so the pipeline runs
without downloading any PDFs. Embeddings and cross-encoder reranking are
**local** (sentence-transformers); only answer generation and the LLM judge need
an API key.

## Architecture

```
Ingestion:  corpus JSON -> loader -> Document(sections) -> chunker -> embedder -> FAISS
Query:      question -> retriever (dense/BM25/hybrid) -> reranker? -> generator -> answer + [N] citations
Evaluation: qrels -> relevant chunks (section overlap) -> IR metrics; answers -> LLM judge
```

All swappable components implement ABCs in `rag/interfaces.py` and are built by
factory functions from `RunConfig` (`rag/config.py`).

| Module | Responsibility |
|--------|----------------|
| `loader.py` | corpus JSON → Document with per-section char spans; PDF loader |
| `chunkers.py` | fixed / sliding / recursive / semantic, token-sized with offsets |
| `embedder.py` | sentence-transformers, L2-normalized, npz cache |
| `vector_store.py` | FAISS `IndexFlatIP` (cosine) + chunk metadata + save/load |
| `retrievers.py` | dense / BM25 / hybrid (min-max fusion) |
| `rerankers.py` | Cohere API + local cross-encoder |
| `generator.py` | LLM answer + `[N]` citation extraction |
| `llm_judge.py` | 4-criteria structured judge (relevance/accuracy/completeness/citation) |
| `metrics.py` | Precision@K, Recall@K, MRR, MAP, NDCG@K |
| `experiments.py` | grid orchestration + qrel ground-truth eval + Rich/JSON output |
| `pipeline.py` | query-time assembly for the CLI/app |

## Ground-truth mapping

`qrels.json` maps each query to `{doc_id, section_id}`. The loader records each
section's character span; every chunk stores the section indices it overlaps. A
retrieved chunk is **relevant** if its `doc_id` matches the qrel and the qrel
`section_id` is among the chunk's sections.

## Configuration

`config/default.yaml` is a single run; `config/experiments/baseline.yaml` defines
the grid (the cartesian product of chunkers × embedders × retrievers × rerankers
= 24 configs). Provider and models are set via `.env` (`QA_PROVIDER`,
`QA_MODEL_NAME`, `JUDGE_MODEL_NAME`).

## Evaluation results

A 12-config grid (4 chunkers × MiniLM × dense/BM25/hybrid) over the 40-paper /
356-query dev subset (`experiments/results/experiment_results.json`):

| Config | MRR | R@5 | NDCG@5 |
|--------|-----|-----|--------|
| semantic + BM25 | 0.769 | 0.629 | 0.618 |
| sliding + hybrid | 0.765 | 0.445 | 0.542 |
| recursive + BM25 | 0.765 | 0.640 | 0.621 |
| … (dense configs) | 0.60–0.67 | — | — |

**Headline finding (consistent with project 03): BM25 and hybrid retrieval
clearly beat pure dense** on terminology-heavy arXiv text — all four dense
configs sit at the bottom of the table. The plan's targets (P@5 > 0.60,
R@5 > 0.80, NDCG@5 > 0.75) assume a stronger embedder (mpnet) plus reranking;
the MiniLM IR baseline lands MRR up to 0.77 with R@5 ≈ 0.64. Run the full
24-config grid with `python scripts/evaluate.py`, or
`streamlit run app.py` to explore answers interactively.

## Tests

```bash
pytest                      # 34 offline tests (no API key needed)
ruff check . && ruff format --check .
```

Embedding/generation are exercised with fake embedders and known-answer fixtures,
so the suite runs fast and offline.
