"""Issue endpoints: detail, search, comments, links, changes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...services.issue_service import IssueService
from ..deps import get_issue_service

router = APIRouter(prefix="/issues", tags=["issues"])


def _issue_dict(issue) -> dict:
    return {
        "key": issue.issue_key,
        "type": issue.type,
        "status": issue.status,
        "priority": issue.priority,
        "title": issue.title,
        "description": issue.description_text,
        "story_points": issue.story_points,
        "assignee_id": issue.assignee_id,
        "sprint_id": issue.sprint_id,
        "components": [c.name for c in issue.components],
    }


# Declared before /{key} so "search" is not captured as a key.
@router.get("/search")
def search_issues(
    status: str | None = None,
    type: str | None = None,
    priority: str | None = None,
    project_key: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    svc: IssueService = Depends(get_issue_service),
) -> list[dict]:
    issues = svc.search_issues(
        status=status, type=type, priority=priority, project_key=project_key, limit=limit
    )
    return [_issue_dict(i) for i in issues]


@router.get("/{key}")
def get_issue(key: str, svc: IssueService = Depends(get_issue_service)) -> dict:
    issue = svc.get_issue(key)
    if issue is None:
        raise HTTPException(status_code=404, detail=f"Issue {key} not found")
    return _issue_dict(issue)


@router.get("/{key}/comments")
def get_comments(key: str, svc: IssueService = Depends(get_issue_service)) -> list[dict]:
    return [{"author_id": c.author_id, "body": c.body} for c in svc.get_issue_comments(key)]


@router.get("/{key}/links")
def get_links(key: str, svc: IssueService = Depends(get_issue_service)) -> list[dict]:
    return [
        {"key": other.issue_key, "title": other.title, "link_type": lt, "direction": direction}
        for other, lt, direction in svc.get_links_with_direction(key)
    ]


@router.get("/{key}/changes")
def get_changes(key: str, svc: IssueService = Depends(get_issue_service)) -> list[dict]:
    return [
        {"field": ch.field, "old_value": ch.old_value, "new_value": ch.new_value}
        for ch in svc.get_issue_changes(key)
    ]
