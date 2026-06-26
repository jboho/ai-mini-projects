"""EvaluatorAgent: multi-metric scoring + deliver/fallback decision (core math)."""

from __future__ import annotations

from core.models import EvaluationConfig, EvaluationResult, KnowledgeChunk, StyleProfile
from core.scoring import evaluate_response


class EvaluatorAgent:
    role = "Quality Evaluator"

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def evaluate(
        self,
        response: str,
        retrieved: list[tuple[KnowledgeChunk, float]],
        profile: StyleProfile,
    ) -> EvaluationResult:
        return evaluate_response(response, retrieved, profile, self.config)
