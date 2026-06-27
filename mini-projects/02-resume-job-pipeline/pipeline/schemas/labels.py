"""Failure label schemas — rule-based metrics and LLM-as-Judge result."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FailureLabels(BaseModel):
    """Six rule-based failure metrics computed per resume-job pair."""

    pair_id: str
    skills_overlap: float = Field(..., ge=0.0, le=1.0, description="Jaccard similarity")
    experience_mismatch: bool
    seniority_mismatch: bool
    missing_core_skills: bool
    hallucinated_skills: bool
    awkward_language: bool

    @property
    def any_failure(self) -> bool:
        return any([
            self.experience_mismatch,
            self.seniority_mismatch,
            self.missing_core_skills,
            self.hallucinated_skills,
            self.awkward_language,
        ])

    @property
    def failure_count(self) -> int:
        return sum([
            self.experience_mismatch,
            self.seniority_mismatch,
            self.missing_core_skills,
            self.hallucinated_skills,
            self.awkward_language,
        ])


class JudgeResult(BaseModel):
    """LLM-as-Judge structured evaluation for a resume-job pair."""

    pair_id: str
    hallucination_score: int = Field(..., ge=0, le=5, description="0=none, 5=severe")
    awkward_language_score: int = Field(..., ge=0, le=5)
    quality_score: int = Field(..., ge=0, le=10, description="Overall quality")
    fit_assessment: str = Field(..., description="Brief fit assessment")
    recommendations: list[str] = Field(default_factory=list)
