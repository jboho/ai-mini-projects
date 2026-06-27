"""Job description domain schemas."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ExperienceLevel(str, enum.Enum):
    ENTRY = "Entry"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"
    EXECUTIVE = "Executive"


class Company(BaseModel):
    name: str = Field(..., min_length=1)
    industry: str = Field(..., min_length=1)
    size: str = Field(..., description="e.g. '50-200 employees'")
    location: str = Field(..., min_length=1)


class JobRequirements(BaseModel):
    required_skills: list[str] = Field(..., min_length=1)
    preferred_skills: list[str] = Field(default_factory=list)
    min_education: str = Field(..., description="e.g. 'Bachelor's in CS'")
    experience_years: int = Field(..., ge=0, le=30)
    experience_level: ExperienceLevel


class JobMetadata(BaseModel):
    trace_id: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    is_niche_role: bool = False


class JobDescription(BaseModel):
    company: Company
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=20)
    requirements: JobRequirements
    metadata: JobMetadata
