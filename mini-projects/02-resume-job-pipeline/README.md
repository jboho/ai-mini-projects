# Resume-Job Synthetic Data Pipeline

Generates synthetic resume-job pairs, validates them, labels them with six failure metrics, runs an LLM correction loop, produces aggregate analysis, and exposes results via a FastAPI service.

## Setup

```bash
cp .env.example .env   # add your OPENAI_API_KEY
pip install -r requirements.txt
```

## Run

```bash
# Full pipeline end-to-end
python run_pipeline.py --mode all

# Individual stages (each reads the previous stage's output from data/)
python run_pipeline.py --mode generate
python run_pipeline.py --mode validate
python run_pipeline.py --mode correct
python run_pipeline.py --mode label
python run_pipeline.py --mode analyze
```

## API

```bash
uvicorn api.app:app --reload
```

- `GET  /health`
- `POST /review-resume`  — body: `{resume: ..., job: ..., enable_judge: false}`
- `GET  /analysis/failure-rates`  — requires a prior pipeline run

## Tests

```bash
pytest tests/ -v
```

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | required | OpenAI API key |
| `MODEL_NAME` | `gpt-4o-mini` | Model for generation and judge |
| `BATCH_SIZE` | `5` | Number of jobs to generate |
| `RESUMES_PER_JOB` | `3` | Resumes generated per job |
| `MAX_CORRECTION_RETRIES` | `3` | Correction loop retries |
| `ENABLE_JUDGE` | `false` | Enable LLM-as-Judge evaluation |

## Architecture

```
generator → validator → corrector → labeler → analyzer → visualizer
                                                    ↓
                                              FastAPI (routes.py)
```

- **Instructor** enforces Pydantic schemas at generation time via structured outputs
- **Validator** catches cross-field logical violations (future dates, impossible timelines)
- **Correction loop** feeds structured error context back to the LLM (max 3 retries)
- **Labeler** applies 6 deterministic rule-based failure metrics
- **LLM-as-Judge** (optional) provides qualitative hallucination + quality scores
- **Visualizer** produces 6 charts to `visuals/`

## Failure Metrics

| Metric | Rule |
|---|---|
| `skills_overlap` | Jaccard similarity on normalized skill sets |
| `experience_mismatch` | Resume years < 50% of required |
| `seniority_mismatch` | Level difference > 1 (Entry=0 … Executive=4) |
| `missing_core_skills` | Any of top-3 required skills absent |
| `hallucinated_skills` | Entry-level + 10+ Expert claims, or 30+ total skills |
| `awkward_language` | 3+ buzzword regex matches in summary/achievements |
