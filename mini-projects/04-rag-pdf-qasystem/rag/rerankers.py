"""Optional reranking: Cohere API or a local cross-encoder.

A reranker re-scores the top retrieval candidates with a more expensive model
and returns the best ``top_k``. ``get_reranker(None)`` returns None (no rerank).
"""

from __future__ import annotations

import logging
import os

from .interfaces import BaseReranker
from .models import RetrievalResult

logger = logging.getLogger(__name__)

_CROSS_ENCODERS: dict[str, object] = {}


class CohereReranker(BaseReranker):
    name = "cohere"

    def __init__(self, model: str = "rerank-english-v3.0") -> None:
        import cohere

        self.model = model
        self.client = cohere.Client(os.environ["COHERE_API_KEY"])

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        if not results:
            return []
        docs = [r.text for r in results]
        ranked = self.client.rerank(
            query=query, documents=docs, top_n=min(top_k, len(docs)), model=self.model
        )
        out = []
        for rank, item in enumerate(ranked.results, start=1):
            base = results[item.index]
            out.append(base.model_copy(update={"score": item.relevance_score, "rank": rank}))
        return out


class CrossEncoderReranker(BaseReranker):
    name = "cross_encoder"

    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model

    @property
    def _model(self):
        if self.model_name not in _CROSS_ENCODERS:
            from sentence_transformers import CrossEncoder

            logger.info("Loading cross-encoder %s", self.model_name)
            _CROSS_ENCODERS[self.model_name] = CrossEncoder(self.model_name)
        return _CROSS_ENCODERS[self.model_name]

    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        if not results:
            return []
        scores = self._model.predict([(query, r.text) for r in results])
        order = sorted(range(len(results)), key=lambda i: -scores[i])[:top_k]
        return [
            results[i].model_copy(update={"score": float(scores[i]), "rank": rank})
            for rank, i in enumerate(order, start=1)
        ]


def get_reranker(name: str | None) -> BaseReranker | None:
    if not name or name == "none":
        return None
    if name == "cohere":
        return CohereReranker()
    if name == "cross_encoder":
        return CrossEncoderReranker()
    raise ValueError(f"Unknown reranker: {name}")
