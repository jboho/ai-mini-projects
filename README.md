# ai-mini-projects

Standalone mini-projects. **`main` carries the shared scaffolding plus integrated code under `mini-projects/` for projects 01–04.** Per-project branches (below) are where isolated development happens.

**All project branches are works in progress.** Expect incomplete features, shifting APIs, and plan/docs that may run ahead of implementation. Prefer `main` for a single checkout that includes the merged mini-projects; use a branch when you want to work on one project’s line without mixing others.

## Branch layout

| Branch | Focus |
|--------|--------|
| **main** | Shared `.cursor/` commands and rules, repo config, and **merged** `mini-projects/01`–`04` (integration branch). |
| **01-synthetic-data-pipeline** | DIY Repair synthetic data pipeline (WIP) |
| **02-resume-job-pipeline** | Resume–job synthetic data pipeline and API (WIP) |
| **03-rag-evaluation-pipeline** | RAG evaluation pipeline (WIP) |
| **04-rag-pdf-qasystem** | RAG over PDFs / Q&A system (WIP) |
| **05-dating-compatibility** | Dating compatibility (WIP) |
| **06-digital-clone** | Digital clone (WIP) |
| **07-customer-feedback-agents** | Customer feedback agents (WIP) |
| **08-jira-copilot** | Jira copilot (WIP) |
| **09-issue-triage-assistant** | Issue triage assistant (WIP) |

Branches **05–09** are early or planning-stage; treat them as especially fluid.

## Usage

```bash
# Work from integrated tree on main
git checkout main
cd mini-projects/02-resume-job-pipeline
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys
python run_pipeline.py --mode all
```

Or focus on one project line:

```bash
git checkout 02-resume-job-pipeline
cd mini-projects/02-resume-job-pipeline
# same install/run steps as above
```

## Source control

Only `.cursor/commands/` and `.cursor/rules/` are tracked under `.cursor/`. `.cursor/docs/`, `.cursor/lessons/`, `.cursor/plans/`, and `.cursor/preflight.json` are gitignored.
