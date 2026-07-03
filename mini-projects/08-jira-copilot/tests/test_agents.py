"""Offline tests for the agent engines and deterministic crew pipelines."""

from __future__ import annotations

import pytest

from jira_copilot.agents.context_agent import ContextAssembler
from jira_copilot.agents.crew import JiraCopilotCrew
from jira_copilot.agents.documentation_agent import (
    ReleaseNotesWriter,
    group_by_section,
    render_markdown,
)
from jira_copilot.agents.retrieval_agent import RetrievalEngine
from jira_copilot.agents.sprint_planner_agent import (
    SprintPlanner,
    average,
    compute_capacity,
    priority_sort_key,
)
from jira_copilot.agents.suggestion_agent import (
    SuggestionEngine,
    rank_by_frequency,
    score_urgency,
    urgency_to_priority,
    weighted_estimate,
)
from jira_copilot.services.issue_service import IssueService


# --- Pure helpers ---


def test_score_urgency_and_priority():
    assert score_urgency("App crash with data loss") >= 5
    assert urgency_to_priority(score_urgency("App crash with data loss")) == "Blocker"
    assert urgency_to_priority(0) == "Minor"
    assert urgency_to_priority(2) == "Major"


def test_weighted_estimate():
    assert weighted_estimate([]) is None
    assert weighted_estimate([(None, 1.0)]) is None
    # weighted toward the higher-similarity neighbour
    assert weighted_estimate([(2.0, 0.0), (8.0, 1.0)]) == 8.0
    assert weighted_estimate([(2.0, 1.0), (4.0, 1.0)]) == 3.0


def test_rank_by_frequency():
    ranked = rank_by_frequency(["a", "b", "a", "c", "b", "a"], exclude={"c"})
    assert ranked == [("a", 3), ("b", 2)]


def test_compute_capacity_and_average():
    assert compute_capacity(5, 8) == 40.0
    assert compute_capacity(5, 8, 0.5) == 20.0
    assert compute_capacity(5, 8, 2.0) == 40.0  # availability clamped to 1.0
    assert average([10, 20]) == 15.0
    assert average([]) == 0.0


def test_priority_sort_key_orders_high_priority_small_first():
    items = [("Minor", 1.0), ("Blocker", 8.0), ("Major", 2.0)]
    ordered = sorted(items, key=lambda x: priority_sort_key(*x))
    assert [p for p, _ in ordered] == ["Blocker", "Major", "Minor"]


def test_group_and_render_release_notes(session):
    issues = IssueService(session).get_sprint_issues(1)  # two closed bugs
    sections = group_by_section(issues)
    assert "Bug Fixes" in sections and len(sections["Bug Fixes"]) == 2
    md = render_markdown("Notes", sections, summary="A summary.")
    assert "## Bug Fixes" in md and "A summary." in md


# --- Engines ---


@pytest.fixture
def engines(session, vector_store):
    svc = IssueService(session)
    return {
        "retrieval": RetrievalEngine(svc, vector_store),
        "context": ContextAssembler(svc),
        "planner": SprintPlanner(svc),
        "docs": ReleaseNotesWriter(svc),
        "suggestion": SuggestionEngine(svc, vector_store),
    }


def test_retrieval_enriches_hits(engines):
    items = engines["retrieval"].search("oauth login", limit=3)
    assert items[0].key == "APACHE-3"
    assert items[0].title == "Add OAuth login"
    assert items[0].status == "In Progress"


def test_context_assembly_links_direction(engines):
    ctx = engines["context"].assemble("APACHE-4")
    assert ctx is not None
    assert ctx.components == ["storage"]
    blocking = [link for link in ctx.linked_issues if link.link_type == "blocks"]
    assert blocking and blocking[0].key == "APACHE-3" and blocking[0].direction == "inward"
    assert engines["context"].assemble("NOPE-1") is None


def test_suggest_priority_from_keywords(engines):
    s = engines["suggestion"].suggest_priority("APACHE-5")  # "Data loss on sync"
    assert s.suggested == "Critical"
    assert s.original == "Critical"


def test_suggest_priority_from_blocking_link(engines):
    s = engines["suggestion"].suggest_priority("APACHE-4")  # blocked by APACHE-3
    assert s.suggested == "Major"  # no urgency words, +1 from inward block


def test_suggest_estimate_and_components_and_assignee(engines):
    eng = engines["suggestion"]
    est = eng.suggest_estimate("APACHE-5")
    assert est is not None and float(est.suggested) > 0

    comp = eng.suggest_components("APACHE-5")
    assert comp is not None and comp.suggested not in {"storage"}  # excludes current

    assignee = eng.suggest_assignee("APACHE-5")
    assert assignee is not None and assignee.suggested in {"alice", "bob", "carol"}


def test_suggest_summary_uses_llm(session, vector_store):
    svc = IssueService(session)
    eng = SuggestionEngine(svc, vector_store, llm=lambda _p: "Fix null pointer crash on startup")
    s = eng.suggest_summary("APACHE-1")
    assert s is not None and s.type == "summary"
    assert s.suggested == "Fix null pointer crash on startup"
    assert s.original == "App crashes on startup"


def test_suggest_all_without_llm_skips_summary(engines):
    result = engines["suggestion"].suggest_all("APACHE-5")
    types = {s.type for s in result.suggestions}
    assert "summary" not in types  # no llm
    assert {"priority", "estimate"} <= types


def test_sprint_health(engines):
    health = engines["planner"].health(1)  # Sprint 1: APACHE-1, -2, -6
    assert health.total_issues == 3
    assert health.total_points == 13.0
    assert health.unestimated_pct == 0.0


def test_sprint_plan_fits_capacity(engines):
    plan = engines["planner"].plan("APACHE")
    assert plan.average_velocity == 13.0
    assert plan.capacity == 13.0
    keys = [r.key for r in plan.recommended]
    assert keys[0] == "APACHE-5"  # Critical before Minor
    assert set(keys) == {"APACHE-4", "APACHE-5"}
    assert plan.total_points == 7.0


def test_velocity(engines):
    vel = engines["planner"].velocity("APACHE")
    assert len(vel) == 1 and vel[0].completed_points == 13.0


def test_release_notes_features_section(engines):
    notes = engines["docs"].generate(1)  # Sprint 1: APACHE-6 closed Story + 2 closed bugs
    assert "Features" in notes.sections
    assert any("APACHE-6" in line for line in notes.sections["Features"])
    assert "Bug Fixes" in notes.sections
    assert "## Features" in notes.markdown


# --- Crew dispatch (deterministic, offline) ---


def test_crew_chat_routes_suggest(session, vector_store):
    crew = JiraCopilotCrew(session, vector_store)  # no llm -> heuristic routing
    out = crew.chat("suggest improvements for APACHE-5")
    assert out["intent"] == "suggest"
    assert out["result"]["issue_key"] == "APACHE-5"


def test_crew_chat_routes_search(session, vector_store):
    crew = JiraCopilotCrew(session, vector_store)
    out = crew.chat("find issues about oauth login")
    assert out["intent"] in {"search", "chat"}
    assert isinstance(out["result"], list)
    assert any(r["key"] == "APACHE-3" for r in out["result"])
