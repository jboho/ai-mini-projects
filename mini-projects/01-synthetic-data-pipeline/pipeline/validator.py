"""Phase 2: Structural validation of generated DIY repair items."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from .models import (
    DIYRepairItem,
    GenerationMetadata,
    PipelineRecord,
    RepairCategory,
)

logger = logging.getLogger(__name__)


def validate_generation_results(
    results: list[tuple[DIYRepairItem | None, RepairCategory, list[str]]],
    *,
    prompt_version: str = "baseline",
    model_name: str = "",
) -> list[PipelineRecord]:
    """Convert raw generation results into validated PipelineRecords.

    Items that failed generation (None) are recorded with validation errors.
    Items that were returned by Instructor already passed Pydantic validation
    during generation, but we re-validate here as a safety net and to produce
    a uniform record list.
    """
    records: list[PipelineRecord] = []

    for idx, (item, category, gen_errors) in enumerate(results):
        trace_id = f"qa_{idx + 1:04d}"
        errors: list[str] = list(gen_errors)
        passed = False

        if item is None:
            errors.append("Generation produced no item")
        else:
            try:
                DIYRepairItem.model_validate(item.model_dump())
                passed = True
            except ValidationError as exc:
                for err in exc.errors():
                    field = " -> ".join(str(loc) for loc in err["loc"])
                    errors.append(f"{field}: {err['msg']}")
                item = None

        metadata = GenerationMetadata(
            trace_id=trace_id,
            category=category,
            prompt_version=prompt_version,
            passed_validation=passed,
            validation_errors=errors,
            model_name=model_name,
        )

        records.append(
            PipelineRecord(
                trace_id=trace_id,
                item=item,
                metadata=metadata,
            )
        )

        if not passed:
            logger.warning(
                "Item %s failed validation: %s", trace_id, errors
            )

    valid = sum(1 for r in records if r.metadata.passed_validation)
    total = len(records)
    rate = (valid / total * 100) if total else 0
    logger.info(
        "Validation: %d/%d passed (%.1f%%)", valid, total, rate
    )

    return records
