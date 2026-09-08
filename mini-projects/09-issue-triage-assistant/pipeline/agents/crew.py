"""TriageCrew: orchestrates the agent engines (and a genuine CrewAI path).

``run_triage`` runs the deterministic pipeline end-to-end and persists an Incident +
Resolution, registering the issue's fingerprint -- reliable and offline-testable.
``run_agentic`` builds and runs a real CrewAI crew (smoke-tested live).
"""

from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db.tables import Incident, JiraIssue, Resolution
from ..services.fingerprinter import register_signature
from .issue_monitor import fetch_issue_details, scan_new_issues
from .reporter import build_report
from .resolution_advisor import advise
from .root_cause import diagnose
from .text_analyzer import analyze_issue

_SEVERITY = {
    "Blocker": "high",
    "Critical": "high",
    "Major": "medium",
    "Minor": "low",
    "Trivial": "low",
}


class TriageCrew:
    def __init__(self, session: Session, llm: Callable[[str], str] | None = None) -> None:
        self.s = session
        self.llm = llm

    def run_triage(self, issue_key: str) -> dict:
        issue = self.s.get(JiraIssue, issue_key)
        if issue is None:
            return {}

        analysis = analyze_issue(self.s, issue_key, llm=self.llm)
        issue.classification = analysis["classification"]
        issue.confidence = analysis["confidence"]

        root_cause = diagnose(self.s, issue_key, llm=self.llm)
        suggestion = advise(self.s, issue_key, llm=self.llm)

        sig = register_signature(
            self.s,
            analysis["signature"],
            issue_key,
            classification=analysis["classification"],
            pattern=analysis["errors"][0] if analysis["errors"] else "",
        )

        incident = Incident(
            title=issue.summary,
            severity=_SEVERITY.get(issue.priority, "medium"),
            status="open",
            source_project=issue.project_key,
            root_cause=root_cause.summary,
            classification=analysis["classification"],
            error_signature=analysis["signature"],
            jira_issue_key=issue_key,
        )
        self.s.add(incident)
        self.s.flush()

        resolution = Resolution(
            incident_id=incident.id,
            title=suggestion.title,
            steps_json=json.dumps(suggestion.steps),
            confidence=suggestion.confidence,
            based_on_issues=",".join(suggestion.based_on_keys),
        )
        self.s.add(resolution)
        self.s.flush()

        return {
            "issue_key": issue_key,
            "classification": analysis["classification"],
            "confidence": analysis["confidence"],
            "is_recurring": sig.occurrence_count > 1,
            "signature": analysis["signature"],
            "root_cause": root_cause.model_dump(),
            "resolution": suggestion.model_dump(),
            "incident_id": incident.id,
        }

    def run_batch_triage(self, issue_keys: list[str]) -> list[dict]:
        return [r for k in issue_keys if (r := self.run_triage(k))]

    def run_monitoring_cycle(self, project_key: str | None = None) -> list[dict]:
        new_issues = scan_new_issues(self.s, project_key=project_key)
        return self.run_batch_triage([i.key for i in new_issues])

    def report(self, project_key: str | None = None) -> dict:
        return build_report(self.s, project_key)

    def context(self, issue_key: str) -> dict:
        return fetch_issue_details(self.s, issue_key)

    # --- Genuine CrewAI path (smoke-tested live) ---

    def _crew_llm(self):
        from crewai import LLM

        return LLM(model=f"openai/{get_settings().model_name}", temperature=0)

    def build_agents(self, llm=None) -> dict:
        from .issue_monitor import create_monitor_agent
        from .reporter import create_reporter_agent
        from .resolution_advisor import create_resolution_advisor_agent
        from .root_cause import create_root_cause_agent
        from .text_analyzer import create_text_analyzer_agent
        from .tools import build_tools

        llm = llm or self._crew_llm()
        tools = build_tools(self.s)
        return {
            "monitor": create_monitor_agent(tools, llm),
            "text_analyzer": create_text_analyzer_agent(tools, llm),
            "root_cause": create_root_cause_agent(tools, llm),
            "resolution_advisor": create_resolution_advisor_agent(tools, llm),
            "reporter": create_reporter_agent(tools, llm),
        }

    def run_agentic(self, issue_key: str, llm=None) -> str:
        """Run a CrewAI crew (text-analyzer + root-cause) over one issue. Needs a live LLM."""
        from crewai import Crew, Process, Task

        agents = self.build_agents(llm)
        analyze = Task(
            description=(
                f"Analyze issue {issue_key}: classify it and extract its errors using the "
                "analyze_issue tool. Summarize the signals."
            ),
            expected_output="Classification and key error signals.",
            agent=agents["text_analyzer"],
        )
        diagnose_task = Task(
            description=f"Given the analysis, state the likely root cause of {issue_key}.",
            expected_output="A 2-sentence root cause.",
            agent=agents["root_cause"],
        )
        crew = Crew(
            agents=[agents["text_analyzer"], agents["root_cause"]],
            tasks=[analyze, diagnose_task],
            process=Process.sequential,
            verbose=False,
        )
        return str(crew.kickoff())
