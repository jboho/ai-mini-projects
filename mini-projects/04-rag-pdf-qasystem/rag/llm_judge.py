"""LLM-as-Judge: score a generated answer on four criteria (1-5) with structured output."""

from __future__ import annotations

import logging

from .client import get_chat_client, get_judge_model_name, get_qa_max_tokens
from .models import JudgeScores, QAResponse

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a strict evaluator of question-answering quality. Score the answer "
    "on four criteria, each 1-5:\n"
    "- relevance: does it address the question?\n"
    "- accuracy: is it consistent with the reference answer?\n"
    "- completeness: does it cover the key points?\n"
    "- citation_quality: are claims supported by bracketed [N] citations?\n"
    "Give a one-sentence reasoning. Use temperature 0 judgment."
)


def judge_answer(
    response: QAResponse,
    reference_answer: str,
    model: str | None = None,
    client=None,
) -> JudgeScores:
    model = model or get_judge_model_name()
    client = client or get_chat_client()
    prompt = (
        f"Question: {response.question}\n\n"
        f"Reference answer: {reference_answer}\n\n"
        f"Candidate answer: {response.answer}\n\n"
        f"Citations used: {len(response.citations)}"
    )
    return client.chat.completions.create(
        model=model,
        max_tokens=get_qa_max_tokens(),
        response_model=JudgeScores,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
