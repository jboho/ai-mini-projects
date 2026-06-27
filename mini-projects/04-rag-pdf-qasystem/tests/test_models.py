"""Validation tests for the Pydantic data models and config loaders."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rag.config import RunConfig, load_default_config, load_experiment_grid
from rag.models import Citation, JudgeScores, QAResponse


def test_judge_scores_average():
    scores = JudgeScores(relevance=4, accuracy=5, completeness=3, citation_quality=4)
    assert scores.average == pytest.approx((4 + 5 + 3 + 4) / 4)


def test_judge_scores_reject_out_of_range():
    with pytest.raises(ValidationError):
        JudgeScores(relevance=6, accuracy=5, completeness=3, citation_quality=4)


def test_qa_response_defaults():
    resp = QAResponse(question="q?", answer="a [1]")
    assert resp.citations == []
    assert resp.retrieved == []


def test_citation_fields():
    c = Citation(marker=1, chunk_id="c1", doc_id="paper-1", text="snippet", page_number=2)
    assert c.marker == 1 and c.doc_id == "paper-1"


def test_run_config_label_and_cache_key():
    cfg = RunConfig(
        chunker={"name": "recursive", "params": {"chunk_size": 512}},
        embedder="sentence-transformers/all-MiniLM-L6-v2",
        retriever={"name": "hybrid"},
    )
    assert "recursive" in cfg.label and "hybrid" in cfg.label
    assert len(cfg.cache_key) == 12


def test_load_default_config():
    cfg = load_default_config()
    assert cfg.chunker.name == "recursive"
    assert cfg.top_k == 10


def test_load_experiment_grid_expands_product():
    grid = load_experiment_grid()
    # 4 chunkers x 2 embedders x 3 retrievers x 1 reranker
    assert len(grid) == 24
    assert all(isinstance(c, RunConfig) for c in grid)
