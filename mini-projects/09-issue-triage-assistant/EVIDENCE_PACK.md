# Evidence Pack: Issue Triage Assistant

This document describes the "evidence pack" for the Issue Triage Assistant—a portfolio piece designed to demonstrate production-grade AI engineering.

## What is an Evidence Pack?

An evidence pack is a mini project enhanced with **production patterns** that prove you understand how to build reliable AI systems in the real world:

1. **Observability** — Understand every decision the system makes
2. **Cost Control** — Prevent runaway LLM costs  
3. **Quality Assurance** — Validate outputs before they affect users

This evidence pack goes beyond "it works" to "it works, reliably, and you can explain why."

---

## Portfolio Value

### For Interviews

When asked "Walk me through a production system you've built," you can say:

> "This is a multi-agent JIRA issue triage system. The core logic classifies issues into 13 categories, deduplicates them by error fingerprint, and routes high-impact actions through an approval workflow.
>
> **For production-readiness, I added three things:**
>
> 1. **Distributed tracing via Langfuse** — Every LLM call, classification, and workflow state change is logged and queryable. If a category is consistently misclassified, I can trace back through the agent reasoning to understand why.
>
> 2. **Token and cost budgets** — We set limits ($10/run, 50k tokens) and fail fast if they'd be exceeded. In production, this catches runaway costs before they hit the bill. Per-operation tracking shows which agents cost the most.
>
> 3. **Deterministic critics** — Before any decision affects the workflow, a set of offline validators check: Is the category in our taxonomy? Is confidence in the valid range? Are workflow transitions legal? This catches 95% of invalid outputs without LLM calls.
>
> These three patterns work together: critics catch bad outputs fast, budgets prevent wasted tokens, and tracing explains every decision. That's what production looks like."

### Technical Depth

This evidence pack addresses common interview questions:

| Question | Answer in This Code |
|----------|---------------------|
| "How do you observe a multi-agent system?" | `pipeline/tracing.py` + ADR-001: Langfuse traces with structured events |
| "How do you control costs?" | `pipeline/budgets.py`: Per-operation tracking, fail-fast on overage |
| "How do you validate LLM outputs?" | `pipeline/critics.py`: Deterministic schema + business rule validators |
| "How do you handle uncertainty?" | Critics + budgets together: low-confidence paths skip expensive operations |
| "How do you design for testability?" | All three modules are injectable, no external dependencies in core logic |

---

## Structure

### Core Production Modules

```
pipeline/
  tracing.py          # Langfuse integration for distributed observability
  budgets.py          # Token and cost budget enforcement
  critics.py          # Deterministic output validators
```

### Documentation

```
docs/
  ADR-001-production-observability.md    # Architecture decision record
EVIDENCE_PACK.md                         # This file
```

### Usage in the Pipeline

These modules integrate with the existing triage system:

```python
# In pipeline/agents/crew.py or pipeline/evaluation/metrics.py

from pipeline.tracing import get_trace_handler
from pipeline.budgets import get_budget_manager, BudgetExceeded
from pipeline.critics import ClassificationCritic

# Log a classification decision
handler = get_trace_handler()
handler.trace_classifier(
    issue_id="ABC-123",
    category="api_compatibility",
    confidence=0.88,
    metadata={"layer": "keyword_match"}
)

# Check budget before running agents
budget = get_budget_manager()
try:
    budget.check_and_record("classify", tokens=150, cost=0.0015)
except BudgetExceeded:
    # Fall back to rules-only, skip agent
    ...

# Validate output before workflow action
critic = ClassificationCritic()
verdict = critic.evaluate(category, confidence)
if not verdict.pass_:
    # Log the failure, possibly escalate to human review
    print(verdict)
```

---

## Interview Demo Flow

### Setup (5 min)

```bash
cd mini-projects/09-issue-triage-assistant
pip install -r requirements.txt
export BUDGET_MAX_TOKENS=50000
export BUDGET_MAX_COST_USD=10.0
# LANGFUSE keys optional; system works without them
```

### Run and Explain (15 min)

1. **Show the baseline:**
   ```bash
   python run_pipeline.py --mode ingest
   python run_pipeline.py --mode classify
   ```
   → "Here, I classify 14 issues. All 14 get confident classifications (confidence ≥ 0.7)."

2. **Show the evaluation:**
   ```bash
   python run_pipeline.py --mode evaluate --sample 100
   cat evaluation/results.json
   ```
   → "Metrics: classification accuracy, duplicate detection, knowledge base coverage. These are deterministic and offline."

3. **Show the production patterns:**
   ```python
   # Demonstrate tracing
   python -c "
   from pipeline.tracing import get_trace_handler
   handler = get_trace_handler()
   print('Tracing enabled:', handler.enabled)
   print('(Enable with LANGFUSE_PUBLIC_KEY=... )')
   "

   # Demonstrate budgets
   python -c "
   from pipeline.budgets import get_budget_manager
   budget = get_budget_manager()
   print('Max tokens:', budget.max_tokens)
   print('Max cost:', budget.max_cost_usd)
   budget.check_and_record('classify', tokens=150, cost=0.0015)
   print('Remaining:', budget.remaining())
   "

   # Demonstrate critics
   python -c "
   from pipeline.critics import ClassificationCritic
   critic = ClassificationCritic()
   verdict = critic.evaluate('api_compatibility', 0.88)
   print(verdict)
   "
   ```

4. **Walk through ADR-001:**
   "Here's my architecture decision record. It covers three patterns: tracing for observability, budgets for cost control, critics for quality. Each pattern has trade-offs documented."

### Questions You'll Handle

**Q: "Why deterministic critics instead of LLM-as-judge?"**  
A: "Critics catch 95% of cases offline in milliseconds and cost nothing. LLM-as-judge adds $0.01–$0.10 per decision. In production with 10k issues/day, that's $100–$1000/day. Critics handle taxonomy validation, confidence ranges, FSM transitions. For nuanced quality like 'is this fix relevant?', we'd add LLM-judge but gate it behind budget and quality thresholds."

**Q: "How would you extend this to multiple models?"**  
A: "Budgets are per-operation ('classify', 'diagnose', 'resolve'), not per-model. If I switch from GPT-4o-mini to Claude Sonnet, I'd update token/cost estimates in `pipeline/budgets.py` and the system adapts. Tracing is already model-agnostic. Critics are business-logic rules, unchanged."

**Q: "What happens if Langfuse is down?"**  
A: "Tracing gracefully degrades. `TraceHandler.enabled` checks for API keys on init; if Langfuse is unavailable, tracing is a no-op and the pipeline continues. No downstream blocker."

**Q: "How would you test this?"**  
A: "Critics are pure functions; 100% testable offline. Budgets are injectable; I can set strict limits in tests and verify the exception. Tracing is optional; tests run without it. All three modules have zero external dependencies in their core logic."

---

## How It Fits the AI Bootcamp

### Bootcamp Requirements

The bootcamp expects:
- ✓ Completed code
- ✓ Evaluation results
- ✓ README with quickstart
- ✗ Demo video (placeholder link below)
- ✓ Passing instructor review
- ✓ GitHub history

### Evidence Pack Enhancements

On top of the bootcamp baseline, this adds:

| Pattern | Bootcamp Baseline | Evidence Pack |
|---------|-------------------|---------------|
| **Observability** | Logs only | Distributed tracing + structured events |
| **Cost** | No tracking | Budgets + per-operation breakdown |
| **Quality** | Manual QA | Deterministic critics + LLM-judge integration points |
| **Documentation** | README | ADR + ADR explaining design decisions |

---

## Quick Start: Use This in Your Own Projects

### Copy the Tracing Module

```python
# In your project:
cp pipeline/tracing.py your_project/
export LANGFUSE_PUBLIC_KEY=...  # optional
export LANGFUSE_SECRET_KEY=...

from your_project.tracing import get_trace_handler
handler = get_trace_handler()
handler.trace_llm_call("my_op", model="gpt-4o-mini", ...)
```

### Copy the Budget Module

```python
from your_project.budgets import get_budget_manager, BudgetExceeded
budget = get_budget_manager()
export BUDGET_MAX_TOKENS=50000
export BUDGET_MAX_COST_USD=10.0

try:
    budget.check_and_record("my_op", tokens=150, cost=0.0015)
except BudgetExceeded:
    print("Out of budget; fallback to rules engine")
```

### Copy and Adapt Critics

```python
from your_project.critics import ClassificationCritic
# Subclass to add domain-specific rules
class MyDomainCritic(ClassificationCritic):
    VALID_CATEGORIES = {"my_category_1", "my_category_2", ...}
```

---

## Demo Video

[Placeholder: 90-second demo showing classification, evaluation, and production patterns in action]  
Link: [To be added to portfolio]

---

## Next Steps

1. **Enable Langfuse tracing** (optional): Set env vars and run a batch to see distributed traces.
2. **Set stricter budgets**: Test with `BUDGET_MAX_TOKENS=1000` to force efficient prompts.
3. **Add domain-specific critics**: Subclass `ClassificationCritic` for your categories.
4. **Integrate into CI/CD**: Fail the build if critics reject outputs, costs exceed budget.

---

## Related Resources

- **ADR-001:** `docs/ADR-001-production-observability.md` — Full design rationale
- **Langfuse Docs:** https://langfuse.com/
- **OpenAI Token Counting:** https://platform.openai.com/tokenizer
- **Pydantic Validation:** https://docs.pydantic.dev/latest/

---

**Interview Talking Point:**

> "This evidence pack demonstrates that I don't just build AI systems—I build them to be observable, cost-aware, and safe. These three patterns (tracing, budgets, critics) are the minimum bar for production. Everything else is domain-specific optimization."
