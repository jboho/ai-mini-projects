"""PlannerAgent: orchestrate retrieve -> draft -> style -> evaluate -> deliver/fallback.

The generative agents (RAG, Style) are injectable so the full routing/scoring/
fallback flow can be exercised offline with stubs.
"""

from __future__ import annotations

import time

from core.models import EvaluationConfig, QueryResult, StyleProfile
from core.vectorstore import KnowledgeStore

from .evaluator_agent import EvaluatorAgent
from .fallback_agent import FallbackAgent
from .rag_agent import RAGAgent
from .style_agent import ChatStyleAgent


class DigitalClone:
    def __init__(
        self,
        store: KnowledgeStore,
        profile: StyleProfile,
        employee: str,
        config: EvaluationConfig | None = None,
        rag=None,
        styler=None,
        evaluator=None,
        fallback=None,
    ) -> None:
        self.store = store
        self.profile = profile
        self.employee = employee
        self.rag = rag or RAGAgent()
        self.styler = styler or ChatStyleAgent()
        self.evaluator = evaluator or EvaluatorAgent(config)
        self.fallback = fallback or FallbackAgent()

    def query(self, question: str, k: int = 5) -> QueryResult:
        start = time.perf_counter()
        retrieved = self.store.search(question, k)
        draft = self.rag.draft(question, retrieved)
        styled = self.styler.apply(draft, self.profile)
        evaluation = self.evaluator.evaluate(styled, retrieved, self.profile)

        result = QueryResult(
            query=question,
            evaluation=evaluation,
            retrieved_chunks=[c.content for c, _ in retrieved],
            processing_time_ms=round((time.perf_counter() - start) * 1000, 1),
        )
        if evaluation.decision == "deliver":
            result.response = styled
        else:
            result.fallback = self.fallback.build(evaluation.reasoning, question, self.employee)
        return result
