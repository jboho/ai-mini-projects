"""Pydantic schemas for the DIY repair synthetic data pipeline."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class RepairCategory(str, enum.Enum):
    APPLIANCE = "appliance"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    GENERAL = "general"


class DIYRepairItem(BaseModel):
    """A single generated DIY repair Q&A item."""

    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    equipment_problem: str = Field(..., min_length=1)
    tools_required: list[str] = Field(..., min_length=1)
    steps: list[str] = Field(..., min_length=3)
    safety_info: str = Field(..., min_length=1)
    tips: list[str] = Field(..., min_length=1)

    @field_validator("steps")
    @classmethod
    def steps_must_be_nonempty_strings(cls, v: list[str]) -> list[str]:
        if any(not s.strip() for s in v):
            raise ValueError("Each step must be a non-empty string")
        return v

    @field_validator("tools_required")
    @classmethod
    def tools_must_be_nonempty_strings(cls, v: list[str]) -> list[str]:
        if any(not t.strip() for t in v):
            raise ValueError("Each tool must be a non-empty string")
        return v

    @field_validator("tips")
    @classmethod
    def tips_must_be_nonempty_strings(cls, v: list[str]) -> list[str]:
        if any(not t.strip() for t in v):
            raise ValueError("Each tip must be a non-empty string")
        return v


FAILURE_MODES = [
    "incomplete_answer",
    "safety_violations",
    "unrealistic_tools",
    "overcomplicated_solution",
    "missing_context",
    "poor_quality_tips",
]


class JudgeResult(BaseModel):
    """LLM-as-Judge evaluation result for a single Q&A item."""

    incomplete_answer: int = Field(..., ge=0, le=1)
    safety_violations: int = Field(..., ge=0, le=1)
    unrealistic_tools: int = Field(..., ge=0, le=1)
    overcomplicated_solution: int = Field(..., ge=0, le=1)
    missing_context: int = Field(..., ge=0, le=1)
    poor_quality_tips: int = Field(..., ge=0, le=1)

    @property
    def overall_failure(self) -> bool:
        return any(
            getattr(self, mode) == 1 for mode in FAILURE_MODES
        )

    @property
    def failure_count(self) -> int:
        return sum(getattr(self, mode) for mode in FAILURE_MODES)

    def to_dict(self) -> dict:
        data = self.model_dump()
        data["overall_failure"] = self.overall_failure
        data["failure_count"] = self.failure_count
        return data


class GenerationMetadata(BaseModel):
    """Metadata tracked per generated item (not part of final dataset)."""

    trace_id: str
    category: RepairCategory
    prompt_version: str = "baseline"
    passed_validation: bool = True
    validation_errors: list[str] = Field(default_factory=list)
    judge_result: JudgeResult | None = None
    model_name: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PipelineRecord(BaseModel):
    """One complete record: generated item + metadata + judge result."""

    trace_id: str
    item: DIYRepairItem | None = None
    metadata: GenerationMetadata
    judge_result: JudgeResult | None = None
