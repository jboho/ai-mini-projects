"""Natural-language query parser: intent detection + entity extraction.

Issue keys are extracted deterministically by regex; intent and the remaining
entities come from an LLM with a few-shot prompt. The LLM is injected (``llm``
callable taking a prompt and returning text), so tests run offline with a stub
and a keyword heuristic provides a graceful fallback when the LLM is unavailable
or returns junk.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from ..config import get_settings
from ..schemas.domain import ExtractedEntities, ParsedQuery, QueryIntent

_ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")

# Canonicalization maps: synonym (lowercased) -> canonical TAWOS value.
_STATUS_SYNONYMS = {
    "open": "Open",
    "to do": "Open",
    "todo": "Open",
    "in progress": "In Progress",
    "in-progress": "In Progress",
    "wip": "In Progress",
    "doing": "In Progress",
    "done": "Done",
    "closed": "Closed",
    "resolved": "Resolved",
    "fixed": "Resolved",
    "reopened": "Reopened",
}
_PRIORITY_SYNONYMS = {
    "blocker": "Blocker",
    "critical": "Critical",
    "urgent": "Critical",
    "high": "Major",
    "major": "Major",
    "medium": "Major",
    "minor": "Minor",
    "low": "Minor",
    "trivial": "Trivial",
}
_TYPE_SYNONYMS = {
    "bug": "Bug",
    "bugs": "Bug",
    "defect": "Bug",
    "story": "Story",
    "stories": "Story",
    "task": "Task",
    "tasks": "Task",
    "epic": "Epic",
    "improvement": "Improvement",
    "feature": "Story",
}

# Ordered (intent, keyword) rules for the heuristic fallback; first match wins.
_INTENT_KEYWORDS: list[tuple[QueryIntent, tuple[str, ...]]] = [
    (
        QueryIntent.WRITE,
        (
            "set ",
            "change ",
            "update ",
            "assign ",
            "reassign",
            "move ",
            "mark ",
            "transition",
            "rename",
        ),
    ),
    (
        QueryIntent.PLAN_SPRINT,
        ("plan sprint", "sprint plan", "plan the sprint", "capacity", "next sprint"),
    ),
    (
        QueryIntent.SUGGEST,
        (
            "suggest",
            "recommend",
            "estimate",
            "story point",
            "improve",
            "what component",
            "who should",
        ),
    ),
    (
        QueryIntent.ANALYZE,
        (
            "velocity",
            "how many",
            "acceptance rate",
            "metrics",
            "stats",
            "trend",
            "average",
            "burndown",
        ),
    ),
    (QueryIntent.SEARCH, ("find", "show", "list", "search", "which issues", "open ", "bugs")),
]


def extract_issue_keys(text: str) -> list[str]:
    """Deterministic regex extraction of issue keys (e.g. APACHE-123), order-preserving."""
    seen: list[str] = []
    for match in _ISSUE_KEY_RE.findall(text or ""):
        if match not in seen:
            seen.append(match)
    return seen


def _canonicalize(values: list[str], mapping: dict[str, str]) -> list[str]:
    out: list[str] = []
    for value in values or []:
        canonical = mapping.get((value or "").strip().lower())
        if canonical and canonical not in out:
            out.append(canonical)
    return out


def heuristic_intent(text: str) -> QueryIntent:
    """Keyword-based intent fallback when no LLM is available."""
    lowered = f" {(text or '').lower()} "
    for intent, keywords in _INTENT_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return intent
    return QueryIntent.CHAT


def parse_llm_json(text: str) -> dict:
    """Best-effort JSON extraction from an LLM response (tolerates code fences/prose)."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


def build_structured_filters(entities: ExtractedEntities) -> dict:
    """Reduce multi-valued entities to single-valued IssueService.search_issues filters."""
    filters: dict = {}
    if entities.statuses:
        filters["status"] = entities.statuses[0]
    if entities.priorities:
        filters["priority"] = entities.priorities[0]
    if entities.issue_types:
        filters["type"] = entities.issue_types[0]
    if entities.projects:
        filters["project_key"] = entities.projects[0]
    return filters


_FEW_SHOT_PROMPT = """You parse Jira-style natural-language queries into structured JSON.

Return ONLY a JSON object with these fields:
- intent: one of "search", "suggest", "plan_sprint", "write", "analyze", "chat"
- projects: list of project keys/names mentioned
- statuses: list of status words (open, in progress, done, closed, resolved)
- priorities: list of priority words (blocker, critical, major, minor, trivial)
- issue_types: list of types (bug, story, task, epic, improvement)
- assignees: list of person names mentioned
- date_range: a short phrase like "last 2 sprints" or null

Intent guide:
- search: finding/listing/showing issues
- suggest: asking for recommendations (components, priority, estimate, assignee, summary)
- plan_sprint: sprint planning, capacity, what to pull into a sprint
- write: changing an issue (set/update/assign/move/transition)
- analyze: metrics, velocity, acceptance rates, counts, trends
- chat: general conversation not covered above

Examples:
Q: "find open critical bugs in APACHE"
A: {"intent":"search","projects":["APACHE"],"statuses":["open"],"priorities":["critical"],"issue_types":["bug"],"assignees":[],"date_range":null}
Q: "suggest a story point estimate for APACHE-3"
A: {"intent":"suggest","projects":[],"statuses":[],"priorities":[],"issue_types":[],"assignees":[],"date_range":null}
Q: "what's the velocity for APACHE over the last 5 sprints"
A: {"intent":"analyze","projects":["APACHE"],"statuses":[],"priorities":[],"issue_types":[],"assignees":[],"date_range":"last 5 sprints"}
Q: "plan the next sprint for APACHE with capacity 40"
A: {"intent":"plan_sprint","projects":["APACHE"],"statuses":[],"priorities":[],"issue_types":[],"assignees":[],"date_range":null}
Q: "assign APACHE-5 to alice"
A: {"intent":"write","projects":[],"statuses":[],"priorities":[],"issue_types":[],"assignees":["alice"],"date_range":null}
Q: "show me bob's in progress stories"
A: {"intent":"search","projects":[],"statuses":["in progress"],"priorities":[],"issue_types":["story"],"assignees":["bob"],"date_range":null}

Q: "{query}"
A:"""


def _openai_llm(prompt: str) -> str:
    """Plain-text LLM call, reused for parsing (JSON elicited by prompt), summaries,
    and release notes. No forced ``response_format`` so it works for free-text outputs;
    ``parse_llm_json`` tolerantly extracts JSON from parser responses."""
    from openai import OpenAI

    settings = get_settings()
    kwargs: dict = {"api_key": settings.openai_api_key or None}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=settings.model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content or ""


class QueryParser:
    def __init__(self, llm: Callable[[str], str] | None = None) -> None:
        self._llm = llm

    def parse_query(self, text: str) -> ParsedQuery:
        regex_keys = extract_issue_keys(text)
        data = self._call_llm(text)

        if data:
            intent = self._coerce_intent(data.get("intent"), text)
            entities = ExtractedEntities(
                issue_keys=regex_keys,
                projects=[p for p in data.get("projects", []) if p],
                statuses=_canonicalize(data.get("statuses", []), _STATUS_SYNONYMS),
                priorities=_canonicalize(data.get("priorities", []), _PRIORITY_SYNONYMS),
                issue_types=_canonicalize(data.get("issue_types", []), _TYPE_SYNONYMS),
                assignees=[a for a in data.get("assignees", []) if a],
                date_range=data.get("date_range") or None,
            )
        else:
            intent = heuristic_intent(text)
            entities = ExtractedEntities(issue_keys=regex_keys)

        return ParsedQuery(
            raw_query=text,
            intent=intent,
            entities=entities,
            structured_filters=build_structured_filters(entities),
        )

    def _call_llm(self, text: str) -> dict:
        llm = self._llm
        if llm is None:
            if not get_settings().openai_api_key:
                return {}
            llm = _openai_llm
        try:
            raw = llm(_FEW_SHOT_PROMPT.replace("{query}", text))
        except Exception:
            return {}
        return parse_llm_json(raw)

    @staticmethod
    def _coerce_intent(value, text: str) -> QueryIntent:
        try:
            return QueryIntent(str(value).strip().lower())
        except ValueError:
            return heuristic_intent(text)
