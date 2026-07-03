# AI-Powered Jira Copilot

A multi-agent assistant over a Jira-style issue tracker (the [TAWOS](https://github.com/SOLAR-group/TAWOS) dataset schema). It does hybrid retrieval, natural-language query understanding, five kinds of issue suggestions, sprint planning, simulation-first writes, release-note generation, and analytics — exposed through both a **REST API (33 endpoints)** and a **Typer CLI**.

The project runs end-to-end **without the real TAWOS MySQL dump**: a synthetic, TAWOS-shaped sample dataset ships in-repo so you can try everything in seconds.

## Highlights

- **Hybrid search** — ChromaDB cosine similarity fused with BM25 keyword scoring (`combined = 0.7·semantic + 0.3·keyword`), with metadata filtering.
- **NL query parser** — regex issue-key extraction + few-shot LLM intent/entity extraction, with a keyword heuristic fallback when no LLM is available.
- **5 CrewAI agents** — Retrieval, Context, Suggestion, Sprint Planner, Documentation. The deterministic engines behind them are fully unit-tested offline; CrewAI provides the live agentic path.
- **5 suggestion types** — summary rewrite (LLM), component, priority, story-point estimate, and assignee — each with a confidence score and rationale.
- **Simulation-first writes** — every change is a dry-run recorded in `pending_operations`; nothing mutates until you explicitly execute.
- **Analytics** — logs suggestions and feedback, reports acceptance rates and quality metrics.
- **Evaluation suite** — Recall@5 / Precision@5 / MRR (semantic vs hybrid) and suggestion-quality metrics, with committed result JSON.

96 tests pass; `ruff` clean. The suite runs entirely offline (deterministic stub embedder + injected stub LLMs); only the optional live smoke paths need an OpenAI key.

## Architecture

```
                 ┌──────────────┐      ┌──────────────┐
   CLI  ───────► │ JiraCopilot  │ ◄─── │  FastAPI     │
   (Typer)       │    Crew      │      │  (33 routes) │
                 └──────┬───────┘      └──────────────┘
                        │
        ┌───────────────┼───────────────────────────┐
        ▼               ▼                            ▼
  QueryParser      Agent engines               Services
  (intent +    Retrieval/Context/Suggestion   IssueService (SQLAlchemy)
   entities)   SprintPlanner/Documentation    VectorStore (Chroma + BM25)
                                              IssueWriter (simulate→execute)
                                              Analytics (suggestions/feedback)
                        │
                        ▼
              SQLite (TAWOS schema)  +  ChromaDB (embeddings)
```

Both the API and CLI call the same service layer. The agent **engines** are deterministic and return Pydantic models, so the API/CLI/eval get reliable structured output; the CrewAI agents wrap those same engines as tools for the live agentic path.

## Quickstart

```bash
cd mini-projects/08-jira-copilot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your OPENAI_API_KEY (optional for offline use)

# Build the sample DB and embed issues into ChromaDB
python run_cli.py sync

# Try it
python run_cli.py search "authentication login"
python run_cli.py suggest APACHE-5 --type priority
python run_cli.py plan-sprint APACHE
python run_cli.py release-notes 1
python run_cli.py chat "find issues about oauth"
```

Run the API:

```bash
python run_api.py            # http://127.0.0.1:8000/docs for interactive OpenAPI
```

## Prerequisites

- Python 3.11+
- An OpenAI API key for embeddings (`text-embedding-3-small`) and the agent LLM (`gpt-4o-mini`). **Optional** — without a key the system falls back to a deterministic offline embedder and the heuristic query parser, so the CLI/API/tests still work (with lower retrieval quality).

Configuration is via `.env` (see `.env.example`): `OPENAI_API_KEY`, `MODEL_NAME`, `EMBEDDING_MODEL`, `DATABASE_URL`, `CHROMADB_PATH`, `TAWOS_PROJECTS`.

## CLI commands

`sync`, `search`, `query`, `context`, `suggest`, `plan-sprint`, `velocity`, `release-notes`, `chat`, `stats`, `pending`, `execute`. Run `python run_cli.py --help` for details.

## API routers

`core` (chat/query/search/health), `issues`, `context`, `suggestions`, `sprint`, `write`, `analytics`, `docs` — 33 endpoints total. Full schema at `/docs` when the server is running.

## Using the real TAWOS dataset

`scripts/convert_tawos.py --sample` builds the synthetic dev dataset. To load real data, export the TAWOS MySQL dump's tables to a SQLite DB matching `jira_copilot/db/models.py`, point `DATABASE_URL` at it, then run `python scripts/seed_vectors.py --project <KEY>` to embed. Embedding ~20K issues costs about $0.20 with `text-embedding-3-small`.

## Evaluation

```bash
python eval/eval_retrieval.py     # Recall@5 / Precision@5 / MRR, semantic vs hybrid
python eval/eval_suggestions.py   # estimate MAE, priority agreement, component/assignee accuracy
python eval/eval_suggestions.py --judge   # also LLM-judge the summary rewrites
```

Results are written to `eval/results_*.json` (committed). On the **synthetic 16-query / 6-issue sample** both semantic and hybrid hit Recall@5 = 1.0 (the queries are easy at this scale), so hybrid shows no lift here — the gap is expected to open up on the full TAWOS set where keyword exact-matches and rare terms matter. The suggestion metrics (estimate MAE, priority agreement) are illustrative on six issues; component/assignee leave-one-out accuracy is near zero simply because six issues give too few neighbours. The point is the **harness**: trace → measure → close the gap. Note the summary LLM-judge scores the model's own rewrites and should be read with that bias in mind.

## Testing

```bash
python -m pytest -q     # 96 tests, fully offline
ruff format . && ruff check .
```

## Demo script (~2 min)

1. `python run_cli.py sync` — "Loads a TAWOS-shaped dataset and embeds every issue into ChromaDB."
2. `python run_cli.py search "authentication login"` — "Hybrid search ranks the OAuth story top, blending semantic + keyword."
3. `python run_cli.py suggest APACHE-5 --type all` — "Five suggestion types, each with a confidence score and rationale."
4. `python run_cli.py plan-sprint APACHE` — "Plans a sprint against historical velocity, prioritizing critical work."
5. API: `POST /write/update` then `GET /write/pending` then `POST /write/execute` — "Writes are simulated first; nothing changes until you confirm."
6. `python run_cli.py release-notes 1` — "Auto-generated release notes grouped by features / fixes / improvements."
7. `python eval/eval_retrieval.py` — "Everything is measured: retrieval and suggestion quality with committed results."
