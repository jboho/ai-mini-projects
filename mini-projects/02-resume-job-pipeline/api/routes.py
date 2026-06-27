"""API route handlers.

POST /review-resume  — label a resume-job pair; optionally run LLM judge
GET  /health         — liveness check
GET  /analysis/failure-rates — aggregate stats from latest pipeline run
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pipeline.config import get_settings
from pipeline.judge import judge_pair
from pipeline.labeler import label_pair
from pipeline.schemas import (
    FailureLabels,
    FitLevel,
    JobDescription,
    JudgeResult,
    Resume,
    WritingStyle,
)
from pipeline.schemas.pair import PairMetadata, ResumeJobPair
from pipeline.validator import validate_pair

router = APIRouter()


class ReviewRequest(BaseModel):
    resume: Resume
    job: JobDescription
    enable_judge: bool = False


class ReviewResponse(BaseModel):
    labels: FailureLabels
    validation_passed: bool
    validation_error_count: int
    judge: JudgeResult | None = None


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


@router.post("/review-resume", response_model=ReviewResponse)
def review_resume(request: ReviewRequest) -> ReviewResponse:
    pair_id = str(uuid.uuid4())
    pair = ResumeJobPair(
        resume=request.resume,
        job=request.job,
        metadata=PairMetadata(
            pair_id=pair_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            fit_level=FitLevel.PARTIAL,
            writing_style=WritingStyle.FORMAL,
        ),
    )
    validation = validate_pair(pair)
    labels = label_pair(pair)

    judge_result: JudgeResult | None = None
    if request.enable_judge:
        settings = get_settings()
        settings_with_judge = settings.model_copy(update={"enable_judge": True})
        judge_result = judge_pair(pair, settings=settings_with_judge)

    return ReviewResponse(
        labels=labels,
        validation_passed=validation.is_valid,
        validation_error_count=validation.error_count,
        judge=judge_result,
    )


@router.get("/analysis/failure-rates")
def failure_rates() -> dict:
    settings = get_settings()
    summary_path = settings.data_dir / "pipeline_summary.json"
    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No pipeline summary found. Run the pipeline first.",
        )
    return json.loads(summary_path.read_text())
