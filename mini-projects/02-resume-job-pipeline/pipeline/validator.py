"""Semantic validation of resume-job pairs with structured error categorization.

Instructor + Pydantic already enforce field types and basic constraints at
generation time. This module adds cross-field logical checks that cannot be
expressed as field-level validators (e.g. timeline plausibility, GPA presence
rules, skill list non-emptiness at the pair level).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from .schemas.pair import ResumeJobPair
from .schemas.validation import (
    ValidationError,
    ValidationErrorCategory,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_DATE_FMTS = ("%Y-%m-%d", "%Y-%m")


def _parse_date(s: str) -> datetime | None:
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _experience_years(pair: ResumeJobPair) -> float:
    """Sum total months across all experience entries, return as years."""
    total_months = 0.0
    for exp in pair.resume.experience:
        start = _parse_date(exp.start_date)
        if start is None:
            continue
        if exp.end_date and exp.end_date.lower() != "present":
            end = _parse_date(exp.end_date)
        else:
            end = datetime.now()
        if end and end >= start:
            total_months += (end.year - start.year) * 12 + (end.month - start.month)
    return total_months / 12


def validate_pair(pair: ResumeJobPair) -> ValidationResult:
    """Run semantic validation checks; return a ValidationResult."""
    errors: list[ValidationError] = []

    _check_experience_timeline(pair, errors)
    _check_graduation_not_future(pair, errors)
    _check_skill_list_nonempty(pair, errors)
    _check_years_experience_plausible(pair, errors)
    _check_required_skills_nonempty(pair, errors)
    _check_phone_format(pair, errors)

    result = ValidationResult(
        pair_id=pair.metadata.pair_id,
        is_valid=len(errors) == 0,
        errors=errors,
    )
    if errors:
        logger.debug(
            "Pair %s failed validation with %d errors",
            pair.metadata.pair_id, len(errors),
        )
    return result


def _check_experience_timeline(
    pair: ResumeJobPair, errors: list[ValidationError]
) -> None:
    for i, exp in enumerate(pair.resume.experience):
        start = _parse_date(exp.start_date)
        if start is None:
            errors.append(ValidationError(
                field_path=f"resume.experience[{i}].start_date",
                category=ValidationErrorCategory.FORMAT_VIOLATION,
                invalid_value=exp.start_date,
                expected_format="YYYY-MM-DD or YYYY-MM",
                message="start_date could not be parsed",
            ))
            continue
        if start > datetime.now():
            errors.append(ValidationError(
                field_path=f"resume.experience[{i}].start_date",
                category=ValidationErrorCategory.LOGICAL_INCONSISTENCY,
                invalid_value=exp.start_date,
                message="start_date is in the future",
            ))


def _check_graduation_not_future(
    pair: ResumeJobPair, errors: list[ValidationError]
) -> None:
    for i, edu in enumerate(pair.resume.education):
        dt = _parse_date(edu.graduation_date)
        if dt and dt > datetime.now():
            errors.append(ValidationError(
                field_path=f"resume.education[{i}].graduation_date",
                category=ValidationErrorCategory.LOGICAL_INCONSISTENCY,
                invalid_value=edu.graduation_date,
                message="graduation_date is in the future",
            ))


def _check_skill_list_nonempty(
    pair: ResumeJobPair, errors: list[ValidationError]
) -> None:
    for i, skill in enumerate(pair.resume.skills):
        if not skill.name.strip():
            errors.append(ValidationError(
                field_path=f"resume.skills[{i}].name",
                category=ValidationErrorCategory.MISSING_FIELD,
                message="Skill name is empty",
            ))


def _check_years_experience_plausible(
    pair: ResumeJobPair, errors: list[ValidationError]
) -> None:
    years = _experience_years(pair)
    # Flag if claimed total experience exceeds 50 years (impossible timeline)
    if years > 50:
        errors.append(ValidationError(
            field_path="resume.experience",
            category=ValidationErrorCategory.LOGICAL_INCONSISTENCY,
            invalid_value=str(round(years, 1)),
            message=f"Total experience ({years:.1f} years) exceeds plausible maximum",
        ))


def _check_required_skills_nonempty(
    pair: ResumeJobPair, errors: list[ValidationError]
) -> None:
    if not pair.job.requirements.required_skills:
        errors.append(ValidationError(
            field_path="job.requirements.required_skills",
            category=ValidationErrorCategory.MISSING_FIELD,
            message="required_skills list is empty",
        ))


def _check_phone_format(
    pair: ResumeJobPair, errors: list[ValidationError]
) -> None:
    digits = re.sub(r"\D", "", pair.resume.contact.phone)
    if len(digits) < 10:
        errors.append(ValidationError(
            field_path="resume.contact.phone",
            category=ValidationErrorCategory.FORMAT_VIOLATION,
            invalid_value=pair.resume.contact.phone,
            expected_format="at least 10 digits",
            message="Phone number has fewer than 10 digits",
        ))
