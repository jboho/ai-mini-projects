"""RAGAgent: retrieve knowledge and draft a grounded, cited answer (CrewAI)."""

from __future__ import annotations

from core.client import get_model_name
from core.models import KnowledgeChunk


class RAGAgent:
    role = "Knowledge Researcher"

    def __init__(self, llm_model: str | None = None) -> None:
        self.model = llm_model or get_model_name()
        self._agent = None

    @property
    def agent(self):
        if self._agent is None:
            from crewai import LLM, Agent

            self._agent = Agent(
                role=self.role,
                goal="Answer questions strictly from retrieved context, citing sources as [n].",
                backstory="You research a knowledge base and draft grounded answers, never inventing facts.",
                llm=LLM(model=self.model),
                verbose=False,
            )
        return self._agent

    def draft(self, query: str, retrieved: list[tuple[KnowledgeChunk, float]]) -> str:
        from crewai import Crew, Task

        context = "\n".join(f"[{i + 1}] {c.content}" for i, (c, _) in enumerate(retrieved))
        task = Task(
            description=(
                f"Question: {query}\n\nContext:\n{context}\n\n"
                "Answer in 2-4 sentences using ONLY the context, citing sources as [n]. "
                "If the context is insufficient, say so plainly."
            ),
            agent=self.agent,
            expected_output="A grounded answer with [n] citations.",
        )
        return str(Crew(agents=[self.agent], tasks=[task], verbose=False).kickoff())
