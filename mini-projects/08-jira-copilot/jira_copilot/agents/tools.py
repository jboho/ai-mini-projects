"""CrewAI tool wrappers around the deterministic engines.

``build_tools`` returns CrewAI tools bound (via closure) to live engine instances, so
the agents can call into hybrid search, context assembly, suggestions, and planning.
"""

from __future__ import annotations

import json


def build_tools(retrieval, context, suggestion, planner) -> list:
    from crewai.tools import tool

    @tool("search_issues")
    def search_issues_tool(query: str) -> str:
        """Search the issue tracker by natural language. Returns top issues as JSON."""
        items = retrieval.search(query, limit=5)
        return json.dumps([i.model_dump() for i in items])

    @tool("get_issue_context")
    def get_issue_context_tool(issue_key: str) -> str:
        """Get full context for an issue key (links, components, comments) as JSON."""
        ctx = context.assemble(issue_key)
        return ctx.model_dump_json() if ctx else "{}"

    @tool("suggest_improvements")
    def suggest_improvements_tool(issue_key: str) -> str:
        """Get improvement suggestions (components/priority/estimate/assignee) for an issue key."""
        return suggestion.suggest_all(issue_key).model_dump_json()

    @tool("get_velocity")
    def get_velocity_tool(project_key: str) -> str:
        """Get recent sprint velocity for a project key as JSON."""
        return json.dumps([v.model_dump() for v in planner.velocity(project_key)])

    @tool("plan_sprint")
    def plan_sprint_tool(project_key: str) -> str:
        """Plan a sprint for a project key within historical capacity. Returns JSON."""
        return planner.plan(project_key).model_dump_json()

    return [
        search_issues_tool,
        get_issue_context_tool,
        suggest_improvements_tool,
        get_velocity_tool,
        plan_sprint_tool,
    ]
