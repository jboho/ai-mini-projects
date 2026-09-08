"""Phase 6: approval workflow finite state machine."""

from __future__ import annotations

import pytest

from pipeline.db.tables import Incident, Resolution
from pipeline.services.workflow import (
    InvalidTransition,
    approve_action,
    can_transition,
    create_action,
    determine_impact,
    execute_action,
    get_pending_actions,
    reject_action,
)


@pytest.fixture
def resolution_id(session):
    incident = Incident(title="t", source_project="SPARK", classification="memory")
    session.add(incident)
    session.flush()
    res = Resolution(incident_id=incident.id, title="fix")
    session.add(res)
    session.flush()
    return res.id


def test_determine_impact():
    assert determine_impact("add_label") == "LOW"
    assert determine_impact("reassign") == "MEDIUM"
    assert determine_impact("close_issue") == "HIGH"
    assert determine_impact("unknown_action") == "MEDIUM"  # default
    assert determine_impact("transition_status", "SPARK") == "HIGH"  # escalated


def test_can_transition():
    assert can_transition("PENDING", "APPROVED")
    assert can_transition("APPROVED", "EXECUTING")
    assert not can_transition("PENDING", "EXECUTING")
    assert not can_transition("REJECTED", "APPROVED")
    assert not can_transition("COMPLETED", "EXECUTING")


def test_low_impact_auto_approves(session, resolution_id):
    action = create_action(session, resolution_id, "add_label")
    assert action.status == "APPROVED" and action.approved_by == "auto"


def test_medium_impact_pending(session, resolution_id):
    action = create_action(session, resolution_id, "reassign")
    assert action.status == "PENDING"
    assert action in get_pending_actions(session)


def test_full_lifecycle(session, resolution_id):
    action = create_action(session, resolution_id, "reassign")
    approve_action(session, action.id, approved_by="alice")
    assert action.status == "APPROVED" and action.approved_by == "alice"
    execute_action(session, action.id)
    assert action.status == "COMPLETED" and action.executed_at is not None


def test_reject_path(session, resolution_id):
    action = create_action(session, resolution_id, "close_issue")
    reject_action(session, action.id, reason="too risky")
    assert action.status == "REJECTED" and action.reason == "too risky"


def test_invalid_transition_raises(session, resolution_id):
    action = create_action(session, resolution_id, "close_issue")  # PENDING
    with pytest.raises(InvalidTransition):
        execute_action(session, action.id)  # cannot execute before approval
    approve_action(session, action.id, approved_by="bob")
    reject_after_approve = action
    with pytest.raises(InvalidTransition):
        reject_action(session, reject_after_approve.id, reason="late")  # APPROVED can't reject
