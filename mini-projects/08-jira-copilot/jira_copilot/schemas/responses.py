"""Structured response models produced by the agent engines (and reused by API/CLI)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    key: str
    title: str = ""
    type: str = ""
    status: str = ""
    priority: str = ""
    score: float = 0.0
    semantic_score: float = 0.0
    keyword_score: float = 0.0


class LinkedIssueRef(BaseModel):
    key: str
    title: str = ""
    link_type: str = ""
    direction: str = "outward"  # outward = this issue -> other; inward = other -> this


class CommentRef(BaseModel):
    author_id: int | None = None
    body: str = ""


class ChangeRef(BaseModel):
    field: str = ""
    old_value: str = ""
    new_value: str = ""


class IssueContext(BaseModel):
    key: str
    title: str = ""
    type: str = ""
    status: str = ""
    priority: str = ""
    story_points: float | None = None
    assignee_id: int | None = None
    components: list[str] = Field(default_factory=list)
    linked_issues: list[LinkedIssueRef] = Field(default_factory=list)
    comments: list[CommentRef] = Field(default_factory=list)
    changes: list[ChangeRef] = Field(default_factory=list)


class Suggestion(BaseModel):
    type: str  # summary | components | priority | estimate | assignee
    issue_key: str
    original: str | None = None
    suggested: str
    confidence: float = 0.0
    rationale: str = ""


class SuggestionSet(BaseModel):
    issue_key: str
    suggestions: list[Suggestion] = Field(default_factory=list)


class VelocityPoint(BaseModel):
    sprint_id: int
    sprint_name: str = ""
    completed_points: float = 0.0


class SprintHealth(BaseModel):
    sprint_id: int
    total_issues: int = 0
    total_points: float = 0.0
    blocked_pct: float = 0.0
    unestimated_pct: float = 0.0
    assignee_load: dict[str, int] = Field(default_factory=dict)


class RecommendedIssue(BaseModel):
    key: str
    title: str = ""
    priority: str = ""
    story_points: float | None = None


class SprintPlan(BaseModel):
    project_key: str
    capacity: float
    average_velocity: float = 0.0
    total_points: float = 0.0
    recommended: list[RecommendedIssue] = Field(default_factory=list)


class ReleaseNotes(BaseModel):
    title: str
    sections: dict[str, list[str]] = Field(default_factory=dict)
    markdown: str = ""
