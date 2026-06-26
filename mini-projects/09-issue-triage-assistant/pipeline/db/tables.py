"""SQLAlchemy 2.0 ORM models -- the 10 triage tables."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class JiraIssue(Base):
    __tablename__ = "jira_issues"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    issuetype: Mapped[str] = mapped_column(String(32), default="Bug")
    priority: Mapped[str] = mapped_column(String(32), default="Major")
    status: Mapped[str] = mapped_column(String(32), default="Open", index=True)
    resolution: Mapped[str] = mapped_column(String(64), default="")
    project_key: Mapped[str] = mapped_column(String(32), index=True)
    components: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, index=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    classification: Mapped[str] = mapped_column(String(32), default="", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    comments: Mapped[list[IssueComment]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    transitions: Mapped[list[StatusTransition]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )


class IssueComment(Base):
    __tablename__ = "issue_comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_key: Mapped[str] = mapped_column(ForeignKey("jira_issues.key"), index=True)
    author: Mapped[str] = mapped_column(String(128), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    contains_error: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_stacktrace: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_fix: Mapped[bool] = mapped_column(Boolean, default=False)

    issue: Mapped[JiraIssue] = relationship(back_populates="comments")


class StatusTransition(Base):
    __tablename__ = "status_transitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_key: Mapped[str] = mapped_column(ForeignKey("jira_issues.key"), index=True)
    field: Mapped[str] = mapped_column(String(64), default="status")
    from_value: Mapped[str] = mapped_column(String(128), default="")
    to_value: Mapped[str] = mapped_column(String(128), default="")
    author: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)

    issue: Mapped[JiraIssue] = relationship(back_populates="transitions")


class IssueLink(Base):
    __tablename__ = "issue_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(ForeignKey("jira_issues.key"), index=True)
    target_key: Mapped[str] = mapped_column(String(64), index=True)
    link_type: Mapped[str] = mapped_column(String(64), default="relates to")
    target_status: Mapped[str] = mapped_column(String(32), default="")


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    source_project: Mapped[str] = mapped_column(String(32), default="", index=True)
    root_cause: Mapped[str] = mapped_column(Text, default="")
    classification: Mapped[str] = mapped_column(String(32), default="")
    error_signature: Mapped[str] = mapped_column(String(64), default="", index=True)
    jira_issue_key: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    resolutions: Mapped[list[Resolution]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class Resolution(Base):
    __tablename__ = "resolutions"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    based_on_issues: Mapped[str] = mapped_column(Text, default="")

    incident: Mapped[Incident] = relationship(back_populates="resolutions")
    actions: Mapped[list[ResolutionAction]] = relationship(
        back_populates="resolution", cascade="all, delete-orphan"
    )


class ResolutionAction(Base):
    __tablename__ = "resolution_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    resolution_id: Mapped[int] = mapped_column(ForeignKey("resolutions.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(64), default="add_comment")
    impact_level: Mapped[str] = mapped_column(String(16), default="LOW")
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    approved_by: Mapped[str] = mapped_column(String(128), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    executed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    resolution: Mapped[Resolution] = relationship(back_populates="actions")


class ErrorSignature(Base):
    __tablename__ = "error_signatures"
    id: Mapped[int] = mapped_column(primary_key=True)
    signature_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    pattern: Mapped[str] = mapped_column(Text, default="")
    classification: Mapped[str] = mapped_column(String(32), default="")
    known_cause: Mapped[str] = mapped_column(Text, default="")
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    first_issue_key: Mapped[str] = mapped_column(String(64), default="")


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    entry_type: Mapped[str] = mapped_column(String(32), default="resolution")
    category: Mapped[str] = mapped_column(String(32), default="other", index=True)
    error_patterns: Mapped[str] = mapped_column(Text, default="")
    source_issue_key: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    report_type: Mapped[str] = mapped_column(String(32), default="daily")
    title: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    project_key: Mapped[str] = mapped_column(String(32), default="")
    period_start: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
