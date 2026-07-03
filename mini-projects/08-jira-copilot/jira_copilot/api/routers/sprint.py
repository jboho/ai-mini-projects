"""Sprint endpoints: plan, health, issues, velocity, recommendations."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...agents.crew import JiraCopilotCrew
from ...schemas.requests import SprintPlanRequest
from ...schemas.responses import RecommendedIssue, SprintHealth, SprintPlan, VelocityPoint
from ...services.issue_service import IssueService
from ..deps import get_crew, get_issue_service

router = APIRouter(tags=["sprint"])


@router.post("/sprint/plan", response_model=SprintPlan)
def plan_sprint(req: SprintPlanRequest, crew: JiraCopilotCrew = Depends(get_crew)) -> SprintPlan:
    return crew.plan_sprint(
        req.project_key,
        capacity=req.capacity,
        team_size=req.team_size,
        points_per_person=req.points_per_person,
        availability=req.availability,
        n_sprints=req.n_sprints,
    )


@router.get("/sprint/{sprint_id}/health", response_model=SprintHealth)
def sprint_health(sprint_id: int, crew: JiraCopilotCrew = Depends(get_crew)) -> SprintHealth:
    return crew.planner.health(sprint_id)


@router.get("/sprint/{sprint_id}/issues")
def sprint_issues(sprint_id: int, svc: IssueService = Depends(get_issue_service)) -> list[dict]:
    return [
        {"key": i.issue_key, "title": i.title, "status": i.status, "story_points": i.story_points}
        for i in svc.get_sprint_issues(sprint_id)
    ]


@router.get("/sprint/{sprint_id}/recommendations", response_model=list[RecommendedIssue])
def sprint_recommendations(
    sprint_id: int,
    project_key: str,
    crew: JiraCopilotCrew = Depends(get_crew),
) -> list[RecommendedIssue]:
    return crew.plan_sprint(project_key).recommended


@router.get("/velocity/{project_key}", response_model=list[VelocityPoint])
def velocity(
    project_key: str, n_sprints: int = 5, crew: JiraCopilotCrew = Depends(get_crew)
) -> list[VelocityPoint]:
    return crew.planner.velocity(project_key, n_sprints)
