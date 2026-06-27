"""Pydantic data models for the RAG PDF QA system."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


class Section(BaseModel):
    """A titled span of a document, used for qrel ground-truth mapping."""

    index: int
    title: str = ""
    start_char: int
    end_char: int


class Document(BaseModel):
    doc_id: str
    text: str
    title: str = ""
    sections: list[Section] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class Chunk(BaseModel):
    id: str = Field(default_factory=_new_id)
    doc_id: str
    text: str
    page_number: int = 0
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    section_indices: list[int] = Field(default_factory=list)
    method: str = ""
    metadata: dict = Field(default_factory=dict)


class Query(BaseModel):
    query_id: str
    text: str


class Qrel(BaseModel):
    """Ground truth: which (doc, section) spans answer a query."""

    query_id: str
    # doc_id -> list of relevant section indices
    relevant: dict[str, list[int]] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    chunk_id: str
    doc_id: str
    score: float
    rank: int = 0
    text: str = ""
    method: str = ""


class Citation(BaseModel):
    marker: int  # the [N] number used in the answer
    chunk_id: str
    doc_id: str
    text: str = ""
    page_number: int = 0


class QAResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved: list[RetrievalResult] = Field(default_factory=list)
    model: str = ""


class JudgeScores(BaseModel):
    """LLM-as-Judge scores, each on a 1-5 scale."""

    relevance: int = Field(ge=1, le=5)
    accuracy: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    citation_quality: int = Field(ge=1, le=5)
    reasoning: str = ""

    @property
    def average(self) -> float:
        return (self.relevance + self.accuracy + self.completeness + self.citation_quality) / 4


class MetricsResult(BaseModel):
    precision_at_k: dict[str, float] = Field(default_factory=dict)
    recall_at_k: dict[str, float] = Field(default_factory=dict)
    ndcg_at_k: dict[str, float] = Field(default_factory=dict)
    mrr: float = 0.0
    map_score: float = 0.0
    total_queries: int = 0
    avg_retrieval_time: float = 0.0


class ExperimentResult(BaseModel):
    experiment_id: str
    config: dict = Field(default_factory=dict)
    metrics: MetricsResult
    judge_average: float | None = None
    num_queries: int = 0
