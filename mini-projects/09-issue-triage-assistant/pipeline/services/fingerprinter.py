"""Fingerprint issues by normalizing volatile tokens and hashing the result.

Same underlying bug -> same signature, even when timestamps, line numbers, hex
addresses, and UUIDs differ between reports. Used to detect recurring/duplicate issues.
"""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.tables import ErrorSignature

_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[ tT]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?")
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b")
_LINENO = re.compile(r":\d+")  # Executor.java:142 -> Executor.java
_NUMBER = re.compile(r"\b\d+\b")
_WS = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    t = (text or "").lower()
    t = _TIMESTAMP.sub(" ", t)
    t = _UUID.sub(" ", t)
    t = _HEX.sub(" ", t)
    t = _LINENO.sub(" ", t)
    t = _NUMBER.sub(" ", t)
    t = _WS.sub(" ", t)
    return t.strip()


def compute_signature(summary: str, description: str = "") -> str:
    normalized = _normalize_text(f"{summary}\n{description}")
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def is_duplicate(session: Session, signature: str) -> ErrorSignature | None:
    return session.scalar(select(ErrorSignature).where(ErrorSignature.signature_hash == signature))


def register_signature(
    session: Session,
    signature: str,
    issue_key: str,
    classification: str = "",
    pattern: str = "",
    known_cause: str = "",
) -> ErrorSignature:
    """Insert a new signature or increment the occurrence count of an existing one."""
    existing = is_duplicate(session, signature)
    if existing is not None:
        existing.occurrence_count += 1
        if known_cause and not existing.known_cause:
            existing.known_cause = known_cause
        session.flush()
        return existing
    row = ErrorSignature(
        signature_hash=signature,
        pattern=pattern,
        classification=classification,
        known_cause=known_cause,
        occurrence_count=1,
        first_issue_key=issue_key,
    )
    session.add(row)
    session.flush()
    return row


def get_occurrence_count(session: Session, signature: str) -> int:
    row = is_duplicate(session, signature)
    return row.occurrence_count if row else 0
