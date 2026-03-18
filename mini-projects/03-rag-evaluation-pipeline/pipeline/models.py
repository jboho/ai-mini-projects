"""Pydantic data models for the RAG evaluation pipeline."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


class Chunk(BaseModel):
    id: str = Field(default_factory=_new_id)
    text: str
    page_number: int = 0
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    method: str = ""
    metadata: dict = Field(default_factory=dict)


class PageText(BaseModel):
    page_number: int
    text: str
    start_char: int = 0
    end_char: int = 0


class QAExample(BaseModel):
    question: str
    relevant_chunk_ids: list[str] = Field(min_length=1)
    metadata: dict = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    query: str
    retrieved_chunk_ids: list[str]
    scores: list[float]
    method: str
    time_taken: float = 0.0


class MetricsAtK(BaseModel):
    """Metrics computed at various k values."""

    k: int
    recall: float = 0.0
    precision: float = 0.0
    ndcg: float = 0.0


class MetricsResult(BaseModel):
    recall_at_k: dict[str, float] = Field(default_factory=dict)
    precision_at_k: dict[str, float] = Field(default_factory=dict)
    mrr: float = 0.0
    map_score: float = 0.0
    ndcg_at_k: dict[str, float] = Field(default_factory=dict)
    total_queries: int = 0
    avg_retrieval_time: float = 0.0


class ExperimentResult(BaseModel):
    experiment_id: str
    embedding_model: str
    chunking_method: str
    retrieval_method: str
    use_reranking: bool = False
    metrics: MetricsResult
