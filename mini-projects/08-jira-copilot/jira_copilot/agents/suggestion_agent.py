"""Suggestion engine (5 suggestion types) + CrewAI agent factory.

Four of the five suggestion types are computed deterministically from similar issues
and issue context, so they are fully offline-testable. Summary improvement uses an
injectable ``llm`` callable (stubbed in tests, real OpenAI in production).
"""

from __future__ import annotations

from collections.abc import Callable

from ..schemas.responses import Suggestion, SuggestionSet
from ..services.issue_service import IssueService
from ..services.vector_store import VectorStore, build_issue_content

SUGGESTION_TYPES = ("summary", "components", "priority", "estimate", "assignee")

# Urgency signal -> weight. Higher total => higher recommended priority.
_URGENCY_WEIGHTS = {
    "data loss": 3,
    "security": 3,
    "vulnerability": 3,
    "outage": 3,
    "crash": 3,
    "corruption": 3,
    "blocker": 3,
    "critical": 2,
    "urgent": 2,
    "broken": 2,
    "regression": 2,
    "fails": 1,
    "failure": 1,
    "error": 1,
    "slow": 1,
    "leak": 1,
}
_PRIORITY_ORDER = ["Trivial", "Minor", "Major", "Critical", "Blocker"]


def score_urgency(text: str) -> int:
    lowered = (text or "").lower()
    return sum(weight for term, weight in _URGENCY_WEIGHTS.items() if term in lowered)


def urgency_to_priority(score: int) -> str:
    if score >= 5:
        return "Blocker"
    if score >= 3:
        return "Critical"
    if score >= 1:
        return "Major"
    return "Minor"


def weighted_estimate(points_and_weights: list[tuple[float, float]]) -> float | None:
    """Similarity-weighted average of neighbour story points, rounded to one decimal."""
    usable = [(p, max(w, 0.0)) for p, w in points_and_weights if p is not None]
    total_weight = sum(w for _, w in usable)
    if not usable or total_weight <= 0:
        return None
    return round(sum(p * w for p, w in usable) / total_weight, 1)


def rank_by_frequency(items: list[str], exclude: set[str] | None = None) -> list[tuple[str, int]]:
    exclude = exclude or set()
    counts: dict[str, int] = {}
    for item in items:
        if item and item not in exclude:
            counts[item] = counts.get(item, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


class SuggestionEngine:
    def __init__(
        self,
        issue_service: IssueService,
        vector_store: VectorStore,
        llm: Callable[[str], str] | None = None,
    ) -> None:
        self.issues = issue_service
        self.vs = vector_store
        self._llm = llm

    def _similar(self, issue, limit: int = 5) -> list[dict]:
        hits = self.vs.hybrid_search(build_issue_content(issue), limit=limit + 1)
        return [h for h in hits if h["key"] != issue.issue_key][:limit]

    def suggest_components(self, key: str) -> Suggestion | None:
        issue = self.issues.get_issue(key)
        if not issue:
            return None
        similar = self._similar(issue)
        current = {c.name for c in issue.components}
        comp_names: list[str] = []
        for hit in similar:
            comp_names.extend(c for c in hit["metadata"].get("components", "").split(",") if c)
        ranked = rank_by_frequency(comp_names, exclude=current)
        if not ranked:
            return None
        name, count = ranked[0]
        return Suggestion(
            type="components",
            issue_key=key,
            original=",".join(sorted(current)) or None,
            suggested=name,
            confidence=round(count / max(len(similar), 1), 2),
            rationale=f"{count}/{len(similar)} similar issues use component '{name}'",
        )

    def suggest_estimate(self, key: str) -> Suggestion | None:
        issue = self.issues.get_issue(key)
        if not issue:
            return None
        similar = self._similar(issue)
        pairs: list[tuple[float, float]] = []
        for hit in similar:
            other = self.issues.get_issue(hit["key"])
            if other and other.story_points is not None:
                pairs.append((other.story_points, hit["score"]))
        estimate = weighted_estimate(pairs)
        if estimate is None:
            return None
        return Suggestion(
            type="estimate",
            issue_key=key,
            original=str(issue.story_points) if issue.story_points is not None else None,
            suggested=str(estimate),
            confidence=round(min(1.0, len(pairs) / 3), 2),
            rationale=f"Similarity-weighted average of {len(pairs)} comparable issues",
        )

    def suggest_priority(self, key: str) -> Suggestion | None:
        issue = self.issues.get_issue(key)
        if not issue:
            return None
        comments = " ".join(c.body for c in self.issues.get_issue_comments(key))
        text = f"{issue.title} {issue.description_text} {comments}"
        score = score_urgency(text)
        for _other, link_type, direction in self.issues.get_links_with_direction(key):
            if "block" in link_type.lower() and direction == "inward":
                score += 1  # something blocks this issue -> more urgent
        suggested = urgency_to_priority(score)
        return Suggestion(
            type="priority",
            issue_key=key,
            original=issue.priority,
            suggested=suggested,
            confidence=round(min(1.0, score / 5), 2),
            rationale=f"Urgency signal score {score} from keywords and blocking links",
        )

    def suggest_assignee(self, key: str) -> Suggestion | None:
        issue = self.issues.get_issue(key)
        if not issue:
            return None
        similar = self._similar(issue)
        assignee_ids = [
            str(hit["metadata"].get("assignee_id"))
            for hit in similar
            if hit["metadata"].get("assignee_id") not in (None, -1)
        ]
        ranked = rank_by_frequency(assignee_ids)
        if not ranked:
            return None
        top_id, count = ranked[0]
        user = self.issues.get_user(int(top_id))
        name = user.username if user else f"user:{top_id}"
        return Suggestion(
            type="assignee",
            issue_key=key,
            original=str(issue.assignee_id) if issue.assignee_id is not None else None,
            suggested=name,
            confidence=round(count / max(len(similar), 1), 2),
            rationale=f"{name} worked on {count}/{len(similar)} similar issues",
        )

    def suggest_summary(self, key: str) -> Suggestion | None:
        issue = self.issues.get_issue(key)
        if not issue or self._llm is None:
            return None
        prompt = (
            "Rewrite this Jira issue title to be clear, specific, and actionable. "
            "Return only the improved title, no quotes.\n"
            f"Title: {issue.title}\n"
            f"Description: {issue.description_text[:500]}"
        )
        try:
            improved = self._llm(prompt).strip()
        except Exception:
            return None
        if not improved or improved == issue.title:
            return None
        return Suggestion(
            type="summary",
            issue_key=key,
            original=issue.title,
            suggested=improved,
            confidence=0.7,
            rationale="LLM-rewritten for clarity and actionability",
        )

    def suggest_all(self, key: str, types: list[str] | None = None) -> SuggestionSet:
        wanted = types or list(SUGGESTION_TYPES)
        dispatch = {
            "summary": self.suggest_summary,
            "components": self.suggest_components,
            "priority": self.suggest_priority,
            "estimate": self.suggest_estimate,
            "assignee": self.suggest_assignee,
        }
        suggestions = []
        for kind in wanted:
            fn = dispatch.get(kind)
            if fn is None:
                continue
            result = fn(key)
            if result is not None:
                suggestions.append(result)
        return SuggestionSet(issue_key=key, suggestions=suggestions)


def build_suggestion_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Issue Quality Advisor",
        goal="Recommend improvements to an issue: summary, components, priority, estimate, assignee.",
        backstory=(
            "You are a meticulous triage lead. You compare an issue against similar past "
            "issues and its own context to recommend concrete, confidence-scored improvements."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
