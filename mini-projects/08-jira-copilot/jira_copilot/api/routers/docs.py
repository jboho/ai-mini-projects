"""Documentation endpoints: release notes and sprint summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...agents.crew import JiraCopilotCrew
from ...schemas.requests import ReleaseNotesRequest
from ...schemas.responses import ReleaseNotes
from ..deps import get_crew

router = APIRouter(prefix="/docs", tags=["docs"])


@router.post("/release-notes", response_model=ReleaseNotes)
def release_notes(
    req: ReleaseNotesRequest, crew: JiraCopilotCrew = Depends(get_crew)
) -> ReleaseNotes:
    return crew.generate_release_notes(req.sprint_id)


@router.post("/sprint-summary")
def sprint_summary(req: ReleaseNotesRequest, crew: JiraCopilotCrew = Depends(get_crew)) -> dict:
    notes = crew.generate_release_notes(req.sprint_id)
    health = crew.planner.health(req.sprint_id)
    return {"release_notes": notes.model_dump(), "health": health.model_dump()}
