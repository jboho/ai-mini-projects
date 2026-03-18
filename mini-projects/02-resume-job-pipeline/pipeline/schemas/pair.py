"""Resume-Job pair schemas."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .job import JobDescription
from .resume import Resume


class FitLevel(str, enum.Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    PARTIAL = "Partial"
    POOR = "Poor"
    MISMATCH = "Mismatch"


class WritingStyle(str, enum.Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    ACHIEVEMENT = "achievement"
    CAREER_CHANGER = "career_changer"


class PairMetadata(BaseModel):
    pair_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    fit_level: FitLevel
    writing_style: WritingStyle
    correction_attempts: int = 0
    passed_validation: bool = True
    validation_error_count: int = 0


class ResumeJobPair(BaseModel):
    resume: Resume
    job: JobDescription
    metadata: PairMetadata
