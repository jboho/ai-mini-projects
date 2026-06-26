"""IssueService: read access over the TAWOS SQLite DB."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ChangeLog, Comment, Component, Issue, IssueLink, Project, Sprint, User

_DONE_STATUSES = {"done", "closed", "resolved", "fixed"}


class IssueService:
    def __init__(self, session: Session) -> None:
        self.s = session

    def get_issue(self, key: str) -> Issue | None:
        return self.s.scalar(select(Issue).where(Issue.issue_key == key))

    def search_issues(
        self,
        status: str | None = None,
        type: str | None = None,
        priority: str | None = None,
        project_key: str | None = None,
        assignee_id: int | None = None,
        limit: int = 50,
    ) -> list[Issue]:
        stmt = select(Issue)
        if status:
            stmt = stmt.where(Issue.status == status)
        if type:
            stmt = stmt.where(Issue.type == type)
        if priority:
            stmt = stmt.where(Issue.priority == priority)
        if assignee_id is not None:
            stmt = stmt.where(Issue.assignee_id == assignee_id)
        if project_key:
            proj = self.s.scalar(select(Project).where(Project.key == project_key))
            if proj:
                stmt = stmt.where(Issue.project_id == proj.id)
        return list(self.s.scalars(stmt.limit(limit)))

    def get_linked_issues(self, key: str) -> list[tuple[Issue, str]]:
        issue = self.get_issue(key)
        if not issue:
            return []
        links = self.s.scalars(
            select(IssueLink).where(
                (IssueLink.source_issue_id == issue.id) | (IssueLink.target_issue_id == issue.id)
            )
        )
        out: list[tuple[Issue, str]] = []
        for link in links:
            other_id = (
                link.target_issue_id if link.source_issue_id == issue.id else link.source_issue_id
            )
            other = self.s.get(Issue, other_id)
            if other:
                out.append((other, link.link_type))
        return out

    def get_links_with_direction(self, key: str) -> list[tuple[Issue, str, str]]:
        """Linked issues with link type and direction (outward=this->other, inward=other->this)."""
        issue = self.get_issue(key)
        if not issue:
            return []
        links = self.s.scalars(
            select(IssueLink).where(
                (IssueLink.source_issue_id == issue.id) | (IssueLink.target_issue_id == issue.id)
            )
        )
        out: list[tuple[Issue, str, str]] = []
        for link in links:
            if link.source_issue_id == issue.id:
                other = self.s.get(Issue, link.target_issue_id)
                direction = "outward"
            else:
                other = self.s.get(Issue, link.source_issue_id)
                direction = "inward"
            if other:
                out.append((other, link.link_type, direction))
        return out

    def get_issue_changes(self, key: str) -> list[ChangeLog]:
        issue = self.get_issue(key)
        if not issue:
            return []
        return list(self.s.scalars(select(ChangeLog).where(ChangeLog.issue_id == issue.id)))

    def get_user(self, user_id: int | None) -> User | None:
        if user_id is None:
            return None
        return self.s.get(User, user_id)

    def get_issue_comments(self, key: str) -> list[Comment]:
        issue = self.get_issue(key)
        if not issue:
            return []
        return list(self.s.scalars(select(Comment).where(Comment.issue_id == issue.id)))

    def get_sprint_issues(self, sprint_id: int) -> list[Issue]:
        return list(self.s.scalars(select(Issue).where(Issue.sprint_id == sprint_id)))

    def get_project_components(self, project_key: str) -> list[Component]:
        proj = self.s.scalar(select(Project).where(Project.key == project_key))
        if not proj:
            return []
        return list(self.s.scalars(select(Component).where(Component.project_id == proj.id)))

    def get_project_velocity(self, project_key: str, n_sprints: int = 5) -> list[dict]:
        proj = self.s.scalar(select(Project).where(Project.key == project_key))
        if not proj:
            return []
        sprints = self.s.scalars(
            select(Sprint)
            .where(Sprint.project_id == proj.id, Sprint.state == "closed")
            .order_by(Sprint.completed_date.desc())
            .limit(n_sprints)
        )
        velocity = []
        for sprint in sprints:
            issues = self.get_sprint_issues(sprint.id)
            completed = sum(
                (i.story_points or 0) for i in issues if i.status.lower() in _DONE_STATUSES
            )
            velocity.append(
                {"sprint_id": sprint.id, "sprint_name": sprint.name, "completed_points": completed}
            )
        return velocity
