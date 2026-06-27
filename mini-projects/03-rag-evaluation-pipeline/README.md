# 03 — RAG Evaluation Pipeline

Modular pipeline that ingests a PDF, chunks it with multiple strategies, embeds
with multiple models, retrieves via BM25 / vector / hybrid, generates a
per-config synthetic QA dataset, and runs a grid search to find the best
retrieval configuration by IR metrics (MRR, MAP, Recall@K, Precision@K, NDCG@K).

## Setup

```bash
cd mini-projects/03-rag-evaluation-pipeline
pip install -r requirements.txt
python -m spacy download en_core_web_sm        # for semantic chunking
cp .env.example .env                            # then add your key
```

Embeddings use the OpenAI API (`text-embedding-3-small` / `-large`); set
`OPENAI_API_KEY`. Synthetic QA generation is provider-configurable via
`QA_PROVIDER` (openrouter / openai / anthropic) with the matching key. The
embedder also supports local sentence-transformers models — swap the names in
`EMBEDDING_MODELS` for a free, offline embedding axis (it dispatches on the
model name).

## Usage

```bash
# Inspect parsing + chunking only — no API calls, no key needed
python run_pipeline.py --mode parse-only --pdf data/pdf/your.pdf

# Full grid search (parse -> chunk -> QA -> embed -> retrieve -> evaluate)
python run_pipeline.py --mode full --pdf data/pdf/your.pdf --num-questions 20

# Re-run evaluation reusing cached QA datasets + embeddings
python run_pipeline.py --mode evaluate --pdf data/pdf/your.pdf
```

Results are written to `results/<pdf>_results.json` and printed as a Rich table
sorted by MRR. Embeddings and QA datasets are cached under `cache/` keyed by the
**PDF stem + chunking-config hash**, so re-runs skip recomputation and different
PDFs never collide.

### Dashboard

```bash
streamlit run dashboard.py
```

Three tabs: **Run** (grid search with live per-stage progress), **Results**
(metric cards, MRR heatmap, per-config bars, sortable table loaded from
`results/*.json`), and **Query Playground** (type a question, see top-k
retrieved chunks instantly using cached embeddings). The full grid run is slow
on the free QA model, so demo from cached results and use the playground for
live interaction.

## Design notes

- **Fair evaluation:** each chunking config gets its own synthetic QA dataset,
  with ground-truth `relevant_chunk_ids` set from the source chunk a question
  was generated from (not trusted from the LLM, which hallucinates ids).
- **Cosine via FAISS:** embeddings are L2-normalized into an `IndexFlatIP`, so
  scores are cosine similarities. Hybrid fusion min-max normalizes BM25 and
  cosine scores across all chunks, then combines `alpha*vector + (1-alpha)*bm25`.
- **BM25 reuse:** BM25 is embedding-independent, so it is computed once per
  chunking config rather than repeated per embedding model.
- **Per-PDF cache key:** caches are keyed by PDF stem + chunking-config hash so
  the same chunking config across different documents never collides.
- **Rate-limit resilience:** QA generation paces calls and backs off on
  transient/rate-limit errors (the free QA model is rate-limited).
- **OpenMP guard:** `pipeline/__init__.py` sets `KMP_DUPLICATE_LIB_OK` because
  faiss and spaCy/torch each bundle an OpenMP runtime that otherwise segfaults
  on macOS when loaded together.

## Tests

```bash
pytest                # offline: chunker, evaluator, retriever (15 tests)
ruff check . && ruff format --check .
```

The test suite needs no API key — embedding-dependent code is exercised with
controlled vectors.

## Module map

| Module | Responsibility |
|--------|----------------|
| `parser.py` | PDF text extraction (pdfplumber / PyPDF2 / PyMuPDF) + page offset map |
| `chunker.py` | fixed-size, sentence, semantic chunking |
| `embedder.py` | OpenAI or local sentence-transformers embedding + `.npz` cache |
| `vectorstore.py` | FAISS index build / search / persist |
| `retriever.py` | BM25, vector, hybrid retrieval (pure, API-free) |
| `qa_generator.py` | Instructor-based synthetic QA tied to chunk ids |
| `evaluator.py` | IR metrics + dataset aggregation |
| `grid_search.py` | experiment orchestration, ranking, Rich table, JSON output |
| `client.py` | QA chat client factory (Anthropic / OpenAI / OpenRouter via Instructor) |
| `run_pipeline.py` | CLI (`full` / `parse-only` / `evaluate`) |
| `dashboard.py` | Streamlit dashboard (shared kit) |
