"""CrewAI orchestration mode.

Defines the agent roster as CrewAI Agents (roles/goals) and runs the same
sequential analysis. The CrewAI agents frame the pipeline; the deterministic
core agents do the work (no duplicated logic), so output matches --mode full.
"""

from __future__ import annotations

import logging

from .config import PipelineConfig
from .orchestrator import PipelineOutput, run_pipeline

logger = logging.getLogger(__name__)

_ROSTER = [
    ("Sentiment Analyst", "Score each review's sentiment and pain intensity."),
    ("Theme Synthesizer", "Cluster feedback into the major recurring themes."),
    ("Roadmap Mapper", "Match themes against the product roadmap."),
    ("Gap Strategist", "Surface high-priority unaddressed customer needs."),
]


def _build_agents(model: str):
    from crewai import LLM, Agent

    llm = LLM(model=model)
    return [
        Agent(role=role, goal=goal, backstory=f"You are the {role}.", llm=llm, verbose=False)
        for role, goal in _ROSTER
    ]


def run_crew(
    config: PipelineConfig,
    sources: list[str] | None = None,
    sample_size: int | None = None,
    roadmap_path=None,
    stop_after: str = "full",
    on_event=None,
) -> PipelineOutput:
    agents = _build_agents(config.model_name)
    if on_event:
        on_event(f"CrewAI roster: {', '.join(a.role for a in agents)}")
    return run_pipeline(config, sources, sample_size, roadmap_path, stop_after, on_event)
