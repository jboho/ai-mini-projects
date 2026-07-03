"""Release-notes engine + CrewAI agent factory."""

from __future__ import annotations

from collections.abc import Callable

from ..schemas.responses import ReleaseNotes
from ..services.issue_service import IssueService

_DONE_STATUSES = {"done", "closed", "resolved", "fixed"}

# Issue type -> release-notes section.
_SECTION_FOR_TYPE = {
    "Story": "Features",
    "Epic": "Features",
    "Improvement": "Improvements",
    "Bug": "Bug Fixes",
    "Task": "Improvements",
}
_SECTION_ORDER = ["Features", "Improvements", "Bug Fixes"]


def group_by_section(issues) -> dict[str, list[str]]:
    """Group completed issues into ordered release-notes sections as 'KEY: title' lines."""
    sections: dict[str, list[str]] = {name: [] for name in _SECTION_ORDER}
    for issue in issues:
        if issue.status.lower() not in _DONE_STATUSES:
            continue
        section = _SECTION_FOR_TYPE.get(issue.type, "Improvements")
        sections[section].append(f"{issue.issue_key}: {issue.title}")
    return {name: lines for name, lines in sections.items() if lines}


def render_markdown(title: str, sections: dict[str, list[str]], summary: str = "") -> str:
    parts = [f"# {title}", ""]
    if summary:
        parts += [summary, ""]
    for name in _SECTION_ORDER:
        lines = sections.get(name)
        if not lines:
            continue
        parts.append(f"## {name}")
        parts += [f"- {line}" for line in lines]
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


class ReleaseNotesWriter:
    def __init__(
        self,
        issue_service: IssueService,
        llm: Callable[[str], str] | None = None,
    ) -> None:
        self.issues = issue_service
        self._llm = llm

    def generate(self, sprint_id: int, title: str | None = None) -> ReleaseNotes:
        issues = self.issues.get_sprint_issues(sprint_id)
        sections = group_by_section(issues)
        title = title or f"Release Notes - Sprint {sprint_id}"

        summary = ""
        if self._llm is not None and sections:
            flat = "; ".join(line for lines in sections.values() for line in lines)
            prompt = (
                "Write a single concise sentence summarizing this release for stakeholders. "
                "Return only the sentence.\n"
                f"Completed work: {flat[:1500]}"
            )
            try:
                summary = self._llm(prompt).strip()
            except Exception:
                summary = ""

        return ReleaseNotes(
            title=title,
            sections=sections,
            markdown=render_markdown(title, sections, summary),
        )


def build_documentation_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Technical Writer",
        goal="Generate clear release notes from completed issues, grouped by category.",
        backstory=(
            "You turn a sprint's completed issues into polished release notes that "
            "stakeholders can read at a glance, grouped into features, improvements, and fixes."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
