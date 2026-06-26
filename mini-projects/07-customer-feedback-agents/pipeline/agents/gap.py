"""GapAgent: priority scoring of themes + LLM recommendations for uncovered gaps."""

from __future__ import annotations

import logging

from ..config import PriorityWeights
from ..models import AlignmentResult, GapAnalysis, SentimentResult, Theme

logger = logging.getLogger(__name__)


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def priority_score(
    avg_pain: float,
    frequency_norm: float,
    has_coverage: bool,
    neg_ratio: float,
    weights: PriorityWeights,
) -> float:
    """Weighted priority: high pain/frequency/negativity and NO roadmap coverage rank highest."""
    coverage_gap = 0.0 if has_coverage else 1.0
    score = (
        weights.pain * avg_pain
        + weights.frequency * frequency_norm
        + weights.coverage * coverage_gap
        + weights.sentiment * neg_ratio
    )
    return round(_clamp01(score), 4)


class GapAgent:
    def __init__(
        self, weights: PriorityWeights | None = None, model: str | None = None, client=None
    ) -> None:
        self.weights = weights or PriorityWeights()
        self.model = model
        self._client = client

    @property
    def client(self):
        if self._client is None:
            from ..client import get_openai_client, get_model_name

            self._client = get_openai_client()
            self.model = self.model or get_model_name()
        return self._client

    def analyze(
        self,
        themes: list[Theme],
        alignments: list[AlignmentResult],
        sentiments: list[SentimentResult],
        generate_recommendations: bool = True,
    ) -> list[GapAnalysis]:
        aligned = {a.theme_id: a.aligned for a in alignments}
        sent_by_id = {s.feedback_id: s for s in sentiments}
        max_count = max((len(t.feedback_ids) for t in themes), default=1) or 1

        gaps: list[GapAnalysis] = []
        for t in themes:
            count = len(t.feedback_ids)
            sents = [sent_by_id[f] for f in t.feedback_ids if f in sent_by_id]
            neg_ratio = (
                sum(1 for s in sents if s.sentiment == "negative") / len(sents) if sents else 0.0
            )
            has_cov = aligned.get(t.theme_id, False)
            score = priority_score(t.avg_pain, count / max_count, has_cov, neg_ratio, self.weights)
            recs = self._recommend(t) if (generate_recommendations and not has_cov) else []
            gaps.append(
                GapAnalysis(
                    theme_id=t.theme_id,
                    theme_name=t.name,
                    feedback_count=count,
                    avg_pain=t.avg_pain,
                    avg_sentiment_neg=round(neg_ratio, 4),
                    has_coverage=has_cov,
                    priority_score=score,
                    recommendations=recs,
                )
            )
        return sorted(gaps, key=lambda g: -g.priority_score)

    def _recommend(self, theme: Theme) -> list[str]:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": "Suggest 2 concrete product actions for the theme. One per line, no numbering.",
                    },
                    {"role": "user", "content": f"Theme: {theme.name}\n{theme.description}"},
                ],
            )
            text = resp.choices[0].message.content or ""
            return [line.strip("-• ").strip() for line in text.splitlines() if line.strip()][:2]
        except (ValueError, RuntimeError) as exc:
            logger.warning("recommendation failed for %s: %s", theme.theme_id, exc)
            return []
