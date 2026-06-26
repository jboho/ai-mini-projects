"""Analytics: log suggestions, record feedback, and report acceptance/quality metrics."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import FeedbackLog, SuggestionLog
from ..schemas.responses import Suggestion


def acceptance_rates(rows: list[tuple[str, bool]]) -> dict[str, dict]:
    """Aggregate (suggestion_type, accepted) pairs into per-type total/accepted/rate."""
    agg: dict[str, dict] = {}
    for stype, accepted in rows:
        bucket = agg.setdefault(stype, {"total": 0, "accepted": 0})
        bucket["total"] += 1
        if accepted:
            bucket["accepted"] += 1
    for bucket in agg.values():
        bucket["rate"] = round(bucket["accepted"] / bucket["total"], 3) if bucket["total"] else 0.0
    return agg


class Analytics:
    def __init__(self, session: Session) -> None:
        self.s = session

    def log_suggestion(self, suggestion: Suggestion) -> int:
        row = SuggestionLog(
            type=suggestion.type,
            issue_key=suggestion.issue_key,
            original=suggestion.original or "",
            suggested=suggestion.suggested,
            confidence=suggestion.confidence,
        )
        self.s.add(row)
        self.s.flush()
        return row.id

    def record_feedback(
        self,
        suggestion_id: int,
        accepted: bool,
        reason: str = "",
        modified: bool = False,
    ) -> int:
        if self.s.get(SuggestionLog, suggestion_id) is None:
            raise ValueError(f"Unknown suggestion_id {suggestion_id}")
        row = FeedbackLog(
            suggestion_id=suggestion_id,
            accepted=accepted,
            modified=modified,
            reason=reason,
        )
        self.s.add(row)
        self.s.flush()
        return row.id

    def _feedback_rows(self, by_type: bool) -> list[tuple[str, bool]]:
        stmt = select(SuggestionLog.type, FeedbackLog.accepted).join(
            FeedbackLog, FeedbackLog.suggestion_id == SuggestionLog.id
        )
        rows = [(t if by_type else "overall", bool(a)) for t, a in self.s.execute(stmt)]
        return rows

    def get_acceptance_rates(self, by_type: bool = True) -> dict[str, dict]:
        return acceptance_rates(self._feedback_rows(by_type))

    def get_suggestion_history(
        self, issue_key: str | None = None, type: str | None = None
    ) -> list[dict]:
        stmt = select(SuggestionLog)
        if issue_key:
            stmt = stmt.where(SuggestionLog.issue_key == issue_key)
        if type:
            stmt = stmt.where(SuggestionLog.type == type)
        stmt = stmt.order_by(SuggestionLog.id.desc())
        return [
            {
                "id": row.id,
                "type": row.type,
                "issue_key": row.issue_key,
                "original": row.original,
                "suggested": row.suggested,
                "confidence": row.confidence,
            }
            for row in self.s.scalars(stmt)
        ]

    def get_quality_metrics(self) -> dict:
        suggestions = list(self.s.scalars(select(SuggestionLog)))
        total = len(suggestions)
        by_type: dict[str, int] = {}
        for row in suggestions:
            by_type[row.type] = by_type.get(row.type, 0) + 1
        avg_conf = round(sum(r.confidence for r in suggestions) / total, 3) if total else 0.0

        feedback = list(self.s.scalars(select(FeedbackLog)))
        total_feedback = len(feedback)
        accepted = sum(1 for f in feedback if f.accepted)
        overall_rate = round(accepted / total_feedback, 3) if total_feedback else 0.0

        return {
            "total_suggestions": total,
            "suggestions_by_type": by_type,
            "average_confidence": avg_conf,
            "total_feedback": total_feedback,
            "overall_acceptance_rate": overall_rate,
        }
