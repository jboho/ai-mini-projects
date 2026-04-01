"""Validation error schemas with structured error categorization."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class ValidationErrorCategory(str, enum.Enum):
    MISSING_FIELD = "missing_field"
    TYPE_MISMATCH = "type_mismatch"
    FORMAT_VIOLATION = "format_violation"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"


class ValidationError(BaseModel):
    field_path: str
    category: ValidationErrorCategory
    invalid_value: str | None = None
    expected_format: str | None = None
    message: str


class ValidationResult(BaseModel):
    pair_id: str
    is_valid: bool
    errors: list[ValidationError] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def errors_by_category(
        self,
    ) -> dict[ValidationErrorCategory, list[ValidationError]]:
        result: dict[ValidationErrorCategory, list[ValidationError]] = {}
        for err in self.errors:
            result.setdefault(err.category, []).append(err)
        return result
