"""Correction loop: feed validation errors back to the LLM and re-validate.

Design: the corrector only fixes schema/logical validation failures, not the
failure-label metrics. A pair is "correctable" when its ValidationResult
contains actionable errors with field paths and expected formats. The LLM is
given the original resume JSON, the specific errors, and precise fix
instructions, then asked to regenerate the Resume only (the job is immutable).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import instructor

from .client import get_instructor_client
from .config import Settings, get_settings
from .schemas.pair import ResumeJobPair
from .schemas.resume import Resume, ResumeMetadata
from .schemas.validation import ValidationResult
from .validator import validate_pair

logger = logging.getLogger(__name__)

RETRY_DELAY_BASE = 1.5


@dataclass
class CorrectionStats:
    total_pairs: int = 0
    corrected_pairs: int = 0
    permanently_failed: int = 0
    attempts_histogram: dict[int, int] = field(default_factory=dict)
    failure_reasons: list[str] = field(default_factory=list)

    @property
    def correction_rate(self) -> float:
        if self.total_pairs == 0:
            return 0.0
        return self.corrected_pairs / self.total_pairs


def _build_correction_prompt(
    resume_json: str, validation_result: ValidationResult
) -> str:
    error_lines = []
    for err in validation_result.errors:
        line = (
            f"  - Field: {err.field_path}\n"
            f"    Category: {err.category.value}\n"
            f"    Message: {err.message}"
        )
        if err.invalid_value:
            line += f"\n    Invalid value: {err.invalid_value}"
        if err.expected_format:
            line += f"\n    Expected format: {err.expected_format}"
        error_lines.append(line)

    errors_text = "\n".join(error_lines)
    return (
        f"The following resume JSON failed validation. Fix ONLY the listed errors "
        f"and return a corrected resume. Do not change any other fields.\n\n"
        f"ORIGINAL RESUME:\n{resume_json}\n\n"
        f"VALIDATION ERRORS TO FIX:\n{errors_text}\n\n"
        "Return the corrected resume as a JSON object matching the Resume schema."
    )


def correct_pair(
    pair: ResumeJobPair,
    validation_result: ValidationResult,
    settings: Settings | None = None,
    client: instructor.Instructor | None = None,
) -> tuple[ResumeJobPair, ValidationResult, int]:
    """Attempt to correct a failing pair via LLM re-generation.

    Returns (corrected_pair, final_validation_result, attempts_used).
    If all retries fail, returns the last pair state and its validation result.
    """
    s = settings or get_settings()
    ic = client or get_instructor_client(s)
    current_pair = pair
    current_validation = validation_result

    for attempt in range(1, s.max_correction_retries + 1):
        if current_validation.is_valid:
            return current_pair, current_validation, attempt - 1

        resume_json = current_pair.resume.model_dump_json(indent=2)
        prompt = _build_correction_prompt(resume_json, current_validation)

        try:
            corrected_resume: Resume = ic.chat.completions.create(
                model=s.model_name,
                response_model=Resume,
                max_retries=2,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data correction assistant. Fix only the "
                        "specified validation errors in the resume JSON and return a "
                        "corrected, schema-valid resume.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            corrected_resume.metadata = ResumeMetadata(
                trace_id=str(uuid.uuid4()),
                generated_at=datetime.now(timezone.utc).isoformat(),
                prompt_template=pair.resume.metadata.prompt_template,
                fit_level=pair.resume.metadata.fit_level,
                writing_style=pair.resume.metadata.writing_style,
            )
            new_pair = current_pair.model_copy(
                update={"resume": corrected_resume}
            )
            new_pair.metadata.correction_attempts = attempt
            new_validation = validate_pair(new_pair)
            current_pair = new_pair
            current_validation = new_validation

            logger.info(
                "Correction attempt %d for pair %s: %s",
                attempt,
                pair.metadata.pair_id,
                "PASS" if new_validation.is_valid
                else f"FAIL ({new_validation.error_count} errors)",
            )
        except Exception as exc:
            logger.warning(
                "Correction attempt %d for pair %s raised: %s",
                attempt, pair.metadata.pair_id, exc,
            )
            if attempt < s.max_correction_retries:
                time.sleep(RETRY_DELAY_BASE * attempt)

    return current_pair, current_validation, s.max_correction_retries


def run_correction_loop(
    invalid_pairs: list[ResumeJobPair],
    initial_validations: dict[str, ValidationResult],
    settings: Settings | None = None,
    client: instructor.Instructor | None = None,
) -> tuple[list[ResumeJobPair], list[ResumeJobPair], CorrectionStats]:
    """Process all invalid pairs through the correction loop.

    Returns (corrected_pairs, permanently_failed_pairs, stats).
    """
    s = settings or get_settings()
    ic = client or get_instructor_client(s)
    corrected: list[ResumeJobPair] = []
    failed: list[ResumeJobPair] = []
    stats = CorrectionStats(total_pairs=len(invalid_pairs))

    for pair in invalid_pairs:
        initial_val = initial_validations.get(pair.metadata.pair_id)
        if initial_val is None:
            logger.warning("No initial validation for pair %s", pair.metadata.pair_id)
            failed.append(pair)
            stats.permanently_failed += 1
            continue

        final_pair, final_val, attempts = correct_pair(pair, initial_val, s, ic)
        count = stats.attempts_histogram.get(attempts, 0)
        stats.attempts_histogram[attempts] = count + 1

        if final_val.is_valid:
            corrected.append(final_pair)
            stats.corrected_pairs += 1
        else:
            failed.append(final_pair)
            stats.permanently_failed += 1
            for err in final_val.errors:
                stats.failure_reasons.append(f"{err.field_path}: {err.message}")

    return corrected, failed, stats
