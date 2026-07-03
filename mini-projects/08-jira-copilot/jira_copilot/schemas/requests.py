"""Pydantic request models for the FastAPI layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str


class QueryRequest(BaseModel):
    text: str


class SearchRequest(BaseModel):
    query: str
    filters: dict | None = None
    limit: int = 10


class SuggestRequest(BaseModel):
    types: list[str] | None = None


class SprintPlanRequest(BaseModel):
    project_key: str
    capacity: float | None = None
    team_size: int = 5
    points_per_person: float = 8.0
    availability: float = 1.0
    n_sprints: int = 5


class WriteUpdateRequest(BaseModel):
    issue_key: str
    field: str
    new_value: str


class WriteBulkMoveRequest(BaseModel):
    issue_keys: list[str]
    sprint_id: int


class OperationIdsRequest(BaseModel):
    operation_ids: list[int] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    suggestion_id: int
    accepted: bool
    reason: str = ""
    modified: bool = False


class ReleaseNotesRequest(BaseModel):
    sprint_id: int
