"""Suggestion endpoints: full set and per-type. Suggestions are logged to analytics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...agents.crew import JiraCopilotCrew
from ...schemas.requests import SuggestRequest
from ...schemas.responses import Suggestion, SuggestionSet
from ...services.analytics import Analytics
from ..deps import get_analytics, get_crew

router = APIRouter(prefix="/suggest", tags=["suggestions"])


def _one(key: str, kind: str, crew: JiraCopilotCrew, analytics: Analytics) -> Suggestion:
    result = crew.suggest(key, types=[kind])
    if not result.suggestions:
        raise HTTPException(status_code=404, detail=f"No {kind} suggestion for {key}")
    suggestion = result.suggestions[0]
    analytics.log_suggestion(suggestion)
    return suggestion


@router.post("/{key}", response_model=SuggestionSet)
def suggest_all(
    key: str,
    req: SuggestRequest | None = None,
    crew: JiraCopilotCrew = Depends(get_crew),
    analytics: Analytics = Depends(get_analytics),
) -> SuggestionSet:
    types = req.types if req else None
    result = crew.suggest(key, types=types)
    for suggestion in result.suggestions:
        analytics.log_suggestion(suggestion)
    return result


@router.post("/{key}/summary", response_model=Suggestion)
def suggest_summary(
    key: str,
    crew: JiraCopilotCrew = Depends(get_crew),
    analytics: Analytics = Depends(get_analytics),
) -> Suggestion:
    return _one(key, "summary", crew, analytics)


@router.post("/{key}/components", response_model=Suggestion)
def suggest_components(
    key: str,
    crew: JiraCopilotCrew = Depends(get_crew),
    analytics: Analytics = Depends(get_analytics),
) -> Suggestion:
    return _one(key, "components", crew, analytics)


@router.post("/{key}/priority", response_model=Suggestion)
def suggest_priority(
    key: str,
    crew: JiraCopilotCrew = Depends(get_crew),
    analytics: Analytics = Depends(get_analytics),
) -> Suggestion:
    return _one(key, "priority", crew, analytics)


@router.post("/{key}/estimate", response_model=Suggestion)
def suggest_estimate(
    key: str,
    crew: JiraCopilotCrew = Depends(get_crew),
    analytics: Analytics = Depends(get_analytics),
) -> Suggestion:
    return _one(key, "estimate", crew, analytics)


@router.post("/{key}/assignee", response_model=Suggestion)
def suggest_assignee(
    key: str,
    crew: JiraCopilotCrew = Depends(get_crew),
    analytics: Analytics = Depends(get_analytics),
) -> Suggestion:
    return _one(key, "assignee", crew, analytics)
