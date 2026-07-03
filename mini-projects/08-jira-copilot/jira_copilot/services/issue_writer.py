"""IssueWriter: simulation-first write operations.

Every write is a dry-run by default: ``simulate_update`` records the intent in the
``pending_operations`` table WITHOUT touching the issue. Operations are applied only
when ``execute_pending`` is called explicitly, giving a review-then-commit workflow.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Component, Issue, PendingOperation, User
from ..schemas.domain import OperationStatus, WriteOperation
from ..schemas.responses import SuggestionSet

# Public field name -> (ORM attribute, coercion). "__components__" is handled specially.
_FIELDS: dict[str, str] = {
    "title": "title",
    "description": "description_text",
    "priority": "priority",
    "status": "status",
    "story_points": "story_points",
    "assignee": "assignee_id",
    "sprint": "sprint_id",
    "components": "__components__",
}

# Suggestion type -> writable field.
_SUGGESTION_FIELD = {
    "summary": "title",
    "priority": "priority",
    "estimate": "story_points",
    "assignee": "assignee",
    "components": "components",
}


def _to_domain(op: PendingOperation) -> WriteOperation:
    return WriteOperation(
        id=op.id,
        issue_key=op.issue_key,
        op_type=op.op_type,
        field=op.field,
        old_value=op.old_value or None,
        new_value=op.new_value,
        status=OperationStatus(op.status),
    )


class IssueWriter:
    def __init__(self, session: Session) -> None:
        self.s = session

    def _current_value(self, issue: Issue, field: str) -> str:
        if field == "components":
            return ",".join(sorted(c.name for c in issue.components))
        attr = _FIELDS[field]
        value = getattr(issue, attr)
        return "" if value is None else str(value)

    def simulate_update(
        self, issue_key: str, field: str, new_value: str, op_type: str = "update"
    ) -> WriteOperation:
        """Record an intended change as a pending operation; does NOT modify the issue."""
        if field not in _FIELDS:
            raise ValueError(f"Unknown field {field!r}. Allowed: {sorted(_FIELDS)}")
        issue = self.s.scalar(select(Issue).where(Issue.issue_key == issue_key))
        if issue is None:
            raise ValueError(f"Issue {issue_key!r} not found")
        op = PendingOperation(
            issue_key=issue_key,
            op_type=op_type,
            field=field,
            old_value=self._current_value(issue, field),
            new_value=str(new_value),
            status=OperationStatus.PENDING.value,
        )
        self.s.add(op)
        self.s.flush()
        return _to_domain(op)

    def get_pending(self) -> list[WriteOperation]:
        rows = self.s.scalars(
            select(PendingOperation).where(PendingOperation.status == OperationStatus.PENDING.value)
        )
        return [_to_domain(op) for op in rows]

    def discard_pending(self, operation_ids: list[int]) -> int:
        count = 0
        for op_id in operation_ids:
            op = self.s.get(PendingOperation, op_id)
            if op and op.status == OperationStatus.PENDING.value:
                op.status = OperationStatus.DISCARDED.value
                count += 1
        self.s.flush()
        return count

    def execute_pending(self, operation_ids: list[int]) -> list[WriteOperation]:
        applied: list[WriteOperation] = []
        for op_id in operation_ids:
            op = self.s.get(PendingOperation, op_id)
            if op is None or op.status != OperationStatus.PENDING.value:
                continue
            issue = self.s.scalar(select(Issue).where(Issue.issue_key == op.issue_key))
            if issue is None:
                continue
            self._apply(issue, op.field, op.new_value)
            op.status = OperationStatus.EXECUTED.value
            applied.append(_to_domain(op))
        self.s.flush()
        return applied

    def _apply(self, issue: Issue, field: str, new_value: str) -> None:
        if field == "components":
            self._set_components(issue, new_value)
            return
        attr = _FIELDS[field]
        if field == "story_points":
            issue.story_points = float(new_value) if new_value not in ("", "None") else None
        elif field in ("assignee", "sprint"):
            setattr(issue, attr, self._resolve_id(issue, field, new_value))
        else:
            setattr(issue, attr, new_value)

    def _resolve_id(self, issue: Issue, field: str, value: str) -> int | None:
        if value in ("", "None"):
            return None
        if value.isdigit():
            return int(value)
        if field == "assignee":
            user = self.s.scalar(select(User).where(User.username == value))
            if user is None:
                raise ValueError(f"Unknown assignee {value!r}")
            return user.id
        raise ValueError(f"Cannot resolve {field} value {value!r} to an id")

    def _set_components(self, issue: Issue, names_csv: str) -> None:
        names = [n.strip() for n in names_csv.split(",") if n.strip()]
        components = list(
            self.s.scalars(
                select(Component).where(
                    Component.project_id == issue.project_id, Component.name.in_(names)
                )
            )
        )
        issue.components = components

    # --- Bulk helpers ---

    def apply_suggestions(self, suggestions: SuggestionSet) -> list[WriteOperation]:
        """Stage one pending op per suggestion (still a dry-run until executed)."""
        ops: list[WriteOperation] = []
        for s in suggestions.suggestions:
            field = _SUGGESTION_FIELD.get(s.type)
            if field is None:
                continue
            ops.append(self.simulate_update(suggestions.issue_key, field, s.suggested))
        return ops

    def move_to_sprint(self, issue_keys: list[str], sprint_id: int) -> list[WriteOperation]:
        return [
            self.simulate_update(key, "sprint", str(sprint_id), op_type="move_sprint")
            for key in issue_keys
        ]
