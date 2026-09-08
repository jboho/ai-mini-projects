"""Pydantic request/response models (non-ORM) shared across services and agents."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    category: str
    confidence: float
    method: str  # keyword | component | pattern | llm | fallback
    evidence: str = ""


class TextAnalysisResult(BaseModel):
    errors: list[str] = Field(default_factory=list)
    stack_traces: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    has_error: bool = False
    has_stacktrace: bool = False


class RootCauseResult(BaseModel):
    summary: str = ""
    what_failed: str = ""
    why_failed: str = ""
    evidence: str = ""
    confidence: float = 0.0
    suggested_steps: list[str] = Field(default_factory=list)


class ResolutionSuggestion(BaseModel):
    title: str
    steps: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    based_on_keys: list[str] = Field(default_factory=list)
    category: str = "other"


class TriageAction(BaseModel):
    action_type: str
    description: str = ""
    target_project: str = ""
    impact_level: str = "LOW"


class AlertRule(BaseModel):
    name: str
    priority_threshold: str = "Major"  # Blocker > Critical > Major > Minor > Trivial
    categories: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)  # slack | email | pagerduty
    cooldown_minutes: int = 60
