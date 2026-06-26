"""Domain models shared across services, agents, API, and CLI."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    SEARCH = "search"
    SUGGEST = "suggest"
    PLAN_SPRINT = "plan_sprint"
    WRITE = "write"
    ANALYZE = "analyze"
    CHAT = "chat"


class ExtractedEntities(BaseModel):
    issue_keys: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    issue_types: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    date_range: str | None = None


class ParsedQuery(BaseModel):
    raw_query: str
    intent: QueryIntent
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    # Single-valued filters ready to hand to IssueService.search_issues.
    structured_filters: dict = Field(default_factory=dict)


class OperationStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    DISCARDED = "discarded"


class WriteOperation(BaseModel):
    id: int | None = None
    issue_key: str
    op_type: str = "update"
    field: str
    old_value: str | None = None
    new_value: str
    status: OperationStatus = OperationStatus.PENDING
