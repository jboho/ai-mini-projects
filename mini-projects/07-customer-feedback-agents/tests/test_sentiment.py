"""SentimentAgent test with a stubbed Instructor client (no LLM call)."""

from __future__ import annotations

from pipeline.agents.sentiment import SentimentAgent, _SentimentOut


class _StubCompletions:
    def create(self, **kwargs):
        return _SentimentOut(
            sentiment="negative", confidence=0.9, pain_intensity=0.8, reasoning="x"
        )


class _StubClient:
    class chat:  # noqa: N801
        completions = _StubCompletions()


def test_sentiment_agent_wraps_output(sample_feedback):
    agent = SentimentAgent(model="gpt-4o-mini", client=_StubClient())
    result = agent.analyze(sample_feedback[0])
    assert result.feedback_id == sample_feedback[0].id
    assert result.sentiment == "negative"
    assert result.pain_intensity == 0.8


def test_sentiment_batch(sample_feedback):
    results = SentimentAgent(model="gpt-4o-mini", client=_StubClient()).analyze_batch(
        sample_feedback
    )
    assert len(results) == len(sample_feedback)
