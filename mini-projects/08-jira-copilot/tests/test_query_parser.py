"""Tests for the NL query parser: regex extraction, heuristics, LLM merge."""

from __future__ import annotations

import json

from jira_copilot.schemas.domain import ExtractedEntities, QueryIntent
from jira_copilot.services.query_parser import (
    QueryParser,
    build_structured_filters,
    extract_issue_keys,
    heuristic_intent,
    parse_llm_json,
)


def test_extract_issue_keys():
    keys = extract_issue_keys("APACHE-3 relates to APACHE-12 and APACHE-3 again")
    assert keys == ["APACHE-3", "APACHE-12"]  # deduped, order-preserved
    assert extract_issue_keys("no keys here") == []
    assert extract_issue_keys("lowercase abc-3 is ignored") == []


def test_heuristic_intent():
    assert heuristic_intent("find open bugs in APACHE") == QueryIntent.SEARCH
    assert heuristic_intent("suggest a component for APACHE-3") == QueryIntent.SUGGEST
    assert heuristic_intent("plan the next sprint") == QueryIntent.PLAN_SPRINT
    assert heuristic_intent("assign APACHE-5 to alice") == QueryIntent.WRITE
    assert heuristic_intent("what is the velocity for APACHE") == QueryIntent.ANALYZE
    assert heuristic_intent("hello there") == QueryIntent.CHAT


def test_parse_llm_json_tolerates_fences_and_prose():
    assert parse_llm_json('{"intent":"search"}') == {"intent": "search"}
    assert parse_llm_json('```json\n{"intent":"search"}\n```') == {"intent": "search"}
    assert parse_llm_json('Here you go: {"intent": "chat"} done') == {"intent": "chat"}
    assert parse_llm_json("not json at all") == {}


def test_build_structured_filters_takes_first_of_each():
    entities = ExtractedEntities(
        statuses=["Open"], priorities=["Critical"], issue_types=["Bug"], projects=["APACHE"]
    )
    filters = build_structured_filters(entities)
    assert filters == {
        "status": "Open",
        "priority": "Critical",
        "type": "Bug",
        "project_key": "APACHE",
    }


def _stub_llm(payload: dict):
    return lambda prompt: json.dumps(payload)


def test_parse_query_merges_regex_keys_and_canonicalizes():
    parser = QueryParser(
        llm=_stub_llm(
            {
                "intent": "search",
                "projects": ["APACHE"],
                "statuses": ["open"],
                "priorities": ["high"],  # -> Major
                "issue_types": ["bugs"],  # -> Bug
                "assignees": ["bob"],
            }
        )
    )
    result = parser.parse_query("find APACHE-3 open high bugs for bob in APACHE")
    assert result.intent == QueryIntent.SEARCH
    assert result.entities.issue_keys == ["APACHE-3"]
    assert result.entities.statuses == ["Open"]
    assert result.entities.priorities == ["Major"]
    assert result.entities.issue_types == ["Bug"]
    assert result.entities.assignees == ["bob"]
    assert result.structured_filters["status"] == "Open"
    assert result.structured_filters["priority"] == "Major"


def test_parse_query_falls_back_to_heuristic_on_llm_failure():
    def broken_llm(_prompt):
        raise RuntimeError("LLM down")

    parser = QueryParser(llm=broken_llm)
    result = parser.parse_query("find open bugs in APACHE-9")
    assert result.intent == QueryIntent.SEARCH  # heuristic
    assert result.entities.issue_keys == ["APACHE-9"]  # regex still works


def test_parse_query_coerces_invalid_intent():
    parser = QueryParser(llm=_stub_llm({"intent": "nonsense"}))
    result = parser.parse_query("plan the next sprint for APACHE")
    assert result.intent == QueryIntent.PLAN_SPRINT  # coerced via heuristic


def test_parse_query_empty_llm_uses_heuristic():
    parser = QueryParser(llm=lambda _p: "")
    result = parser.parse_query("show me critical bugs")
    assert result.intent == QueryIntent.SEARCH
