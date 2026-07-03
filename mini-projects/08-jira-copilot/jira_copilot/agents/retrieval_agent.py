"""Retrieval engine + CrewAI agent factory.

The engine performs hybrid search and enriches each hit with live DB fields. It is
deterministic and offline-testable; the CrewAI agent is the optional agentic wrapper.
"""

from __future__ import annotations

from ..schemas.responses import SearchResultItem
from ..services.issue_service import IssueService
from ..services.vector_store import VectorStore


class RetrievalEngine:
    def __init__(self, issue_service: IssueService, vector_store: VectorStore) -> None:
        self.issues = issue_service
        self.vs = vector_store

    def search(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 10,
        alpha: float = 0.7,
    ) -> list[SearchResultItem]:
        hits = self.vs.hybrid_search(query, filters=filters, limit=limit, alpha=alpha)
        results: list[SearchResultItem] = []
        for hit in hits:
            issue = self.issues.get_issue(hit["key"])
            meta = hit.get("metadata", {})
            results.append(
                SearchResultItem(
                    key=hit["key"],
                    title=issue.title if issue else meta.get("title", ""),
                    type=issue.type if issue else meta.get("type", ""),
                    status=issue.status if issue else meta.get("status", ""),
                    priority=issue.priority if issue else meta.get("priority", ""),
                    score=round(hit["score"], 4),
                    semantic_score=round(hit.get("semantic_score", 0.0), 4),
                    keyword_score=round(hit.get("keyword_score", 0.0), 4),
                )
            )
        return results


def build_retrieval_agent(tools: list, llm=None):
    from crewai import Agent

    return Agent(
        role="Issue Retrieval Specialist",
        goal="Find the issues most relevant to a user's request using hybrid search.",
        backstory=(
            "You are an expert at navigating large issue trackers. You combine semantic "
            "and keyword search to surface the most relevant issues with their scores."
        ),
        tools=tools,
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )
