"""Pydantic schemas and shared constants for the dating compatibility pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Preference hierarchy (dealbreakers > values > lifestyle > interests) drives both
# generation and the "real-life matching" quality dimension.
CATEGORIES = ["dealbreakers", "values", "lifestyle", "interests", "multi"]

PAIR_TYPES = [
    "dealbreaker_aligned",
    "dealbreaker_conflict",
    "values_aligned",
    "values_conflict",
    "lifestyle_aligned",
    "lifestyle_conflict",
    "interests_aligned",
    "interests_conflict",
    "multi_preference",
]


class DatingPair(BaseModel):
    text_1: str = Field(min_length=1)
    text_2: str = Field(min_length=1)
    label: int  # 1 = compatible, 0 = incompatible
    category: str
    subcategory: str = ""
    pair_type: str

    @field_validator("label")
    @classmethod
    def _label_binary(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("label must be 0 or 1")
        return v

    @field_validator("pair_type")
    @classmethod
    def _pair_type_known(cls, v: str) -> str:
        if v not in PAIR_TYPES:
            raise ValueError(f"pair_type must be one of {PAIR_TYPES}")
        return v


class DataQualityScore(BaseModel):
    dimension: str
    score: float = Field(ge=0, le=100)
    details: dict = Field(default_factory=dict)


class DataQualityReport(BaseModel):
    dimensions: list[DataQualityScore]
    overall_score: float = Field(ge=0, le=100)
    passed: bool
    threshold: float = 60.0

    @property
    def by_dimension(self) -> dict[str, float]:
        return {d.dimension: d.score for d in self.dimensions}


class EvaluationMetrics(BaseModel):
    # Core embedding metrics
    margin: float = 0.0
    effect_size: float = 0.0  # Cohen's d
    false_positive_rate: float = 0.0
    cluster_purity: float = 0.0
    # Classification metrics (threshold 0.5)
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    auc_roc: float = 0.0
    per_category: dict[str, dict[str, float]] = Field(default_factory=dict)


class ComparisonReport(BaseModel):
    baseline: EvaluationMetrics
    finetuned: EvaluationMetrics
    improvements: dict[str, float] = Field(default_factory=dict)
    targets_met: dict[str, bool] = Field(default_factory=dict)


# Target thresholds from the project spec.
TARGETS = {
    "margin": 0.10,
    "effect_size": 0.50,
    "false_positive_rate": 0.10,  # lower is better
    "cluster_purity": 0.70,
    "accuracy": 0.90,
    "precision": 0.90,
    "recall": 0.90,
    "f1": 0.90,
    "auc_roc": 0.90,
}
