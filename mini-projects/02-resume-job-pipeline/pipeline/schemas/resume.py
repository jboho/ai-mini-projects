"""Resume domain schemas."""

from __future__ import annotations

import enum
import re
from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class ProficiencyLevel(str, enum.Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


class ContactInfo(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    linkedin: str | None = None
    portfolio: str | None = None

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Phone must contain at least 10 digits")
        return v


class Education(BaseModel):
    degree: str = Field(..., min_length=1)
    institution: str = Field(..., min_length=1)
    graduation_date: str = Field(..., description="ISO date YYYY-MM-DD or YYYY-MM")
    gpa: float | None = Field(None, ge=0.0, le=4.0)
    coursework: list[str] = Field(default_factory=list)

    @field_validator("graduation_date")
    @classmethod
    def graduation_date_format(cls, v: str) -> str:
        for fmt in ("%Y-%m-%d", "%Y-%m"):
            try:
                datetime.strptime(v, fmt)
                return v
            except ValueError:
                continue
        raise ValueError("graduation_date must be YYYY-MM-DD or YYYY-MM")


class Experience(BaseModel):
    company: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    start_date: str = Field(..., description="ISO date YYYY-MM-DD or YYYY-MM")
    end_date: str | None = Field(None, description="ISO date or 'Present'")
    responsibilities: list[str] = Field(..., min_length=1)
    achievements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def end_after_start(self) -> Experience:
        if self.end_date and self.end_date.lower() != "present":
            for fmt in ("%Y-%m-%d", "%Y-%m"):
                try:
                    start = datetime.strptime(self.start_date, fmt)
                    end = datetime.strptime(self.end_date, fmt)
                    if end < start:
                        raise ValueError("end_date must be after start_date")
                    return self
                except ValueError as exc:
                    if "end_date must be after" in str(exc):
                        raise
                    continue
        return self


class Skill(BaseModel):
    name: str = Field(..., min_length=1)
    proficiency_level: ProficiencyLevel
    years_used: float | None = Field(None, ge=0)


class ResumeMetadata(BaseModel):
    trace_id: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    prompt_template: str
    fit_level: str
    writing_style: str


class Resume(BaseModel):
    contact: ContactInfo
    education: list[Education] = Field(..., min_length=1)
    experience: list[Experience] = Field(default_factory=list)
    skills: list[Skill] = Field(..., min_length=1)
    summary: str = Field(..., min_length=10)
    metadata: ResumeMetadata
