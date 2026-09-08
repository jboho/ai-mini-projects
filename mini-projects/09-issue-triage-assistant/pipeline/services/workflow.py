"""Approval workflow finite state machine for resolution actions.

States: PENDING -> APPROVED -> EXECUTING -> COMPLETED, or PENDING -> REJECTED.
Impact level governs auto-approval: LOW auto-approves; MEDIUM/HIGH require a human.
All transitions are validated against the FSM; invalid transitions raise.
"""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import IMPACT_RULES
from ..db.tables import ResolutionAction

# Allowed state transitions.
_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"APPROVED", "REJECTED"},
    "APPROVED": {"EXECUTING"},
    "EXECUTING": {"COMPLETED"},
    "REJECTED": set(),
    "COMPLETED": set(),
}


class InvalidTransition(Exception):
    pass


def can_transition(from_state: str, to_state: str) -> bool:
    return to_state in _TRANSITIONS.get(from_state, set())


def _transition(action: ResolutionAction, to_state: str) -> None:
    if not can_transition(action.status, to_state):
        raise InvalidTransition(f"{action.status} -> {to_state} is not allowed")
    action.status = to_state


def determine_impact(action_type: str, project_key: str | None = None) -> str:
    """LOW / MEDIUM / HIGH. Cross-project actions are escalated to HIGH."""
    impact = IMPACT_RULES.get(action_type, "MEDIUM")
    if project_key and action_type == "transition_status" and project_key in {"SPARK", "HADOOP"}:
        impact = "HIGH"  # high-traffic projects: status changes need extra scrutiny
    return impact


def create_action(
    session: Session,
    resolution_id: int,
    action_type: str,
    project_key: str | None = None,
    description: str = "",
) -> ResolutionAction:
    """Create an action; LOW-impact ones auto-approve, others land in PENDING."""
    impact = determine_impact(action_type, project_key)
    auto = impact == "LOW"
    action = ResolutionAction(
        resolution_id=resolution_id,
        action_type=action_type,
        impact_level=impact,
        status="APPROVED" if auto else "PENDING",
        approved_by="auto" if auto else "",
        reason=description,
    )
    session.add(action)
    session.flush()
    return action


def approve_action(session: Session, action_id: int, approved_by: str) -> ResolutionAction:
    action = session.get(ResolutionAction, action_id)
    _transition(action, "APPROVED")
    action.approved_by = approved_by
    session.flush()
    return action


def reject_action(session: Session, action_id: int, reason: str = "") -> ResolutionAction:
    action = session.get(ResolutionAction, action_id)
    _transition(action, "REJECTED")
    action.reason = reason
    session.flush()
    return action


def execute_action(session: Session, action_id: int) -> ResolutionAction:
    """APPROVED -> EXECUTING -> COMPLETED, stamping executed_at."""
    action = session.get(ResolutionAction, action_id)
    _transition(action, "EXECUTING")
    _transition(action, "COMPLETED")
    action.executed_at = datetime.datetime.utcnow()
    session.flush()
    return action


def get_pending_actions(session: Session) -> list[ResolutionAction]:
    return list(
        session.scalars(select(ResolutionAction).where(ResolutionAction.status == "PENDING"))
    )
