"""Synthetic QA generation tied to specific chunk ids (per chunking config).

Each chunking configuration gets its own QA dataset so the grid search is a fair
apples-to-apples comparison. A question is generated *from* a known source chunk
and the ground-truth ``relevant_chunk_ids`` is set to that chunk's id, rather
than trusting the model to echo ids back (which it routinely hallucinates).
"""

from __future__ import annotations

import logging
import os
import time

from instructor.core.exceptions import InstructorError
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field

from .client import get_qa_client, get_qa_max_tokens, get_qa_model_name
from .models import Chunk, QAExample

logger = logging.getLogger(__name__)

_MIN_CHUNK_WORDS = 20
_MAX_RETRIES = 6
# Transient/availability failures worth backing off on (vs. auth, which is fatal).
# InstructorError wraps the provider error after instructor's own retries exhaust.
_TRANSIENT_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError, InstructorError)

# Minimum seconds between QA calls, to stay under free-tier rate limits
# (OpenRouter free models allow ~20 req/min). Override with QA_MIN_INTERVAL.
_MIN_CALL_INTERVAL = float(os.environ.get("QA_MIN_INTERVAL", "3.5"))
_last_call_at = 0.0

_QUESTION_TYPES = ["factual", "conceptual", "analytical"]

_SYSTEM_PROMPT = (
    "You write evaluation questions for a retrieval system. Given a passage, "
    "write ONE self-contained {qtype} question that can be answered using only "
    "that passage. The question must not reference 'the passage' or 'this text'; "
    "it should read as a natural standalone question a user would ask."
)


class GeneratedQuestion(BaseModel):
    question: str = Field(min_length=10)
    question_type: str = ""


def _pace() -> None:
    """Block until at least ``_MIN_CALL_INTERVAL`` has elapsed since the last call."""
    global _last_call_at
    wait = _MIN_CALL_INTERVAL - (time.monotonic() - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def _select_chunks(chunks: list[Chunk], num_questions: int) -> list[Chunk]:
    """Pick diverse, substantive chunks spread across the document."""
    eligible = [c for c in chunks if len(c.text.split()) >= _MIN_CHUNK_WORDS]
    if not eligible:
        eligible = chunks
    if len(eligible) <= num_questions:
        return eligible
    step = len(eligible) / num_questions
    return [eligible[int(i * step)] for i in range(num_questions)]


def generate_qa_dataset(
    chunks: list[Chunk],
    num_questions: int = 20,
    model: str | None = None,
    client=None,
) -> list[QAExample]:
    """Generate ``num_questions`` questions, each tied to one source chunk."""
    if not chunks:
        return []

    model = model or get_qa_model_name()
    client = client or get_qa_client()
    max_tokens = get_qa_max_tokens()
    selected = _select_chunks(chunks, num_questions)

    dataset: list[QAExample] = []
    for i, chunk in enumerate(selected):
        qtype = _QUESTION_TYPES[i % len(_QUESTION_TYPES)]
        generated = _generate_one(client, model, max_tokens, chunk, qtype)
        if generated is None:
            continue
        dataset.append(
            QAExample(
                question=generated.question,
                relevant_chunk_ids=[chunk.id],
                metadata={"question_type": qtype, "source_page": chunk.page_number},
            )
        )

    logger.info("Generated %d/%d QA examples", len(dataset), len(selected))
    return dataset


def _generate_one(client, model, max_tokens, chunk, qtype) -> GeneratedQuestion | None:
    """One QA call with exponential backoff on transient/rate-limit errors."""
    for attempt in range(_MAX_RETRIES):
        _pace()
        try:
            return client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                max_retries=1,  # cap instructor's internal retries; we control backoff here
                response_model=GeneratedQuestion,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT.format(qtype=qtype)},
                    {"role": "user", "content": chunk.text},
                ],
            )
        except AuthenticationError:
            raise  # deterministic; retrying only floods logs
        except _TRANSIENT_ERRORS as exc:
            wait = min(60, 5 * 2**attempt)
            logger.warning(
                "Transient QA error (attempt %d/%d), backing off %ds: %s",
                attempt + 1,
                _MAX_RETRIES,
                wait,
                str(exc)[:120],
            )
            time.sleep(wait)
        except (ValueError, RuntimeError) as exc:
            logger.warning("QA generation failed for chunk %s: %s", chunk.id, exc)
            return None
    logger.warning("QA generation exhausted retries for chunk %s", chunk.id)
    return None
