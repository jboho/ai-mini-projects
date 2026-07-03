"""End-to-end orchestration tests with stubbed generative agents (no LLM)."""

from __future__ import annotations

from agents.planner import DigitalClone
from core.models import EvaluationConfig
from core.style_features import build_style_profile
from core.vectorstore import KnowledgeStore


class _StubRAG:
    def __init__(self, text: str) -> None:
        self.text = text

    def draft(self, query, retrieved) -> str:
        return self.text


class _StubStyle:
    def apply(self, draft, profile) -> str:
        return draft


def _clone(sample_chunks, sample_emails, draft_text, **kw):
    store = KnowledgeStore.build(sample_chunks)
    profile = build_style_profile("vince.kaminski", sample_emails)
    return DigitalClone(
        store,
        profile,
        "vince.kaminski@enron.com",
        rag=_StubRAG(draft_text),
        styler=_StubStyle(),
        **kw,
    )


def test_fallback_path(sample_chunks, sample_emails):
    clone = _clone(sample_chunks, sample_emails, "zzz qqq unrelated maybe perhaps")
    result = clone.query("how does a neural network learn?")
    assert result.evaluation.decision == "fallback"
    assert result.response is None
    assert result.fallback is not None
    assert result.fallback.available_slots
    assert result.retrieved_chunks  # retrieval happened


def test_deliver_path(sample_chunks, sample_emails):
    clone = _clone(
        sample_chunks,
        sample_emails,
        "A neural network learns weights via backprop and gradient descent",
        config=EvaluationConfig(deliver_threshold=0.2),
    )
    result = clone.query("how does a neural network learn?")
    assert result.evaluation.decision == "deliver"
    assert result.response is not None
    assert result.fallback is None
    assert result.processing_time_ms >= 0
