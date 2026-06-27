# Evidence Pack: RAG PDF QA System

Production patterns for retrieval reliability, latency SLAs, and cost control.

## What's Added

### 1. Distributed Tracing (`rag/tracing.py`)
- Logs retrieval latency per query
- Tracks embedding model performance
- Traces LLM generation with context/response lengths

**Interview angle:** "I can see which queries hit the embedding bottleneck, which retriever is slowest, and which prompts generate the longest responses. This drives optimization priorities."

### 2. Latency Budgets (`rag/budgets.py`)
- SLA enforcement: 200ms target for retrieval (configurable)
- Per-query cost tracking (embeddings ~$0.0001, generation ~$0.001)
- Query count limits

**Interview angle:** "Retrieval SLA matters. I track p50/p95/p99 latency and alert on violations. At scale, 100ms savings per query = 27 hours saved per million queries."

### 3. Response Critics (`rag/critics.py`)
- **RetrievalCritic:** Validates precision@1, chunk count, SLA compliance
- **ResponseCritic:** Validates response length, citation of sources

**Interview angle:** "Before returning a response, critics check: Did retrieval find anything? Is the top result relevant? Did generation cite sources? This is the last line of defense against hallucinations."

## Usage

### Enable Tracing
```bash
export LANGFUSE_PUBLIC_KEY=...
python app.py  # Traces all queries
```

### Set Latency SLA
```bash
export BUDGET_MAX_RETRIEVAL_LATENCY_MS=150  # 150ms target
python app.py  # Alerts on violations
```

### Enforce Budgets
```bash
export BUDGET_MAX_QUERIES=10000
export BUDGET_MAX_COST_USD=50
python experiments/run_experiment.py
```

## Interview Questions

**Q: "How do you know if your RAG system is slow?"**  
A: Tracing records latency per component. If retrieval p50 > 200ms, I switch to a faster embedder (e.g., all-MiniLM vs. all-mpnet). If generation is slow, I check context length or switch models.

**Q: "What's your SLA for retrieval?"**  
A: 200ms for latency, precision@1 > 0.8. If either is violated, I log it and can trigger fallback (e.g., BM25 instead of dense retrieval).

**Q: "How do you prevent hallucinations?"**  
A: Three layers: (1) RetrievalCritic checks if we found anything relevant, (2) ResponseCritic checks if response length is reasonable, (3) Prompt includes "[STOP if no relevant sources found]" instruction.

**Q: "How does this scale to 1M queries/day?"**  
A: Query cost is ~$0.001 (embedding + generation). 1M queries = ~$1000/day. With budgets, I catch cost overruns immediately. Tracing identifies which queries are anomalies (slow or hallucinating).

## Comparison to Bootcamp Baseline

| Baseline | Evidence Pack |
|----------|---------------|
| Generate answer from retrieval | + Trace latency per component |
| One result | + SLA enforcement on retrieval |
| Hope it's good | + Critics validate before return |
