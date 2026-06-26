"""Analytics endpoints: acceptance rates, suggestion history, feedback, metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...schemas.requests import FeedbackRequest
from ...services.analytics import Analytics
from ..deps import get_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/acceptance")
def acceptance(by_type: bool = True, analytics: Analytics = Depends(get_analytics)) -> dict:
    return analytics.get_acceptance_rates(by_type=by_type)


@router.get("/suggestions")
def suggestions(
    issue_key: str | None = None,
    type: str | None = None,
    analytics: Analytics = Depends(get_analytics),
) -> list[dict]:
    return analytics.get_suggestion_history(issue_key=issue_key, type=type)


@router.post("/feedback")
def feedback(req: FeedbackRequest, analytics: Analytics = Depends(get_analytics)) -> dict:
    try:
        feedback_id = analytics.record_feedback(
            req.suggestion_id, accepted=req.accepted, reason=req.reason, modified=req.modified
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"feedback_id": feedback_id}


@router.get("/metrics")
def metrics(analytics: Analytics = Depends(get_analytics)) -> dict:
    return analytics.get_quality_metrics()
