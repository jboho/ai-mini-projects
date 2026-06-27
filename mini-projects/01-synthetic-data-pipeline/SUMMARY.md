# Mini Project 1: DIY Repair Synthetic Data Pipeline — Project Summary

## Goal

Build an automated pipeline that generates high-quality synthetic Q&A data for a Home DIY Repair assistant. The pipeline must:

1. Generate structured repair guidance across 5 repair categories
2. Validate every item against a Pydantic schema
3. Detect quality failures using an LLM-as-Judge scoring 6 independent failure modes
4. Analyze failure patterns to identify what's going wrong and where
5. Apply data-driven prompt corrections
6. Demonstrate measurable improvement (>80% reduction in failure rate)

The core challenge: close the loop from generation to evaluation to correction, and prove the corrections work with real numbers.

---

## Architecture

```
[Phase 1] Generation → 5 prompt templates (one per repair category) → Instructor + LLM → Structured Q&A items
    ↓
[Phase 2] Structural Validation → Pydantic schema checks → Filter malformed items
    ↓
[Phase 3] LLM-as-Judge → Independent evaluation of 6 failure modes per item (temp=0)
    ↓
[Phase 4] Failure Analysis → Aggregate rates, co-occurrence heatmap, category breakdown
    ↓
[Phase 5] Prompt Correction → Targeted improvements → Re-run pipeline → Compare before/after
```

---

## Step-by-Step Build Process

### Step 1: Pydantic Models (`pipeline/models.py`)

Defined the data contracts first:

- **DIYRepairItem** — 7 required fields (`question`, `answer`, `equipment_problem`, `tools_required`, `steps`, `safety_info`, `tips`) with validators: steps >= 3, tools >= 1, tips >= 1, safety_info non-empty
- **JudgeResult** — 6 binary int fields (0=pass, 1=fail) with derived `overall_failure` property
- **GenerationMetadata** — tracks which template, validation status, timestamps
- **PipelineRecord** — combines item + metadata + judge result into one serializable unit

Verified: all validators reject bad input correctly (too few steps, empty safety_info, etc.)

### Step 2: Generator (`pipeline/generator.py`)

Built 5 category-specific prompt templates, each with a distinct expert persona:

| Category | Persona |
|----------|---------|
| Appliance | 20-year appliance repair technician |
| Plumbing | Licensed residential plumber |
| Electrical | Certified electrician teaching safe homeowner work |
| HVAC | HVAC maintenance specialist |
| General | Experienced general contractor |

Each template uses Instructor to force the LLM response into the `DIYRepairItem` Pydantic model. Random category selection per item ensures all 5 categories get covered across 50+ items. Retry logic with exponential backoff handles API errors without crashing.

Smoke tested: generated 2 items, verified all 7 fields populated, steps/tools/tips present.

### Step 3: Validator (`pipeline/validator.py`)

Takes raw generation results and produces `PipelineRecord` objects. Re-validates each item through Pydantic as a safety net. Logs field-level errors for any failures (field name + error message). Items that failed generation entirely are recorded with their error context.

Verified: correctly passes valid items, correctly rejects and logs failed items.

### Step 4: LLM-as-Judge (`pipeline/judge.py`)

Built the judge with a detailed system prompt containing:
- Definitions for all 6 failure modes
- Concrete PASS and FAIL examples for each mode
- Instructions to score each mode independently (binary 0/1)

Key design decisions:
- **Temperature = 0** for deterministic, reproducible evaluations
- **Instructor** returns structured `JudgeResult` (no string parsing needed)
- Rate-limited with delay between calls

Smoke tested: fed a deliberately terse item, judge correctly flagged `incomplete_answer` and passed everything else.

### Step 5: Analyzer (`pipeline/analyzer.py`)

Built the diagnostic toolkit:
- **Per-mode failure rates** — which modes fail most
- **Overall failure rate** with 95% confidence interval
- **Co-occurrence matrix** — which failure modes appear together (heatmap)
- **Failure by category** — which prompt templates produce the most failures (stacked bar chart)
- **Shannon entropy** — measures how evenly the 5 categories are distributed
- **Worst items** — items with 3+ simultaneous failures (diagnostic targets)
- **Before/after comparison chart** — grouped bars for baseline vs corrected

All visualizations include titles, labeled axes, value annotations, and appropriate color scales.

### Step 6: Corrector (`pipeline/corrector.py`)

Wrote 6 targeted prompt corrections, one per failure mode. Each correction is documented with:
- What was changed
- Which failure mode it targets
- Which templates it affects
- Why (linked to baseline data)

The corrections are additive — a quality requirements suffix appended to each baseline prompt rather than rewriting the originals. This keeps the changes traceable.

### Step 7: CLI Entrypoint (`run_pipeline.py`)

Three modes:
- `--mode baseline` — runs phases 1-4, saves `data/baseline.jsonl` + summary + charts
- `--mode corrected` — runs phases 1-3 with improved prompts, saves `data/corrected.jsonl` + summary + charts
- `--mode compare` — loads both datasets, prints side-by-side comparison table, saves `comparison.json` + before/after chart

---

## Baseline Run Results

| Metric | Value |
|--------|-------|
| Items generated | 50 |
| Schema validation pass rate | 100% (50/50) |
| Categories represented | All 5 (hvac: 16, plumbing: 10, general: 9, electrical: 8, appliance: 7) |
| Shannon entropy | 2.26 (max possible: 2.32) |
| **Overall failure rate** | **30.0%** (95% CI: 17.3% – 42.7%) |

### Per-mode failure rates (baseline)

| Failure Mode | Rate |
|-------------|------|
| poor_quality_tips | 18% |
| overcomplicated_solution | 16% |
| incomplete_answer | 6% |
| safety_violations | 0% |
| unrealistic_tools | 0% |
| missing_context | 0% |

### Diagnosis from baseline

- **Dominant failure mode**: `poor_quality_tips` (18%) — the generator produced vague platitudes like "be careful" and "take your time" instead of actionable advice
- **Second highest**: `overcomplicated_solution` (16%) — the generator recommended calling professionals for straightforward DIY tasks
- **Third**: `incomplete_answer` (6%) — some answers lacked enough steps to actually complete the repair
- **Worst item**: qa_0019 (HVAC category) with 3 simultaneous failures
- Three modes had 0% failure: `safety_violations`, `unrealistic_tools`, `missing_context` — the baseline prompts already handled these adequately

---

## Prompt Corrections Applied

Based on the baseline failure analysis, 6 targeted corrections were added to all prompt templates:

| # | Correction | Target Mode | Rationale |
|---|-----------|-------------|-----------|
| 1 | "Answer MUST contain at least 5 numbered steps, specific enough for a first-timer" | incomplete_answer | Baseline items had vague or too-few steps |
| 2 | "MUST include specific safety precautions relevant to this task" + per-category rules | safety_violations | Preemptive — 0% baseline but important to maintain |
| 3 | "Tools limited to basic home toolkit" + explicit whitelist | unrealistic_tools | Preemptive — prevent regression |
| 4 | "Do NOT recommend hiring a professional unless genuine danger" | overcomplicated_solution | 16% baseline rate — generator defaulted to "call a pro" |
| 5 | "Question must name the specific appliance/fixture/area" | missing_context | Preemptive — prevent generic references |
| 6 | "Each tip must be specific and actionable, NOT platitudes" + good example | poor_quality_tips | 18% baseline rate — highest failure mode |

---

## Corrected Run Results

| Metric | Value |
|--------|-------|
| Items generated | 50 |
| Schema validation pass rate | 100% (50/50) |
| Categories represented | All 5 (plumbing: 16, electrical: 10, hvac: 9, appliance: 8, general: 7) |
| Shannon entropy | 2.26 |
| **Overall failure rate** | **2.0%** (95% CI: 0.0% – 5.9%) |
| Worst items (3+ failures) | None |

### Per-mode failure rates (corrected)

| Failure Mode | Rate |
|-------------|------|
| poor_quality_tips | 2% |
| overcomplicated_solution | 0% |
| incomplete_answer | 0% |
| safety_violations | 0% |
| unrealistic_tools | 0% |
| missing_context | 0% |

---

## Before / After Comparison

| Failure Mode | Baseline | Corrected | Reduction |
|-------------|----------|-----------|-----------|
| incomplete_answer | 6.0% | 0.0% | 100.0% |
| safety_violations | 0.0% | 0.0% | — |
| unrealistic_tools | 0.0% | 0.0% | — |
| overcomplicated_solution | 16.0% | 0.0% | 100.0% |
| missing_context | 0.0% | 0.0% | — |
| poor_quality_tips | 18.0% | 2.0% | 88.9% |
| **OVERALL** | **30.0%** | **2.0%** | **93.3%** |

- Baseline 95% CI: 17.3% – 42.7% (n=50)
- Corrected 95% CI: 0.0% – 5.9% (n=50)
- Confidence intervals do NOT overlap — improvement is statistically significant

**RESULT: PASS — 93.3% improvement (target was >= 80%)**

---

## Success Criteria Checklist

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Q&A pairs per run | >= 50 | 50 | Pass |
| All 7 fields present | 100% | 100% | Pass |
| Schema validation rate | >= 95% | 100% | Pass |
| Repair categories covered | All 5 | All 5 | Pass |
| All 6 failure modes scored | All 6 | All 6 | Pass |
| Failure heatmap generated | Yes | Yes | Pass |
| Baseline failure rate | >= 15% | 30% | Pass |
| Corrections documented | Yes | 6 documented corrections | Pass |
| Improvement rate | >= 80% | 93.3% | Pass |
| Before/after comparison | Reported | Per-mode table + chart + CIs | Pass |
| Handles malformed responses | Yes | Retry logic, zero crashes | Pass |
| README with instructions | Yes | Yes | Pass |

All 12 criteria met.

---

## Key Takeaways

1. **The generate-evaluate-correct loop works.** Baseline prompts produced 30% failure rate. Targeted corrections based on failure data brought it to 2%. This is the same feedback loop used in production data pipelines.

2. **Measuring failure modes independently reveals actionable targets.** An aggregate "30% bad" doesn't tell you what to fix. Breaking it into 6 modes showed that `poor_quality_tips` and `overcomplicated_solution` were the dominant problems — and the fixes were specific prompt additions, not rewrites.

3. **Confidence intervals matter at small scale.** With n=50, a 30% rate has a CI of 17-43%. The corrected rate of 2% has a CI of 0-6%. The intervals don't overlap, which means the improvement isn't just noise.

4. **Instructor eliminates brittle string parsing.** The LLM-as-Judge mini-exercise used regex parsing on free-text LLM output. Using Instructor + Pydantic models gives schema-guaranteed structured output — the judge returns exactly 6 binary fields every time.

---

## Files Produced

```
mini-projects/01-synthetic-data-pipeline/
├── README.md                    # Setup and usage instructions
├── SUMMARY.md                   # This document
├── run_pipeline.py              # CLI entrypoint
├── pipeline/
│   ├── models.py                # Pydantic schemas
│   ├── client.py                # OpenAI + Instructor client factory
│   ├── generator.py             # Phase 1: 5 prompt templates + generation
│   ├── validator.py             # Phase 2: structural validation
│   ├── judge.py                 # Phase 3: LLM-as-Judge (6 failure modes)
│   ├── analyzer.py              # Phase 4: failure aggregation + charts
│   └── corrector.py             # Phase 5: documented corrected prompts
├── data/
│   ├── baseline.jsonl           # 50 generated + judged items (baseline)
│   ├── baseline_summary.json    # Baseline failure rates and coverage
│   ├── corrected.jsonl          # 50 generated + judged items (corrected)
│   ├── corrected_summary.json   # Corrected failure rates and coverage
│   └── comparison.json          # Side-by-side rates + improvement ratio
└── visuals/
    ├── cooccurrence_baseline.png
    ├── cooccurrence_corrected.png
    ├── failure_by_category_baseline.png
    ├── failure_by_category_corrected.png
    └── before_after_comparison.png
```
