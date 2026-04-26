---
name: adapt-domain
description: >-
  Adapt an existing mini-project to a new domain while preserving the
  original tech stack, techniques, pipeline structure, and success criteria.
  Collect four required inputs before proceeding.
---

# Domain Adaptation

Adapt a mini-project to a new domain. Collect all required inputs before generating any output.

## Required Inputs

Prompt for all four; ask only for missing ones if some are pre-supplied in the invocation:

1. **Source project** — path or number (e.g. `03` or `03-rag-evaluation-pipeline`)
2. **Original topic** — what domain does it currently address?
3. **Target domain** — what domain should it be adapted to?
4. **Success criteria** — paste from the original project's README or PLAN.md

## Phase 0: Source Reconnaissance

Before generating anything, read the source project:
- `README.md` or `PLAN.md` — description, tech stack, success criteria
- `pipeline/` — module structure and patterns
- `data/` — sample data format and schema
- Entry point (`run_pipeline.py`) — CLI args and flow

Output a source analysis:
```
## Source Analysis

Project: 03-rag-evaluation-pipeline
Current domain: DIY home repair customer support
Tech stack: [list]

Domain-specific elements (will change):
- Prompt text referencing "home repair" / "contractor" / "DIY"
- Synthetic question topics
- Seed data examples

Domain-neutral elements (will stay unchanged):
- Pipeline structure and module layout
- Libraries (OpenAI, ChromaDB, ruff, pytest)
- Eval metrics (MRR, Recall@k, Faithfulness)
- Logging patterns
- Test count and test patterns
```

## Phase 1: Feasibility Check

For each success criterion, evaluate whether it is achievable in the target domain. Flag any that cannot be fulfilled and propose an alternative criterion or domain adjustment.

## Phase 2: Adaptation

Generate adapted content for:

1. **README/spec** — updated domain description, same structure, identical success criteria
2. **Synthetic data / seed prompts** — domain-appropriate examples, same count and variety (factoid, multi-hop, distractor, edge-case)
3. **System/user prompts** — replace domain references, preserve technique and structure
4. **Variable names and comments** — update domain-specific identifiers (e.g., `diy_question` → `ecommerce_question`)

**Hard constraint:** Do not change libraries, pipeline structure, eval metrics, logging patterns, test structure, or test count.

## Phase 3: Verification

For each success criterion, mark:
- ✅ preserved — achievable in target domain without modification
- ⚠️ modified — state what changed and why

## Output Format

Deliver as an edit plan or inline diffs, one file at a time. For each file: state what changed (domain text, prompt copy, example data) vs. what stayed the same (structure, tech, metrics).
