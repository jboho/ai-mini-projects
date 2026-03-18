---
name: Dating Compatibility Pipeline
overview: Build a dating compatibility system at `mini-projects/05-dating-compatibility/` that fine-tunes `all-MiniLM-L6-v2` with CosineSimilarityLoss to distinguish compatible from incompatible dating pairs, validated through a 5-dimension data quality gate and rigorous statistical evaluation (Cohen's d >= 0.5, FPR <= 0.10, cluster purity >= 0.70).
todos:
  - id: scaffold
    content: Create project directory structure, requirements.txt, pipeline/__init__.py
    status: pending
  - id: models
    content: Implement Pydantic schemas in pipeline/models.py (DatingPair, DataQualityReport, EvaluationMetrics, ComparisonReport)
    status: pending
  - id: data-loader
    content: Implement pipeline/data_loader.py -- JSONL loading with Pydantic validation, distribution stats logging
    status: pending
  - id: data-quality
    content: Implement pipeline/data_quality.py -- 5-dimension quality evaluator (Data Quality, Diversity, Bias, Linguistic, Real-life Matching) with >= 60/100 gate
    status: pending
  - id: evaluator
    content: Implement pipeline/evaluator.py -- shared evaluate_model() computing margin, Cohen's d, FPR, cluster purity, classification metrics, per-category breakdown
    status: pending
  - id: trainer
    content: Implement pipeline/trainer.py -- sentence-transformers fine-tuning with CosineSimilarityLoss (4 epochs, batch 16, lr 2e-5)
    status: pending
  - id: visualizer
    content: Implement pipeline/visualizer.py -- similarity distributions, UMAP projections, before/after bars, per-category heatmap, ROC curves
    status: pending
  - id: run-pipeline
    content: "Implement run_pipeline.py CLI with modes: explore, quality, baseline, train, evaluate, compare, all"
    status: pending
  - id: tests
    content: Write unit tests for models, metrics calculations, and data quality scoring
    status: pending
  - id: verify
    content: End-to-end run with --mode all, verify all targets met, self-audit
    status: pending
isProject: false
---

# Dating Compatibility Fine-Tuning Pipeline

## Project Location & Structure

```
mini-projects/05-dating-compatibility/
├── run_pipeline.py                # CLI entrypoint (--mode explore|quality|baseline|train|evaluate|compare|all)
├── requirements.txt               # Project-specific deps
├── .env.example                   # Template for any config
├── data/                          # Pre-provided dataset (user downloads data.zip here)
│   ├── dating_pairs.jsonl         # 6,000 training pairs
│   ├── eval_pairs.jsonl           # 1,469 evaluation pairs
│   ├── dating_pairs_metadata.json
│   └── eval_pairs_metadata.json
├── models/                        # Saved fine-tuned model
│   └── finetuned-minilm/
├── reports/                       # JSON metric reports
│   ├── data_quality_report.json
│   ├── baseline_metrics.json
│   └── finetuned_metrics.json
├── visuals/                       # PNG/HTML visualizations
└── pipeline/
    ├── __init__.py
    ├── models.py                  # Pydantic schemas
    ├── data_loader.py             # JSONL loading + validation
    ├── data_quality.py            # 5-dimension quality evaluator
    ├── evaluator.py               # Shared metric computation
    ├── trainer.py                 # Fine-tuning with CosineSimilarityLoss
    └── visualizer.py              # Distribution plots, UMAP, comparisons
```

Follows the established pattern from [mini-projects/01-synthetic-data-pipeline/](mini-projects/01-synthetic-data-pipeline/): `run_pipeline.py` entrypoint, `pipeline/` package, `data/` + `visuals/` output dirs.

## Dependencies (`requirements.txt`)

```
sentence-transformers
torch
pydantic
numpy
pandas
scipy
scikit-learn
matplotlib
seaborn
umap-learn
hdbscan
```

No OpenAI/LLM dependency needed -- this is a local ML pipeline.

## Phase 1: Pydantic Models (`pipeline/models.py`)

Core data schemas validated at load time:

- **`DatingPair`** -- Schema for each JSONL record: `text_1`, `text_2`, `label` (0 or 1), `category`, `subcategory`, `pair_type`. Validators: label in {0,1}, text fields non-empty, pair_type in the 9 allowed values.
- **`DataQualityScore`** -- Per-dimension score (0-100) + details dict.
- **`DataQualityReport`** -- All 5 dimension scores + overall score + pass/fail gate.
- **`EvaluationMetrics`** -- The 4 core metrics (margin, effect_size, false_positive_rate, cluster_purity) + classification metrics (accuracy, precision, recall, f1, auc_roc) + per-category breakdown dict.
- **`ComparisonReport`** -- Baseline vs finetuned `EvaluationMetrics` + improvement percentages + pass/fail per target.

## Phase 2: Data Loading (`pipeline/data_loader.py`)

- Load JSONL files line-by-line, validate each line with `DatingPair.model_validate_json()`
- Return `list[DatingPair]` for train and eval sets
- Log counts: total, compatible, incompatible, per pair_type, per category
- Fail fast on malformed records with clear error messages

## Phase 3: Data Quality Evaluator (`pipeline/data_quality.py`)

Scores the dataset across 5 dimensions (each 0-100), produces an overall score (average). **Must pass >= 60/100 before training proceeds.**

| Dimension | What it checks |
|-----------|----------------|
| Data Quality | Completeness (no empty fields), format consistency, duplicate rate (<5%), label validity |
| Diversity | Vocabulary richness (unique tokens / total tokens), category distribution evenness (Shannon entropy), label balance (40-60% range), text length variance |
| Bias Detection | Gender prefix balance (boy/girl), category-label correlation (no category dominates one label), text length bias across labels, vocabulary overlap bias |
| Linguistic Quality | Mean text length, readability (avg words/sentence), repetition rate (duplicate n-grams), coherence (no garbled text) |
| Real-life Matching | Preference hierarchy adherence (dealbreakers > values > lifestyle > interests), multi-preference pair presence, edge case coverage |

Output: `reports/data_quality_report.json` with per-dimension scores, details, and overall score.

## Phase 4: Baseline Evaluation (`evaluator.py` + `run_pipeline.py`)

Load pre-trained `all-MiniLM-L6-v2`, encode all eval pairs, compute:

**Core embedding metrics:**
- **Margin**: `mean(compatible_sims) - mean(incompatible_sims)` (target >= 0.10)
- **Effect size (Cohen's d)**: `(mean_compat - mean_incompat) / pooled_std` (target >= 0.50)
- **FPR**: `count(incompatible_sims > 0.5) / count(incompatible)` (target <= 0.10)
- **Cluster purity**: HDBSCAN on concatenated embeddings, measure label homogeneity within clusters (target >= 0.70)

**Classification metrics** (threshold = 0.5):
- Accuracy, Precision, Recall, F1, AUC-ROC (all target >= 0.90)

**Per-category breakdown**: All metrics broken down by `category` field.

Output: `reports/baseline_metrics.json`

The `evaluator.py` module exposes a single `evaluate_model(model, pairs) -> EvaluationMetrics` function used by both baseline and post-training evaluation.

### Key metric implementations

```python
# Cohen's d
pooled_std = np.sqrt((np.std(compat_sims)**2 + np.std(incompat_sims)**2) / 2)
effect_size = (np.mean(compat_sims) - np.mean(incompat_sims)) / pooled_std

# Cluster purity via HDBSCAN
clusterer = hdbscan.HDBSCAN(min_cluster_size=15)
cluster_labels = clusterer.fit_predict(all_embeddings)
# For each cluster, purity = max(count_compat, count_incompat) / cluster_size
# Overall purity = weighted average across clusters (excluding noise label -1)
```

## Phase 5: Fine-Tuning (`pipeline/trainer.py`)

Uses sentence-transformers' native training API with `CosineSimilarityLoss`:

```python
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

model = SentenceTransformer("all-MiniLM-L6-v2")
train_examples = [
    InputExample(texts=[p.text_1, p.text_2], label=float(p.label))
    for p in train_pairs
]
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.CosineSimilarityLoss(model)

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=4,
    warmup_steps=100,
    output_path="models/finetuned-minilm",
    show_progress_bar=True,
)
```

This is intentionally simple -- sentence-transformers handles the training loop, gradient accumulation, and model saving. The spec's recommended defaults (4 epochs, batch 16, lr 2e-5) align with the library's defaults.

The trainer module:
- Accepts hyperparameters via function args with sensible defaults
- Logs training progress
- Saves the model to `models/finetuned-minilm/`
- Returns the path to the saved model

## Phase 6: Post-Training Evaluation & Comparison

Reuses `evaluator.evaluate_model()` on the fine-tuned model. Comparison logic in `run_pipeline.py`:
- Load both metric reports
- Compute improvement percentages: `(finetuned - baseline) / abs(baseline) * 100`
- For FPR: lower is better, so `(baseline - finetuned) / baseline * 100`
- Check each metric against targets, report pass/fail
- Save `reports/finetuned_metrics.json` and print comparison table

## Phase 7: Visualizations (`pipeline/visualizer.py`)

Uses `matplotlib.use("Agg")` for headless rendering, saves to `visuals/`:

1. **Similarity distribution plots** -- Overlapping histograms of compatible vs incompatible cosine similarities (one for baseline, one for finetuned)
2. **Before/after comparison** -- Side-by-side bar chart of all 4 core metrics
3. **UMAP projections** -- 2D scatter plots colored by label (baseline vs finetuned side-by-side)
4. **Per-category FPR heatmap** -- Category x model heatmap showing FPR improvement
5. **ROC curves** -- Baseline vs finetuned overlaid

## CLI Design (`run_pipeline.py`)

```
python run_pipeline.py --mode explore     # Load data, print distribution stats
python run_pipeline.py --mode quality     # Run data quality evaluator
python run_pipeline.py --mode baseline    # Evaluate pre-trained model
python run_pipeline.py --mode train       # Fine-tune the model
python run_pipeline.py --mode evaluate    # Evaluate fine-tuned model
python run_pipeline.py --mode compare     # Side-by-side comparison + visualizations
python run_pipeline.py --mode all         # Run full pipeline end-to-end
```

Follows the argparse pattern from [mini-projects/01-synthetic-data-pipeline/run_pipeline.py](mini-projects/01-synthetic-data-pipeline/run_pipeline.py).

## Testing Strategy

- Unit tests for Pydantic model validation (valid/invalid pairs)
- Unit tests for metric calculations (known inputs -> expected outputs)
- Unit tests for data quality scoring dimensions
- Integration test: load a small fixture, run baseline eval, verify metric structure

## Key Design Decisions

- **CosineSimilarityLoss over triplet loss**: The spec explicitly requires it, and the dataset is pairs (not triplets). sentence-transformers' `CosineSimilarityLoss` maps label=1 to sim=1.0 and label=0 to sim=0.0, pushing compatible embeddings together and incompatible apart.
- **sentence-transformers native training**: Unlike the mini-exercise which uses raw `AutoModel` + LoRA + custom loss, this project uses `model.fit()` -- simpler, less error-prone, and matches the spec's technology requirements.
- **Shared `evaluator.py`**: One function evaluates any model, ensuring identical metric computation for baseline and finetuned comparison.
- **Quality gate before training**: The `--mode all` pipeline will abort if data quality < 60/100.
- **No LLM/API calls**: This is entirely local ML. No `.env` with API keys needed (unlike project 01).

## File Size Budget (250-line rule)

| Module | Estimated lines | Notes |
|--------|----------------|-------|
| `models.py` | ~80 | Pydantic schemas |
| `data_loader.py` | ~60 | JSONL loading + stats |
| `data_quality.py` | ~220 | 5 scoring dimensions (largest module) |
| `evaluator.py` | ~180 | Metrics + HDBSCAN + classification |
| `trainer.py` | ~70 | Thin wrapper around sentence-transformers |
| `visualizer.py` | ~200 | 5 chart types |
| `run_pipeline.py` | ~200 | CLI + pipeline orchestration |
