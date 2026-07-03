# 05 — Dating Compatibility Fine-Tuning

Fine-tunes `all-MiniLM-L6-v2` with `CosineSimilarityLoss` to distinguish
compatible from incompatible dating pairs, gated by a 5-dimension data-quality
check and validated with rigorous statistical metrics. **Fully local — no API
key required.**

## Quickstart

```bash
cd mini-projects/05-dating-compatibility
pip install -r requirements.txt
python scripts/generate_data.py          # synthesize 6000 train + 1469 eval pairs
python run_pipeline.py --mode all         # quality gate -> baseline -> train -> evaluate -> compare
streamlit run app.py                       # dashboard + interactive compatibility checker
```

Training runs on CPU by default; set `EMBED_DEVICE=mps` (Apple Silicon) or
`cuda` to accelerate (`--mode all` takes ~3 min on MPS).

## Pipeline

`run_pipeline.py` modes: `explore | quality | baseline | train | evaluate | compare | all`.

```
generate_data -> data_quality (>=60 gate) -> baseline eval -> fine-tune -> eval -> compare + visuals
```

| Module | Responsibility |
|--------|----------------|
| `data_gen.py` | synthetic pair generator across the preference hierarchy |
| `data_loader.py` | validated JSONL loading + distribution stats |
| `data_quality.py` | 5-dimension quality evaluator (Data Quality, Diversity, Bias, Linguistic, Real-life) |
| `evaluator.py` | margin, Cohen's d, FPR, HDBSCAN cluster purity, classification metrics |
| `trainer.py` | sentence-transformers fine-tuning (CosineSimilarityLoss) |
| `visualizer.py` | similarity dists, metric bars, UMAP, FPR heatmap, ROC |

## Results

Data quality gate: **85/100** (passes ≥ 60). Fine-tuning over 6000 synthetic
pairs hits **all 9 targets**:

| Metric | Baseline | Fine-tuned | Target |
|--------|----------|-----------|--------|
| margin | 0.202 | **0.990** | ≥ 0.10 ✓ |
| effect size (Cohen's d) | 1.79 | **11.99** | ≥ 0.50 ✓ |
| false positive rate | 0.595 | **0.010** | ≤ 0.10 ✓ |
| cluster purity | 0.574 | **0.984** | ≥ 0.70 ✓ |
| accuracy | 0.684 | **0.995** | ≥ 0.90 ✓ |
| AUC-ROC | 0.888 | **1.000** | ≥ 0.90 ✓ |

Reports in `reports/`, charts in `visuals/`. (The synthetic data is cleanly
separable, so the fine-tuned model reaches near-perfect separation — the point
is that the pipeline measures and proves the improvement end-to-end.)

## Frontend

`streamlit run app.py` — three tabs:
- **Data Quality** — the 5-dimension scores and gate status.
- **Results** — baseline vs fine-tuned table + all visualizations.
- **Compatibility Checker** — type two profiles and the fine-tuned model scores
  their match, shown next to the baseline score so you can see what fine-tuning
  changed.

## Tests

```bash
pytest                 # 12 offline tests (models, metrics, generator, quality)
ruff check .
```
