"""SentimentAgent: per-feedback sentiment + pain intensity via structured output."""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field

from ..models import Feedback, SentimentResult

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You analyze customer feedback. Return the overall sentiment AND a separate "
    "pain_intensity in [0,1] measuring how strongly the user is hurting/frustrated "
    "(independent of sentiment polarity). A factual negative review can have lower "
    "pain than an emotional one."
)


class _SentimentOut(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0, le=1)
    pain_intensity: float = Field(ge=0, le=1)
    reasoning: str = ""


class SentimentAgent:
    def __init__(self, model: str | None = None, temperature: float = 0.3, client=None) -> None:
        self.model = model
        self.temperature = temperature
        self._client = client

    @property
    def client(self):
        if self._client is None:
            from ..client import get_instructor_client, get_model_name

            self._client = get_instructor_client()
            self.model = self.model or get_model_name()
        return self._client

    def analyze(self, feedback: Feedback) -> SentimentResult:
        out = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_model=_SentimentOut,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": feedback.text[:1500]},
            ],
        )
        return SentimentResult(feedback_id=feedback.id, **out.model_dump())

    def analyze_batch(self, feedback: list[Feedback]) -> list[SentimentResult]:
        results = []
        for fb in feedback:
            try:
                results.append(self.analyze(fb))
            except (ValueError, RuntimeError) as exc:
                logger.warning("sentiment failed for %s: %s", fb.id, exc)
        return results
