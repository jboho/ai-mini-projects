# Evidence Pack: Embedding Finetuning

Production patterns for embedding quality, false positive rate management, and training efficiency.

## What's Added

### 1. Distributed Tracing (`pipeline/tracing.py`)
- Logs embedding quality metrics per epoch (AUC, FPR by category)
- Traces every prediction with confidence and correctness
- Tracks finetuning progress

**Interview angle:** "I can see when the model starts overfitting (validation AUC plateaus). I can identify which categories (interests vs dealbreakers) are harder to learn and require different strategies."

### 2. Training Budgets (`pipeline/budgets.py`)
- Enforces early stopping when validation AUC doesn't improve (patience=3 epochs)
- Tracks compute hours budget (GPU time is expensive)
- Warns when FPR exceeds target (1%)

**Interview angle:** "Training budgets prevent wasted compute. If validation AUC plateaus, I stop immediately instead of waiting for max epochs. This saves hours of GPU time per experiment."

### 3. Quality Critics (`pipeline/critics.py`)
- **MatchCritic:** Validates match predictions and confidence ranges
- **ConfidenceCritic:** Checks if predicted confidence matches empirical accuracy
- **FalsePositiveRateCritic:** Enforces FPR < 1% for user experience

**Interview angle:** "Before showing a match to a user, I check: Is this prediction well-calibrated? Is the FPR acceptable? If not, I either require higher confidence thresholds or retrain."

## Usage

### Enable Tracing
```bash
export LANGFUSE_PUBLIC_KEY=...
python pipeline/trainer.py  # Traces all epochs
```

### Set Training Budgets
```bash
export BUDGET_MAX_EPOCHS=100
export BUDGET_MAX_COMPUTE_HOURS=10
python pipeline/trainer.py  # Stops early if AUC plateaus
```

### Enforce Quality
```python
from pipeline.critics import FalsePositiveRateCritic

critic = FalsePositiveRateCritic()
verdict = critic.evaluate_fpr(false_positive_rate=0.008, category="interests")
if not verdict.pass_:
    print("FPR too high; increase confidence threshold or retrain")
```

## Interview Questions

**Q: "How do you prevent overfitting in embedding finetuning?"**  
A: Early stopping with patience=3. If validation AUC doesn't improve for 3 consecutive epochs, I stop. This prevents overfitting while maximizing test-time generalization.

**Q: "What's your false positive rate target?"**  
A: 1% per category. At scale (1M users), 1% FPR means ~10k bad matches shown. Unacceptable UX. I enforce this with critics before any match is shown to users.

**Q: "How do you know which category (interests vs dealbreakers) is harder?"**  
A: Tracing logs AUC per category. Dealbreakers typically reach 0.93 AUC; interests take longer (0.90). This tells me to use different architectures or more training data for interests.

**Q: "How does your model scale to different user demographics?"**  
A: I track calibration error per demographic segment. If the model is overconfident for age 18-25 but underconfident for 35+, I retrain with balanced data sampling.

## Patterns Reusable

```python
# Early stopping
budget = get_budget_manager()
budget.record_training_step(loss=0.15, val_auc=0.92, val_fpr=0.008)
if budget.should_stop():
    print("Stop training; no improvement for 3 epochs")

# FPR enforcement
fpr_critic = FalsePositiveRateCritic()
verdict = fpr_critic.evaluate_fpr(0.012)
if not verdict.pass_:
    raise_alert("FPR too high; escalate to ML team")

# Tracing predictions
handler = get_trace_handler()
handler.trace_prediction(
    pair_id="u1_u2",
    predicted_match=True,
    confidence=0.82,
    category="interests"
)
```

## Comparison to Bootcamp Baseline

| Baseline | Evidence Pack |
|----------|---------------|
| Train embeddings, evaluate | + Early stopping prevents overfitting |
| Single quality metric | + Per-category breakdowns identify problem areas |
| Hope FPR is low | + Enforce FPR < 1% with critics |
