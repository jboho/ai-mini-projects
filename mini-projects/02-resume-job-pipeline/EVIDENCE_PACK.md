# Evidence Pack: Resume-Job Synthetic Data Pipeline

This evidence pack demonstrates production-grade patterns for data quality, API safety, and cost management.

## What's Added

### 1. Distributed Tracing (`pipeline/tracing.py`)
- Logs every pair generation, judgment, and correction event
- Tracks failure modes and costs per operation
- Optional Langfuse integration for observability

**Interview angle:** "I can trace where failures come from. If 40% of 'Excellent' matches show 'hallucinated_skills', I know the generation prompt needs fixing."

### 2. Budget Management (`pipeline/budgets.py`)
- Per-operation cost tracking (generation ≈$0.002, judgment ≈$0.005, correction ≈$0.003)
- Pair count limits + cost limits
- Early warnings at 80% utilization

**Interview angle:** "In production, I set budgets to prevent surprise bills. A 10k-pair run costs ~$50-$100 depending on correction rate. The system fails fast if limits would be exceeded."

### 3. Quality Critics (`pipeline/critics.py`)
- **PairCritic:** Validates resume/job structure before judgment (catches hallucinations)
- **FailureModeCritic:** Validates failure mode labels
- **FitLevelCritic:** Validates Excellent/Good/Poor classifications

**Interview angle:** "Critics catch format issues offline before expensive LLM calls. If a resume looks like AI-generated fluff, we reject it before wasting tokens on judgment."

## Usage

### Enable Tracing
```bash
export LANGFUSE_PUBLIC_KEY=...
export LANGFUSE_SECRET_KEY=...
python pipeline/analyzer.py  # Now traces to Langfuse
```

### Set Budgets
```bash
export BUDGET_MAX_PAIRS=100        # 100 pairs max
export BUDGET_MAX_JUDGES=500       # 500 judgments max
export BUDGET_MAX_COST_USD=50      # $50 max spend
python run_pipeline.py --mode all
```

### Use Critics
```python
from pipeline.critics import PairCritic, FailureModeCritic

pair_critic = PairCritic()
verdict = pair_critic.evaluate_pair(resume, job)
if not verdict.pass_:
    print(f"Rejected: {verdict.reason}")
    # Skip expensive judgment call
```

## Interview Questions This Answers

**Q: "How do you avoid hallucinations in synthetic data?"**  
A: Critics validate resume/job pairs before judgment. If a resume looks AI-generated, we reject it. This catches the hallucination early, before wasting tokens on a judgment.

**Q: "How do you manage LLM costs in production?"**  
A: Budgets track per-operation costs. We set limits (50 pairs/run = $0.10) and fail fast if limits would be crossed. Per-operation breakdown shows which steps cost the most.

**Q: "How would you extend this to 10M pairs?"**  
A: Batch in 1k-pair chunks with budgets. Tracing identifies which failure modes are systematic, so we can fix the generation prompt once instead of judgment-correcting everything.

**Q: "How do you know if your data is good?"**  
A: Three levels: critics (format/structure), judgment (LLM-as-judge on failures), and production metrics (do downstream models trained on this data actually work?).

## Patterns Reusable in Other Projects

```python
# Cost tracking
budget = get_budget_manager()
budget.record_judgment(cost=0.005, failures=2)
print(budget.summary())

# Tracing
handler = get_trace_handler()
handler.trace_judgment("pair_123", failures=["hallucinated_skills"])
handler.flush()

# Early validation
critic = PairCritic()
verdict = critic.evaluate_pair(resume, job)
if not verdict.pass_:
    skip_expensive_step()
```

## Comparison to Bootcamp Baseline

| Baseline | Evidence Pack |
|----------|---------------|
| Generate pairs, judge, report | + Trace every decision |
| One cost at end | + Budget per operation, fail-fast |
| Manual validation | + Critics catch issues offline |

This adds **observability** (where do failures come from?) and **safety** (stop expensive operations if likely to fail).
