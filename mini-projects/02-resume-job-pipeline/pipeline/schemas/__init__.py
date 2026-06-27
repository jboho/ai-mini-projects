"""Pydantic schema package."""

from .job import Company, ExperienceLevel, JobDescription, JobMetadata, JobRequirements
from .labels import FailureLabels, JudgeResult
from .pair import FitLevel, PairMetadata, ResumeJobPair, WritingStyle
from .resume import (
    ContactInfo,
    Education,
    Experience,
    ProficiencyLevel,
    Resume,
    ResumeMetadata,
    Skill,
)
from .validation import ValidationError, ValidationErrorCategory, ValidationResult

__all__ = [
    "ContactInfo",
    "Education",
    "Experience",
    "ExperienceLevel",
    "FailureLabels",
    "FitLevel",
    "JobDescription",
    "JobMetadata",
    "JobRequirements",
    "JudgeResult",
    "Company",
    "PairMetadata",
    "ProficiencyLevel",
    "Resume",
    "ResumeJobPair",
    "ResumeMetadata",
    "Skill",
    "ValidationError",
    "ValidationErrorCategory",
    "ValidationResult",
    "WritingStyle",
]
