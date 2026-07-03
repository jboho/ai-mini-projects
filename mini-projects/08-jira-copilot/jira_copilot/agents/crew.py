"""JiraCopilotCrew: orchestrates the engines and (optionally) real CrewAI agents.

The high-level methods (search/get_context/suggest/plan_sprint/release_notes/chat)
call the deterministic engines directly so the API, CLI, and eval get reliable,
fast, structured results. ``run_agentic`` builds and runs a genuine CrewAI crew for
the agentic path (smoke-tested live).
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from ..config import get_settings
from ..schemas.domain import ParsedQuery, QueryIntent
from ..schemas.responses import IssueContext, ReleaseNotes, SprintPlan, SuggestionSet
from ..services.issue_service import IssueService
from ..services.query_parser import QueryParser
from ..services.vector_store import VectorStore
from .context_agent import ContextAssembler
from .documentation_agent import ReleaseNotesWriter
from .retrieval_agent import RetrievalEngine
from .sprint_planner_agent import SprintPlanner
from .suggestion_agent import SuggestionEngine


class JiraCopilotCrew:
    def __init__(
        self,
        session: Session,
        vector_store: VectorStore,
        llm: Callable[[str], str] | None = None,
    ) -> None:
        self.issues = IssueService(session)
        self.vs = vector_store
        self.retrieval = RetrievalEngine(self.issues, vector_store)
        self.context = ContextAssembler(self.issues)
        self.suggestion = SuggestionEngine(self.issues, vector_store, llm=llm)
        self.planner = SprintPlanner(self.issues)
        self.docs = ReleaseNotesWriter(self.issues, llm=llm)
        self.parser = QueryParser(llm=llm)

    # --- Deterministic, structured pipelines (used by API/CLI/eval) ---

    def search(self, query: str, filters: dict | None = None, limit: int = 10):
        return self.retrieval.search(query, filters=filters, limit=limit)

    def get_context(self, issue_key: str) -> IssueContext | None:
        return self.context.assemble(issue_key)

    def suggest(self, issue_key: str, types: list[str] | None = None) -> SuggestionSet:
        return self.suggestion.suggest_all(issue_key, types)

    def plan_sprint(self, project_key: str, **kwargs) -> SprintPlan:
        return self.planner.plan(project_key, **kwargs)

    def generate_release_notes(self, sprint_id: int) -> ReleaseNotes:
        return self.docs.generate(sprint_id)

    def route(self, message: str) -> ParsedQuery:
        return self.parser.parse_query(message)

    def chat(self, message: str) -> dict:
        """Parse the message and dispatch to the matching pipeline."""
        parsed = self.route(message)
        intent = parsed.intent
        keys = parsed.entities.issue_keys
        project = parsed.structured_filters.get("project_key") or (
            parsed.entities.projects[0] if parsed.entities.projects else None
        )

        if intent == QueryIntent.SUGGEST and keys:
            result = self.suggest(keys[0]).model_dump()
        elif intent == QueryIntent.PLAN_SPRINT and project:
            result = self.plan_sprint(project).model_dump()
        elif intent == QueryIntent.ANALYZE and project:
            result = [v.model_dump() for v in self.planner.velocity(project)]
        elif intent == QueryIntent.WRITE:
            result = {
                "note": "Write operations require simulation + confirmation; use the write API."
            }
        elif intent in (QueryIntent.SEARCH, QueryIntent.CHAT):
            result = [
                r.model_dump() for r in self.search(message, filters=parsed.structured_filters)
            ]
        else:
            result = [r.model_dump() for r in self.search(message)]

        return {"intent": intent.value, "parsed": parsed.model_dump(), "result": result}

    # --- Genuine CrewAI agentic path (smoke-tested live) ---

    def _crew_llm(self):
        from crewai import LLM

        settings = get_settings()
        return LLM(model=f"openai/{settings.model_name}", temperature=0)

    def build_agents(self, llm=None) -> dict:
        from .context_agent import build_context_agent
        from .documentation_agent import build_documentation_agent
        from .retrieval_agent import build_retrieval_agent
        from .sprint_planner_agent import build_sprint_planner_agent
        from .suggestion_agent import build_suggestion_agent
        from .tools import build_tools

        llm = llm or self._crew_llm()
        tools = build_tools(self.retrieval, self.context, self.suggestion, self.planner)
        return {
            "retrieval": build_retrieval_agent(tools, llm),
            "context": build_context_agent(tools, llm),
            "suggestion": build_suggestion_agent(tools, llm),
            "sprint_planner": build_sprint_planner_agent(tools, llm),
            "documentation": build_documentation_agent(tools, llm),
        }

    def run_agentic(self, query: str, llm=None) -> str:
        """Run a single-agent CrewAI crew (retrieval) over a query. Requires a live LLM."""
        from crewai import Crew, Process, Task

        agents = self.build_agents(llm)
        agent = agents["retrieval"]
        task = Task(
            description=(
                f"Find the issues most relevant to this request and summarize them: {query!r}. "
                "Use the search_issues tool."
            ),
            expected_output="A short ranked list of relevant issue keys with one-line reasons.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
        return str(crew.kickoff())
