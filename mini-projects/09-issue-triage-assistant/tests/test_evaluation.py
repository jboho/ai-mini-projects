"""Phase 9: evaluation metrics (offline) and LLM-as-judge parsing."""

from __future__ import annotations

from pipeline.evaluation import metrics
from pipeline.evaluation.judge import (
    _parse_scores,
    judge_resolution,
    judge_root_cause,
)


def test_classification_accuracy(session):
    result = metrics.classification_accuracy(session)
    assert result["evaluated"] > 0
    assert 0.0 <= result["accuracy"] <= 1.0


def test_duplicate_detection_rate_finds_known_dups(session):
    result = metrics.duplicate_detection_rate(session)
    # sample_data links SPARK-1002 as a duplicate of SPARK-1001 (shared OOM signature).
    assert result["known_duplicate_pairs"] >= 1
    assert result["detected"] >= 1
    assert result["rate"] > 0.0


def test_resolution_relevance(session):
    result = metrics.resolution_relevance(session)
    assert result["evaluated"] >= 1
    assert 0.0 <= result["mean_relevance"] <= 1.0


def test_knowledge_base_coverage(session):
    result = metrics.knowledge_base_coverage(session)
    assert result["categories_total"] == 13
    assert 0.0 <= result["coverage_pct"] <= 100.0


def test_run_all_serializable(session):
    import json

    result = metrics.run_all(session)
    json.dumps(result)  # must not raise
    assert set(result) >= {
        "classification_accuracy",
        "resolution_relevance",
        "knowledge_base_coverage",
        "duplicate_detection_rate",
    }


# --- judge ---------------------------------------------------------------


def test_parse_scores_clamps_and_averages():
    scores = _parse_scores(
        '{"clarity": 5, "accuracy": 3, "actionability": 9}',
        [
            "clarity",
            "accuracy",
            "actionability",
        ],
    )
    assert scores["clarity"] == 5
    assert scores["actionability"] == 5  # clamped to 5
    assert scores["overall"] == round((5 + 3 + 5) / 3, 2)


def test_parse_scores_handles_garbage():
    scores = _parse_scores("not json at all", ["relevance"])
    assert scores["relevance"] == 0
    assert scores["overall"] == 0.0


def test_judge_skips_without_llm():
    assert judge_root_cause("s", "rc", llm=None) == {"skipped": True}
    assert judge_resolution("s", "fix", llm=None) == {"skipped": True}


def test_judge_with_stub_llm():
    def stub(prompt: str) -> str:
        return 'here you go: {"clarity": 4, "accuracy": 4, "actionability": 5}'

    scores = judge_root_cause("summary", "root cause", llm=stub)
    assert scores["clarity"] == 4
    assert scores["overall"] > 0
