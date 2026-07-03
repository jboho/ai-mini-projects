# 07 — Customer Feedback Multi-Agent System

Ingests product reviews from three sources, runs four analysis agents
(sentiment → themes → roadmap mapping → gap analysis), and surfaces the
highest-priority **unaddressed** customer needs — with Markdown/HTML reports and
a 4-tab Streamlit dashboard.

## Quickstart

```bash
cd mini-projects/07-customer-feedback-agents
pip install -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY (agents + embeddings)

python run_pipeline.py --mode full --sample-size 300     # full analysis
python run_pipeline.py --mode full --crew                # CrewAI orchestration
python run_dashboard.py                                   # 4-tab dashboard
```

`--mode ingest-only` and `--mode sentiment-only` stop early; `--source` limits to
one of amazon/yelp/app_store; `-r` swaps the roadmap; `--no-visuals` skips reports.

## Pipeline

```
3 loaders (Amazon/Yelp/AppStore) -> SentimentAgent -> ThemeAgent
   -> MappingAgent (themes x roadmap, cosine) -> GapAgent (priority + recs)
   -> reports + dashboard
```

| Component | What it does | LLM? |
|-----------|--------------|------|
| loaders | normalize each source into `Feedback` (BaseLoader ABC) | no |
| SentimentAgent | sentiment + **separate** pain intensity (structured) | yes |
| ThemeAgent | cluster into 5-10 named themes | yes |
| MappingAgent | embed themes + roadmap, cosine align (threshold 0.75) | embeddings + reason |
| GapAgent | weighted priority score + recommendations for gaps | recs only |
| evaluation | sentiment accuracy vs stars, pain calibration | no |

## Priority formula

```
priority = 0.35*pain + 0.25*frequency + 0.25*coverage_gap + 0.15*neg_sentiment
```

Themes with high pain/frequency/negativity that the roadmap does **not** cover
score highest — those are the gaps. Weights live in `config.yaml`.

## Dashboard (4 tabs)

- **Overview** — KPI cards, sentiment pie, pain histogram
- **Themes** — frequency bar + expandable theme cards
- **Gaps** — priority scatter (feedback × pain, size = priority) + gap cards
- **Explorer** — filterable feedback table (source / sentiment)

## Datasets

Amazon Reviews 2023, Yelp Review Full, and App Reviews — all streamed from
HuggingFace on `--mode full` and embedded via `text-embedding-3-small`.

## Tests

```bash
pytest          # 21 offline tests: models, loaders, mapping, gap formula,
                # evaluation, sentiment (stub client)
ruff check .
```

The LLM-dependent agents are tested with stubs/known-answer math; the full
pipeline (datasets + API) is run with `--mode full`.
