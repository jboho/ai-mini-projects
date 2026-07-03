# 06 — Digital Clone (CrewAI Multi-Agent)

A 5-agent system that learns a person's email writing style, answers questions
from a RAG knowledge base, evaluates its own responses, and falls back to a
calendar booking when confidence is low — orchestrated with CrewAI.

## Quickstart

```bash
cd mini-projects/06-digital-clone
pip install -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY (CrewAI uses gpt-4o-mini)

python run_clone.py --mode learn  --employee vince.kaminski   # build profile + RAG index
python run_clone.py --mode query  --employee vince.kaminski --question "What is gradient descent?"
python run_clone.py --mode demo   --employee vince.kaminski
python run_clone.py --mode test-agents                        # offline smoke test
```

Embeddings, scoring, and feature extraction are **local**; only the RAG draft and
style rewrite call the LLM.

## Architecture

Two layers keep the computational backbone testable independently of the agents:

- **`core/`** — pure, LLM-free: email parsing, 11+ style features, chunking,
  FAISS store, evaluation scoring math, calendar. (23 unit tests, no mocking.)
- **`agents/`** — CrewAI agents wrapping `core/` tools.

```
query -> retrieve (FAISS) -> RAGAgent draft (cited) -> StyleAgent rewrite
      -> EvaluatorAgent score -> deliver (>= 0.75) | FallbackAgent (calendar)
```

| Agent | Role | LLM? |
|-------|------|------|
| RAGAgent | retrieve + draft grounded, cited answer | yes |
| ChatStyleAgent | rewrite in the person's email voice | yes |
| EvaluatorAgent | style + groundedness + confidence -> decision | no (core math) |
| FallbackAgent | low-confidence calendar booking message | no (core) |
| PlannerAgent | orchestrate the pipeline | — |

## How it scores

```
final = 0.4*style + 0.4*groundedness + 0.2*confidence      # weights configurable
```
- **style** — cosine between the response's style vector and the learned profile.
- **groundedness** — fraction of response content found in retrieved chunks.
- **confidence** — average retrieval relevance minus a hedging-phrase penalty.

`final >= 0.75` delivers; otherwise the FallbackAgent returns a calendar link and
weekday slots.

## Style learning

`style_features.py` extracts 11+ interpretable features (message length, greeting
/sign-off distributions, punctuation, capitalization, question frequency, vocab
richness, common phrases, reasoning connectors, sentiment, formality, technical
usage), packs them into a fixed-length style vector, and refines it with an EMA
(`updated = (1-alpha)*current + alpha*new`) for incremental learning.

## Datasets

- **Style**: Enron sent mail (`enronarchive/mail` on HuggingFace), filtered by
  employee + sent folder, cached to `data/emails/`.
- **Knowledge**: `open-phi/textbooks` (computer-science field), chunked to ~900
  KnowledgeChunks. Both downloaded on `--mode learn`.

## Tests

```bash
pytest          # 25 tests: models, email parsing, style math, chunker, store,
                # scoring, calendar, fallback, and offline orchestration
ruff check .
```

The live 5-agent pipeline was validated end-to-end with gpt-4o-mini: it drafts a
cited answer, rewrites it in the learned voice, scores it, and delivers or falls
back accordingly.
