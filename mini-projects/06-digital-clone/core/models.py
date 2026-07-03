"""Pydantic models for the digital clone system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    subject: str = ""
    body: str
    timestamp: datetime | None = None
    folder: str = ""


class StyleFeatures(BaseModel):
    avg_message_length: float = 0.0
    greeting_patterns: dict[str, float] = Field(default_factory=dict)
    signoff_patterns: dict[str, float] = Field(default_factory=dict)
    punctuation_patterns: dict[str, float] = Field(default_factory=dict)
    capitalization_ratio: float = 0.0
    question_frequency: float = 0.0
    vocabulary_richness: float = 0.0
    common_phrases: list[str] = Field(default_factory=list)
    reasoning_patterns: dict[str, float] = Field(default_factory=dict)
    sentiment_distribution: dict[str, float] = Field(default_factory=dict)
    formality_level: float = 0.0
    technical_terminology_usage: float = 0.0


class StyleProfile(BaseModel):
    employee_name: str
    email_count: int = 0
    style_features: StyleFeatures
    style_embedding: list[float] = Field(default_factory=list)
    last_updated: datetime | None = None
    learning_alpha: float = 0.3


class KnowledgeChunk(BaseModel):
    chunk_id: str
    content: str
    source_topic: str = ""
    source_field: str = ""
    chunk_index: int = 0
    embedding: list[float] | None = None


class EvaluationConfig(BaseModel):
    style_weight: float = 0.4
    groundedness_weight: float = 0.4
    confidence_weight: float = 0.2
    deliver_threshold: float = 0.75


class EvaluationResult(BaseModel):
    style_score: float = Field(ge=0, le=1)
    groundedness_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    final_score: float = Field(ge=0, le=1)
    decision: Literal["deliver", "fallback"]
    reasoning: str = ""


class FallbackResponse(BaseModel):
    trigger_reason: str
    context_summary: str = ""
    calendar_link: str = ""
    available_slots: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    query: str
    response: str | None = None
    evaluation: EvaluationResult
    fallback: FallbackResponse | None = None
    retrieved_chunks: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
