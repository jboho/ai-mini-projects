"""Context assembly engine + CrewAI agent factory."""

from __future__ import annotations

from ..schemas.responses import ChangeRef, CommentRef, IssueContext, LinkedIssueRef
from ..services.issue_service import IssueService


class ContextAssembler:
    def __init__(self, issue_service: IssueService) -> None:
        self.issues = issue_service

    def assemble(
        self, key: str, max_comments: int = 5, max_changes: int = 10
    ) -> IssueContext | None:
        issue = self.issues.get_issue(key)
        if not issue:
            return None

        linked = [
            LinkedIssueRef(
                key=other.issue_key,
                title=other.title,
                link_type=link_type,
                direction=direction,
            )
            for other, link_type, direction in self.issues.get_links_with_direction(key)
        ]
        comments = [
            CommentRef(author_id=c.author_id, body=c.body)
            for c in self.issues.get_issue_comments(key)[-max_comments:]
        ]
        changes = [
            ChangeRef(field=ch.field, old_value=ch.old_value, new_value=ch.new_value)
            for ch in self.issues.get_issue_changes(key)[-max_changes:]
        ]
        return IssueContext(
            key=issue.issue_key,
            title=issue.title,
            type=issue.type,
            status=issue.status,
            priority=issue.priority,
            story_points=issue.story_points,
            assignee_id=issue.assignee_id,
            components=[c.name for c in issue.components],
            linked_issues=linked,
            comments=comments,
            changes=changes,
        )


def build_context_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Context Assembly Expert",
        goal="Assemble the full context around an issue: links, components, comments, history.",
        backstory=(
            "You stitch together everything a developer needs to understand an issue: its "
            "linked issues and their direction, components, recent discussion, and changes."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
