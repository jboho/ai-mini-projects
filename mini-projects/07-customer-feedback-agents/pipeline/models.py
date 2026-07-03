"""Pydantic models for the customer feedback pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["amazon", "yelp", "app_store"]
Sentiment = Literal["positive", "neutral", "negative"]


class Feedback(BaseModel):
    id: str
    source: Source
    text: str = Field(min_length=1)
    rating: int | None = None  # 1-5 stars
    date: str | None = None
    product_area: str | None = None
    metadata: dict = Field(default_factory=dict)


class SentimentResult(BaseModel):
    feedback_id: str
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1)
    pain_intensity: float = Field(ge=0, le=1)
    reasoning: str = ""


class Theme(BaseModel):
    theme_id: str
    name: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    feedback_ids: list[str] = Field(default_factory=list)
    avg_pain: float = 0.0
    product_area: str = ""


class RoadmapItem(BaseModel):
    item_id: str
    title: str
    description: str = ""
    product_area: str = ""
    status: str = "backlog"


class AlignmentResult(BaseModel):
    theme_id: str
    roadmap_item_id: str | None = None
    similarity: float = 0.0
    aligned: bool = False
    alignment_reason: str = ""


class GapAnalysis(BaseModel):
    theme_id: str
    theme_name: str
    feedback_count: int = 0
    avg_pain: float = 0.0
    avg_sentiment_neg: float = 0.0
    has_coverage: bool = False
    priority_score: float = Field(ge=0, le=1, default=0.0)
    recommendations: list[str] = Field(default_factory=list)
