"""Context endpoints: assembled issue context."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...agents.crew import JiraCopilotCrew
from ...schemas.responses import IssueContext
from ..deps import get_crew

router = APIRouter(prefix="/context", tags=["context"])


@router.get("/{key}", response_model=IssueContext)
def get_context(key: str, crew: JiraCopilotCrew = Depends(get_crew)) -> IssueContext:
    ctx = crew.get_context(key)
    if ctx is None:
        raise HTTPException(status_code=404, detail=f"Issue {key} not found")
    return ctx


@router.get("/{key}/deep")
def get_context_deep(key: str, crew: JiraCopilotCrew = Depends(get_crew)) -> dict:
    """Issue context plus the context of each directly-linked issue."""
    ctx = crew.get_context(key)
    if ctx is None:
        raise HTTPException(status_code=404, detail=f"Issue {key} not found")
    linked = {link.key: crew.get_context(link.key) for link in ctx.linked_issues}
    return {
        "issue": ctx.model_dump(),
        "linked": {k: (v.model_dump() if v else None) for k, v in linked.items()},
    }
