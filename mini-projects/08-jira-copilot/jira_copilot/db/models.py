"""SQLAlchemy ORM models mirroring the core TAWOS schema."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


issue_components = Table(
    "issue_components",
    Base.metadata,
    Column("issue_id", ForeignKey("issues.id"), primary_key=True),
    Column("component_id", ForeignKey("components.id"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(255), default="")


class Sprint(Base):
    __tablename__ = "sprints"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(255), default="")
    state: Mapped[str] = mapped_column(String(32), default="future")
    start_date: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    end_date: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    completed_date: Mapped[datetime.datetime | None] = mapped_column(DateTime)


class Component(Base):
    __tablename__ = "components"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(255), default="")


class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String(32), default="Task")
    status: Mapped[str] = mapped_column(String(32), default="Open", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="Major")
    title: Mapped[str] = mapped_column(Text, default="")
    description_text: Mapped[str] = mapped_column(Text, default="")
    story_points: Mapped[float | None] = mapped_column(Float)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id"), index=True)
    created: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    resolved: Mapped[datetime.datetime | None] = mapped_column(DateTime)

    project: Mapped[Project | None] = relationship()
    sprint: Mapped[Sprint | None] = relationship()
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    components: Mapped[list[Component]] = relationship(secondary=issue_components)
    comments: Mapped[list[Comment]] = relationship(back_populates="issue")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[datetime.datetime | None] = mapped_column(DateTime)
    issue: Mapped[Issue] = relationship(back_populates="comments")


class ChangeLog(Base):
    __tablename__ = "changelogs"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    field: Mapped[str] = mapped_column(String(64), default="")
    old_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[datetime.datetime | None] = mapped_column(DateTime)


class IssueLink(Base):
    __tablename__ = "issue_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    target_issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    link_type: Mapped[str] = mapped_column(String(64), default="relates to")


class PendingOperation(Base):
    __tablename__ = "pending_operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_key: Mapped[str] = mapped_column(String(64), index=True)
    op_type: Mapped[str] = mapped_column(String(32), default="update")
    field: Mapped[str] = mapped_column(String(64), default="")
    old_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class SuggestionLog(Base):
    __tablename__ = "suggestions"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    issue_key: Mapped[str] = mapped_column(String(64), index=True)
    original: Mapped[str] = mapped_column(Text, default="")
    suggested: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class FeedbackLog(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    suggestion_id: Mapped[int] = mapped_column(ForeignKey("suggestions.id"), index=True)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    modified: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
