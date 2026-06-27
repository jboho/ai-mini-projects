# Exercise 04 — DIY Repair Synthetic Data Pipeline

An automated pipeline that generates synthetic Q&A data for a Home DIY Repair assistant, evaluates quality with an LLM-as-Judge, analyzes failure patterns, corrects prompts, and proves measurable improvement.

## Quick Start

```bash
cd mini-projects/01-synthetic-data-pipeline

# 1. Run the baseline pipeline (generates 50 items, judges them, produces charts)
python run_pipeline.py --mode baseline

# 2. Run the corrected pipeline (same flow with improved prompts)
python run_pipeline.py --mode corrected

# 3. Compare before/after and check for >80% improvement
python run_pipeline.py --mode compare
```

## Prerequisites

From the project root with the venv active:

```bash
pip install instructor openai python-dotenv matplotlib seaborn pandas
```

You need a `.env` file with your API credentials. The pipeline searches for `.env` in:
1. `mini-projects/01-synthetic-data-pipeline/.env`
2. The repo root

Required variables:

```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1   # optional, for compatible providers
MODEL_NAME=gpt-4o-mini                       # optional, defaults to gpt-4o-mini
```

## Pipeline Phases

| Phase | Module | What it does |
|-------|--------|-------------|
| 1. Generation | `pipeline/generator.py` | 5 category-specific prompt templates produce diverse Q&A items via Instructor |
| 2. Validation | `pipeline/validator.py` | Pydantic schema checks (steps >= 3, tools >= 1, safety_info non-empty, etc.) |
| 3. Judging | `pipeline/judge.py` | LLM-as-Judge scores 6 failure modes independently per item (temp=0) |
| 4. Analysis | `pipeline/analyzer.py` | Aggregates failure rates, produces heatmap and charts |
| 5. Correction | `pipeline/corrector.py` | Documented prompt improvements targeting each failure mode |

## Repair Categories

- **Appliance** — refrigerators, washing machines, dryers, dishwashers, ovens
- **Plumbing** — leaks, clogs, fixture repairs, pipe problems
- **Electrical** — outlet replacement, switch repair, fixture installation
- **HVAC** — filter changes, thermostat issues, vent cleaning
- **General** — drywall, doors/windows, flooring, basic carpentry

## Failure Modes (scored by the judge)

| Mode | What it catches |
|------|----------------|
| `incomplete_answer` | Not enough detail to complete the repair |
| `safety_violations` | Missing or incorrect safety warnings |
| `unrealistic_tools` | Professional tools a homeowner wouldn't own |
| `overcomplicated_solution` | Recommends a pro for a straightforward DIY task |
| `missing_context` | Vague question or answer without specifics |
| `poor_quality_tips` | Generic platitudes instead of actionable advice |

## Output Files

After running all three modes:

```
data/
├── baseline.jsonl           # Generated + judged items (baseline prompts)
├── baseline_summary.json    # Per-mode rates, coverage, worst items
├── corrected.jsonl          # Generated + judged items (corrected prompts)
├── corrected_summary.json   # Same structure, corrected run
└── comparison.json          # Side-by-side rates, improvement ratio, CI

visuals/
├── cooccurrence_baseline.png         # Which failure modes appear together
├── cooccurrence_corrected.png        # Same, after corrections
├── failure_by_category_baseline.png  # Which repair categories fail most
├── failure_by_category_corrected.png # Same, after corrections
└── before_after_comparison.png       # Per-mode side-by-side bars
```

## Reading the Charts

**Co-occurrence heatmap** — Both axes are the 6 failure modes. Each cell shows how often two modes appear together on the same item. High values on off-diagonal cells mean correlated failures (likely a shared root cause). The diagonal shows each mode's individual rate.

**Failure by category** — Stacked bars for each repair category. Taller bars = more failures from that prompt template. Use this to decide which template needs the most correction.

**Before/after comparison** — Red bars (baseline) vs green bars (corrected) for each failure mode. Green bars should be much shorter. The terminal also prints exact rates and a PASS/FAIL verdict.

## Adjusting the Run

```bash
# Generate fewer items for a quick test
python run_pipeline.py --mode baseline --num-items 10

# Full run (default)
python run_pipeline.py --mode baseline --num-items 50
```

## Success Criteria

- >= 50 Q&A pairs per run without crashing
- >= 95% pass Pydantic schema validation
- All 5 repair categories represented
- Baseline failure rate >= 15%
- Post-correction improvement >= 80% reduction in overall failure rate
- All 6 failure modes independently measurable
