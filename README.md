# ai-mini-projects

Standalone mini-projects extracted from ai-bootcamp. Each project lives on its own branch.

## Branch layout

- **main** — Shared scaffolding only. `.cursor/commands/`, `.cursor/rules/`, config. No mini-projects.
- **01-synthetic-data-pipeline** — DIY Repair synthetic data pipeline
- **02-resume-job-pipeline** — Resume-job synthetic data pipeline with API
- **03-rag-evaluation-pipeline** — RAG evaluation pipeline

Additional branches: 04–09 (planning only).

## Usage

```bash
# Checkout a project to work on it
git checkout 02-resume-job-pipeline

# Install and run (example for 02-resume-job-pipeline)
cd mini-projects/02-resume-job-pipeline
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys
python run_pipeline.py --mode all
```

## Source control

Only `.cursor/commands/` and `.cursor/rules/` are tracked. `.cursor/docs/`, `.cursor/lessons/`, `.cursor/plans/`, and `.cursor/preflight.json` are gitignored.
