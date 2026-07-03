"""ThemeAgent: cluster feedback into 5-10 named themes via the LLM."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from ..models import Feedback, SentimentResult, Theme

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You cluster customer feedback into 5-10 distinct themes. Each theme has a "
    "short name, a one-sentence description, keywords, the product_area it relates "
    "to, and the list of feedback IDs that belong to it. Cover the major pain points."
)


class _ThemeItem(BaseModel):
    name: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    product_area: str = ""
    feedback_ids: list[str] = Field(default_factory=list)


class _ThemeOut(BaseModel):
    themes: list[_ThemeItem]


class ThemeAgent:
    def __init__(self, model: str | None = None, temperature: float = 0.5, client=None) -> None:
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

    def extract(
        self,
        feedback: list[Feedback],
        sentiments: list[SentimentResult] | None = None,
        max_themes: int = 10,
    ) -> list[Theme]:
        catalog = "\n".join(f"{fb.id}: {fb.text[:200]}" for fb in feedback[:200])
        out = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_model=_ThemeOut,
            messages=[
                {"role": "system", "content": f"{_SYSTEM} Return at most {max_themes} themes."},
                {"role": "user", "content": f"Feedback:\n{catalog}"},
            ],
        )
        pain = {s.feedback_id: s.pain_intensity for s in (sentiments or [])}
        themes = []
        for i, t in enumerate(out.themes[:max_themes]):
            pains = [pain[fid] for fid in t.feedback_ids if fid in pain]
            themes.append(
                Theme(
                    theme_id=f"T{i + 1}",
                    name=t.name,
                    description=t.description,
                    keywords=t.keywords,
                    feedback_ids=t.feedback_ids,
                    avg_pain=round(sum(pains) / len(pains), 4) if pains else 0.0,
                    product_area=t.product_area,
                )
            )
        return themes
