"""Sprint planning engine + CrewAI agent factory."""

from __future__ import annotations

from ..schemas.responses import RecommendedIssue, SprintHealth, SprintPlan, VelocityPoint
from ..services.issue_service import IssueService

_DONE_STATUSES = {"done", "closed", "resolved", "fixed"}
_OPEN_STATUSES = {"open", "to do", "todo", "reopened", "backlog"}
_PRIORITY_RANK = {"Blocker": 0, "Critical": 1, "Major": 2, "Minor": 3, "Trivial": 4}


def compute_capacity(team_size: int, points_per_person: float, availability: float = 1.0) -> float:
    """Sprint capacity in story points: team_size * points_per_person * availability."""
    return round(team_size * points_per_person * max(0.0, min(availability, 1.0)), 1)


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def priority_sort_key(priority: str, story_points: float | None) -> tuple[int, float]:
    """Higher priority first, then smaller stories first (quick wins)."""
    return (_PRIORITY_RANK.get(priority, 99), story_points if story_points is not None else 1e9)


class SprintPlanner:
    def __init__(self, issue_service: IssueService) -> None:
        self.issues = issue_service

    def velocity(self, project_key: str, n_sprints: int = 5) -> list[VelocityPoint]:
        return [
            VelocityPoint(
                sprint_id=row["sprint_id"],
                sprint_name=row["sprint_name"],
                completed_points=row["completed_points"],
            )
            for row in self.issues.get_project_velocity(project_key, n_sprints)
        ]

    def average_velocity(self, project_key: str, n_sprints: int = 5) -> float:
        return average([v.completed_points for v in self.velocity(project_key, n_sprints)])

    def health(self, sprint_id: int) -> SprintHealth:
        issues = self.issues.get_sprint_issues(sprint_id)
        total = len(issues)
        blocked = 0
        unestimated = 0
        load: dict[str, int] = {}
        total_points = 0.0
        for issue in issues:
            total_points += issue.story_points or 0.0
            if issue.story_points is None:
                unestimated += 1
            if "block" in issue.status.lower():
                blocked += 1
            else:
                for _o, lt, direction in self.issues.get_links_with_direction(issue.issue_key):
                    if "block" in lt.lower() and direction == "inward":
                        blocked += 1
                        break
            key = str(issue.assignee_id) if issue.assignee_id is not None else "unassigned"
            load[key] = load.get(key, 0) + 1
        pct = lambda n: round(100 * n / total, 1) if total else 0.0  # noqa: E731
        return SprintHealth(
            sprint_id=sprint_id,
            total_issues=total,
            total_points=round(total_points, 1),
            blocked_pct=pct(blocked),
            unestimated_pct=pct(unestimated),
            assignee_load=load,
        )

    def plan(
        self,
        project_key: str,
        capacity: float | None = None,
        team_size: int = 5,
        points_per_person: float = 8.0,
        availability: float = 1.0,
        n_sprints: int = 5,
    ) -> SprintPlan:
        avg_velocity = self.average_velocity(project_key, n_sprints)
        if capacity is None:
            capacity = avg_velocity or compute_capacity(team_size, points_per_person, availability)

        backlog = [
            i
            for i in self.issues.search_issues(project_key=project_key, limit=500)
            if i.status.lower() in _OPEN_STATUSES
        ]
        backlog.sort(key=lambda i: priority_sort_key(i.priority, i.story_points))

        recommended: list[RecommendedIssue] = []
        total = 0.0
        for issue in backlog:
            points = issue.story_points or 0.0
            if total + points > capacity:
                continue
            recommended.append(
                RecommendedIssue(
                    key=issue.issue_key,
                    title=issue.title,
                    priority=issue.priority,
                    story_points=issue.story_points,
                )
            )
            total += points
        return SprintPlan(
            project_key=project_key,
            capacity=round(capacity, 1),
            average_velocity=avg_velocity,
            total_points=round(total, 1),
            recommended=recommended,
        )


def build_sprint_planner_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Sprint Planning Strategist",
        goal="Plan a balanced, achievable sprint within capacity and report sprint health.",
        backstory=(
            "You are a pragmatic agile lead. You size sprints against historical velocity, "
            "prioritize ruthlessly, and flag blocked or unestimated work."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
