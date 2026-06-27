"""Answer generation with inline citations over retrieved chunks.

The prompt numbers each context chunk ``[1], [2], ...`` and asks the model to
cite with those markers. ``extract_citations`` parses the ``[N]`` markers back to
the source chunks, so citation quality is checkable independently of the LLM.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from .client import get_chat_client, get_qa_max_tokens, get_qa_model_name
from .interfaces import BaseGenerator
from .models import Chunk, Citation, QAResponse

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(r"\[(\d+)\]")

_SYSTEM = (
    "You answer questions using only the provided numbered context passages. "
    "Cite every claim with the passage number in square brackets, e.g. [1] or "
    "[2]. If the context does not contain the answer, say so. Be concise."
)


class GeneratedAnswer(BaseModel):
    answer: str = Field(min_length=1)


def build_context(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[{i}] {c.text}" for i, c in enumerate(chunks, start=1))


def extract_citations(answer: str, chunks: list[Chunk]) -> list[Citation]:
    """Map ``[N]`` markers in the answer back to their source chunks (in order)."""
    citations: list[Citation] = []
    seen: set[int] = set()
    for match in _CITATION_RE.finditer(answer):
        n = int(match.group(1))
        if n in seen or not (1 <= n <= len(chunks)):
            continue
        seen.add(n)
        chunk = chunks[n - 1]
        citations.append(
            Citation(
                marker=n,
                chunk_id=chunk.id,
                doc_id=chunk.doc_id,
                text=chunk.text[:200],
                page_number=chunk.page_number,
            )
        )
    return citations


class LLMGenerator(BaseGenerator):
    name = "llm"

    def __init__(
        self, model: str | None = None, client=None, max_tokens: int | None = None
    ) -> None:
        self.model = model or get_qa_model_name()
        self.client = client or get_chat_client()
        self.max_tokens = max_tokens or get_qa_max_tokens()

    def generate(self, question: str, chunks: list[Chunk]) -> QAResponse:
        context = build_context(chunks)
        prompt = f"Question: {question}\n\nContext:\n{context}\n\nAnswer with citations:"
        generated = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            response_model=GeneratedAnswer,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return QAResponse(
            question=question,
            answer=generated.answer,
            citations=extract_citations(generated.answer, chunks),
            model=self.model,
        )


def get_generator(model: str | None = None) -> LLMGenerator:
    return LLMGenerator(model=model)
