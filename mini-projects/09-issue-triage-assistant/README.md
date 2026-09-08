# AI-Powered Issue Triage Assistant

A multi-agent system that triages Apache JIRA issues end-to-end: it classifies them
into 13 engineering categories, deduplicates recurring failures by error fingerprint,
diagnoses root causes, suggests resolutions, routes high-impact actions through an
approval workflow, and fans out notifications -- all surfaced in a Streamlit dashboard.

The pipeline is built in two layers throughout:

- **Pure, deterministic logic** (classification rules, fingerprinting, the approval
  state machine, evaluation metrics) -- fully unit-tested offline.
- **An injectable LLM callable** for the parts that benefit from generation (root-cause
  diagnosis, resolution drafting, classification fallback, LLM-as-judge). Tests stub it;
  the CLI uses a live model. Swapping providers touches only `pipeline/client.py`.

## Architecture

```
CSV / synthetic seed
        │
   ingest (chunked, project-filtered)  ──►  SQLite (10 tables, SQLAlchemy 2.0)
        │
   ┌────┴───────────────── core services ──────────────────┐
   │ classifier (layered)   fingerprinter (dedup)           │
   │ text_analysis          knowledge_base                  │
   │ resolver               workflow (approval FSM)         │
   │ notifier (simulation)                                  │
   └────┬───────────────────────────────────────────────────┘
        │
   CrewAI agents: Issue Monitor → Text Analyzer → Root Cause
                  → Resolution Advisor → Reporter
        │
   evaluation (metrics + LLM-as-judge)      Streamlit dashboard (Home + 9 pages)
```

### Layered classification

Each issue passes through ordered layers; the first confident match wins:

1. Keyword / regex match (0.90–0.95)
2. Component match (0.85)
3. Composite-pattern match (0.70)
4. LLM fallback (0.60, only when a model is configured)
5. `other` (0.30)

### Deduplication

Volatile tokens (timestamps, UUIDs, hex, line numbers) are normalized out of the error
text, then SHA-256 hashed. Issues that differ only in such noise collapse to the same
signature, so recurring failures are detected and counted.

### Approval workflow

Resolution actions are scored by impact (LOW / MEDIUM / HIGH). LOW actions auto-approve;
higher-impact actions move through a finite state machine
(`PENDING → APPROVED → EXECUTING → COMPLETED`, or `→ REJECTED`). Invalid transitions raise.

### Notifications

Multi-channel (Slack / email / PagerDuty) with alert-rule matching (severity threshold,
project / category / pattern filters) and per-rule cooldowns. Runs in **simulation mode**
by default: each channel builds its real payload and returns a `simulated` result instead
of sending, so the full path is exercised without credentials.

## Setup

```bash
cd mini-projects/09-issue-triage-assistant
pip install -r requirements.txt
cp .env.example .env        # then add your key
```

`.env`:

```
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini
OTEL_SDK_DISABLED=true
```

The CLI runs fully offline without a key (the LLM callable is simply `None`); set the key
to enable live classification fallback, agent runs, and the LLM-as-judge.

## Usage

```bash
python run_pipeline.py --mode ingest                 # load CSVs from ./data, or seed a synthetic sample
python run_pipeline.py --mode classify               # classify every issue (layered + optional LLM)
python run_pipeline.py --mode triage --issue SPARK-1001   # full triage for one issue
python run_pipeline.py --mode triage                 # batch triage all issues
python run_pipeline.py --mode monitor --project SPARK     # scan active issues + simulated alerts
python run_pipeline.py --mode report --type daily    # build + persist a triage report
python run_pipeline.py --mode evaluate --sample 100  # compute metrics → evaluation/results.json

streamlit run dashboard/app.py                       # Home + 9 pages, wired to SQLite
```

Place real exports as `data/issues.csv`, `data/comments.csv`, `data/changelog.csv`,
`data/issuelinks.csv` (tolerant column aliasing handles common JIRA export shapes). With
no CSVs present, ingest seeds a 14-issue synthetic sample spanning all 10 target projects
and 13 categories, including a true-duplicate OOM triplet and resolved issues with fixes.

## Evaluation

`--mode evaluate` writes `evaluation/results.json`. Metrics are deterministic and offline;
the LLM-as-judge adds root-cause quality scores when a model is configured.

| Metric | Meaning |
|--------|---------|
| `classification_accuracy.accuracy` | Confident-classification rate (confidence ≥ 0.7). No human labels exist, so this measures decisiveness, not correctness. |
| `classification_accuracy.component_agreement` | Secondary check vs a weak unique-component oracle — deliberately kept separate because component metadata alone is a noisy predictor. |
| `resolution_relevance.mean_relevance` | Mean Jaccard overlap between generated resolution steps and the actual fix comment, over resolved issues. |
| `knowledge_base_coverage` | Share of the 13 categories with KB entries. |
| `duplicate_detection_rate.rate` | Share of known `duplicates` links whose fingerprints collide as intended. |

On the synthetic sample: confident-classification rate **1.0**, duplicate-detection rate
**1.0**, with component agreement reported transparently at **0.07** (the oracle, not the
classifier, is the limitation). LLM-judge root-cause scores average ~3/5.

## Testing

```bash
python -m pytest -q        # 88 tests, fully offline
ruff format . && ruff check .
```

All LLM calls are stubbed in tests; each phase was additionally smoke-tested against a live
model. Dashboard pages are verified to render exception-free headless via
`streamlit.testing`.

## Project structure

```
pipeline/
  config.py            # settings, 13-category taxonomy, impact rules, templates
  client.py            # injectable LLM callable (OpenAI-compatible)
  db/                  # SQLAlchemy 2.0 models, engine, synthetic seeder
  ingest/              # chunked CSV loader + enricher
  services/            # classifier, fingerprinter, text_analysis, knowledge_base,
                       #   resolver, workflow (FSM), notifier
  agents/              # 5 CrewAI agents + TriageCrew orchestrator + tools
  evaluation/          # metrics + LLM-as-judge
dashboard/             # Streamlit Home + 9 pages
tests/                 # offline unit tests
run_pipeline.py        # CLI: ingest | classify | triage | monitor | report | evaluate
```

## Notes

- SQLite + `create_all` for dev simplicity (no Alembic migrations).
- OpenAI `gpt-4o-mini` is used via the OpenAI-compatible SDK; the PLAN's Groq target swaps
  in by changing only `pipeline/client.py`.
- The database, vector caches, generated visuals, and `.env` are gitignored;
  `evaluation/results.json` is committed as a demo artifact.
