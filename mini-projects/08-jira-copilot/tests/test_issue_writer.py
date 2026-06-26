"""Tests for simulation-first write operations."""

from __future__ import annotations

import pytest

from jira_copilot.schemas.domain import OperationStatus
from jira_copilot.schemas.responses import Suggestion, SuggestionSet
from jira_copilot.services.issue_service import IssueService
from jira_copilot.services.issue_writer import IssueWriter


def test_simulate_does_not_mutate_issue(session):
    writer = IssueWriter(session)
    svc = IssueService(session)
    before = svc.get_issue("APACHE-4").priority

    op = writer.simulate_update("APACHE-4", "priority", "Critical")
    assert op.status == OperationStatus.PENDING
    assert op.old_value == before
    assert op.new_value == "Critical"
    # Issue itself is untouched
    assert svc.get_issue("APACHE-4").priority == before


def test_get_pending_lists_only_pending(session):
    writer = IssueWriter(session)
    writer.simulate_update("APACHE-4", "priority", "Critical")
    writer.simulate_update("APACHE-4", "title", "New title")
    pending = writer.get_pending()
    assert len(pending) == 2
    assert {p.field for p in pending} == {"priority", "title"}


def test_execute_applies_changes(session):
    writer = IssueWriter(session)
    svc = IssueService(session)
    op = writer.simulate_update("APACHE-4", "priority", "Critical")

    applied = writer.execute_pending([op.id])
    assert len(applied) == 1
    assert applied[0].status == OperationStatus.EXECUTED
    assert svc.get_issue("APACHE-4").priority == "Critical"
    assert writer.get_pending() == []  # no longer pending


def test_discard_removes_from_queue_without_applying(session):
    writer = IssueWriter(session)
    svc = IssueService(session)
    before = svc.get_issue("APACHE-4").priority
    op = writer.simulate_update("APACHE-4", "priority", "Blocker")

    assert writer.discard_pending([op.id]) == 1
    assert writer.get_pending() == []
    assert svc.get_issue("APACHE-4").priority == before  # unchanged


def test_execute_story_points_coercion(session):
    writer = IssueWriter(session)
    svc = IssueService(session)
    op = writer.simulate_update("APACHE-4", "story_points", "13")
    writer.execute_pending([op.id])
    assert svc.get_issue("APACHE-4").story_points == 13.0


def test_execute_assignee_by_username(session):
    writer = IssueWriter(session)
    svc = IssueService(session)
    carol = svc.get_issue("APACHE-3").assignee_id  # carol is user idx 2
    op = writer.simulate_update("APACHE-4", "assignee", "carol")
    writer.execute_pending([op.id])
    assert svc.get_issue("APACHE-4").assignee_id == carol


def test_execute_components_sets_relationship(session):
    writer = IssueWriter(session)
    svc = IssueService(session)
    op = writer.simulate_update("APACHE-4", "components", "api,ui")
    writer.execute_pending([op.id])
    names = {c.name for c in svc.get_issue("APACHE-4").components}
    assert names == {"api", "ui"}


def test_unknown_field_and_issue_raise(session):
    writer = IssueWriter(session)
    with pytest.raises(ValueError):
        writer.simulate_update("APACHE-4", "nonsense", "x")
    with pytest.raises(ValueError):
        writer.simulate_update("NOPE-1", "priority", "Critical")


def test_apply_suggestions_stages_pending_ops(session):
    writer = IssueWriter(session)
    sset = SuggestionSet(
        issue_key="APACHE-4",
        suggestions=[
            Suggestion(type="priority", issue_key="APACHE-4", suggested="Critical", confidence=0.8),
            Suggestion(type="estimate", issue_key="APACHE-4", suggested="5", confidence=0.6),
            Suggestion(type="unknown", issue_key="APACHE-4", suggested="x"),  # ignored
        ],
    )
    ops = writer.apply_suggestions(sset)
    assert {o.field for o in ops} == {"priority", "story_points"}
    assert all(o.status == OperationStatus.PENDING for o in ops)


def test_move_to_sprint_bulk(session):
    writer = IssueWriter(session)
    ops = writer.move_to_sprint(["APACHE-4", "APACHE-5"], sprint_id=2)
    assert len(ops) == 2
    assert all(o.field == "sprint" and o.new_value == "2" for o in ops)
    assert all(o.op_type == "move_sprint" for o in ops)

    writer.execute_pending([o.id for o in ops])
    svc = IssueService(session)
    assert svc.get_issue("APACHE-4").sprint_id == 2
    assert svc.get_issue("APACHE-5").sprint_id == 2
