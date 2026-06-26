# AI Mini-Projects

A series of applied AI engineering projects, each demonstrating a different technique or system pattern. Projects progress from structured data generation pipelines through RAG evaluation, embedding fine-tuning, and multi-agent systems.

## Projects

| # | Project | What it does | PR |
|---|---------|--------------|-----|
| 01 | [Synthetic Data Pipeline](mini-projects/01-synthetic-data-pipeline) | Generate-evaluate-correct loop for synthetic Q&A; 93% failure rate reduction | [PR #1](../../pull/1) |
| 02 | [Resume-Job Pipeline](mini-projects/02-resume-job-pipeline) | Schema-enforced resume/job pair generation with 6 failure metrics and LLM judge | [PR #2](../../pull/2) |
| 03 | [RAG Evaluation Pipeline](mini-projects/03-rag-evaluation-pipeline) | Grid search over 24 RAG configurations; best MRR 0.917 with semantic chunking + BM25 | [PR #3](../../pull/3) |
| 04 | [RAG PDF QA System](mini-projects/04-rag-pdf-qasystem) | Production RAG on Vectara benchmark (1,000 papers, 3,045 QA pairs); MRR 0.769 | [PR #4](../../pull/4) |
| 05 | [Dating Compatibility](mini-projects/05-dating-compatibility) | Embedding fine-tuning pipeline; FPR 0.595→0.010 (-98%), Cohen's d 1.79→11.99 | [PR #5](../../pull/5) |
| 06 | [Digital Clone](mini-projects/06-digital-clone) | 5-agent CrewAI system replicating email writing style with RAG and calendar fallback | [PR #6](../../pull/6) |
| 07 | [Customer Feedback Agents](mini-projects/07-customer-feedback-agents) | 4-agent pipeline for gap analysis from 3,000+ reviews across Amazon, Yelp, App Store | [PR #7](../../pull/7) |
| 08 | [Jira Copilot](mini-projects/08-jira-copilot) | Multi-agent Jira assistant; hybrid search, 33 API endpoints, 96 tests passing | [PR #8](../../pull/8) |
| 09 | [Issue Triage Assistant](mini-projects/09-issue-triage-assistant) | Automated bug triage with layered classification, FSM approval workflow (WIP) | [PR #9](../../pull/9) |

## Recurring Patterns

Patterns that emerged and were reused across projects:

**Data & Generation**
- Instructor + Pydantic for guaranteed schema-compliant LLM outputs on every call
- Generate-evaluate-correct loops: LLM-as-Judge failure signal drives targeted prompt corrections
- Independent failure mode scoring (6 specific types) over aggregate quality labels

**Retrieval**
- Hybrid retrieval (BM25 + vector) consistently outperforms either alone across Projects 03 and 04
- Chunking strategy matters more than embedding model size for retrieval quality
- BM25 is a strong baseline on terminology-heavy text — don't assume embeddings are always better

**Agents & Systems**
- CrewAI agents as thin wrappers over deterministic service functions — logic stays in services for testability
- Two-layer architecture (`core/` pure computation, `agents/` LLM calls) enables offline unit tests without mocking
- Simulation-first writes (dry-run → audit trail → explicit execute) for any system that modifies shared state

**Evaluation**
- Multi-metric statistical evaluation (Cohen's d, FPR, cluster purity) over accuracy alone
- Per-config QA ground truth for fair RAG evaluation — shared datasets across chunking configs introduce bias
- LLM-as-judge for quality, but with awareness of self-evaluation bias; third-party validation where possible
- Embedding and result caching by content hash to enable rapid iteration without re-running expensive steps

## Structure

```
mini-projects/
├── _shared/                    # Shared dashboard utilities
├── 01-synthetic-data-pipeline/
├── 02-resume-job-pipeline/
├── 03-rag-evaluation-pipeline/
├── 04-rag-pdf-qasystem/
├── 05-dating-compatibility/
├── 06-digital-clone/
├── 07-customer-feedback-agents/
├── 08-jira-copilot/
└── 09-issue-triage-assistant/
```

Each project is self-contained with its own `requirements.txt`, `README.md`, and test suite.

## Quick Start

Each project directory contains a `README.md` with setup and run instructions. Most projects require `OPENAI_API_KEY` set in a `.env` file copied from `.env.example`. All test suites run offline with stub LLMs — no API key needed to run tests.
