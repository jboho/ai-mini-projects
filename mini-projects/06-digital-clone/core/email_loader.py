"""Enron email loading: parse raw messages, filter sent mail, cache per employee.

Parsing and filtering are pure (testable); the HuggingFace download is isolated
in load_employee_emails and cached to data/emails/{employee}.json.
"""

from __future__ import annotations

import email
import json
import logging
from email.utils import parsedate_to_datetime
from pathlib import Path

from .models import EmailMessage

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "emails"


def parse_enron_message(raw: str) -> EmailMessage:
    """Parse a raw RFC822 Enron message into an EmailMessage."""
    msg = email.message_from_string(raw)
    payload = msg.get_payload()
    body = payload if isinstance(payload, str) else ""
    timestamp = None
    if msg.get("Date"):
        try:
            timestamp = parsedate_to_datetime(msg["Date"])
        except (TypeError, ValueError):
            timestamp = None
    recipients = [r.strip() for r in (msg.get("To", "") or "").split(",") if r.strip()]
    return EmailMessage(
        sender=(msg.get("From", "") or "").strip(),
        recipients=recipients,
        subject=(msg.get("Subject", "") or "").strip(),
        body=body.strip(),
        timestamp=timestamp,
        folder=(msg.get("X-Folder", "") or "").strip(),
    )


def is_sent_folder(folder: str) -> bool:
    f = folder.lower()
    return "sent" in f


def filter_sent(emails: list[EmailMessage], employee: str = "") -> list[EmailMessage]:
    out = []
    for e in emails:
        if not is_sent_folder(e.folder):
            continue
        if employee and employee.lower() not in e.sender.lower():
            continue
        if len(e.body.split()) >= 5:  # skip near-empty stubs
            out.append(e)
    return out


def _cache_path(employee: str) -> Path:
    return DATA_DIR / f"{employee.replace('@', '_at_')}.json"


def load_employee_emails(
    employee: str,
    limit: int = 300,
    dataset: str = "enronarchive/mail",
    use_cache: bool = True,
) -> list[EmailMessage]:
    """Load up to ``limit`` sent emails for ``employee``, caching the result."""
    cache = _cache_path(employee)
    if use_cache and cache.exists():
        logger.info("Loaded cached emails: %s", cache.name)
        return [EmailMessage.model_validate(d) for d in json.loads(cache.read_text())]

    from datasets import load_dataset

    logger.info("Streaming %s for %s sent emails...", dataset, employee)
    stream = load_dataset(dataset, split="train", streaming=True)
    collected: list[EmailMessage] = []
    for record in stream:
        raw = record.get("message") or record.get("text") or record.get("body") or ""
        if not raw:
            continue
        parsed = parse_enron_message(raw)
        if is_sent_folder(parsed.folder) and employee.lower() in parsed.sender.lower():
            if len(parsed.body.split()) >= 5:
                collected.append(parsed)
        if len(collected) >= limit:
            break

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps([e.model_dump(mode="json") for e in collected], indent=2))
    logger.info("Cached %d emails for %s", len(collected), employee)
    return collected
