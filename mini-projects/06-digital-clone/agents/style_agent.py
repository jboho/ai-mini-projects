"""ChatStyleAgent: rewrite a draft in the target person's email style (CrewAI)."""

from __future__ import annotations

from core.client import get_model_name
from core.models import StyleProfile
from core.scoring import style_score


def _top_key(dist: dict[str, float]) -> str:
    return max(dist, key=dist.get) if dist else "none"


class ChatStyleAgent:
    role = "Style Stylist"

    def __init__(self, llm_model: str | None = None) -> None:
        self.model = llm_model or get_model_name()
        self._agent = None

    @property
    def agent(self):
        if self._agent is None:
            from crewai import LLM, Agent

            self._agent = Agent(
                role=self.role,
                goal="Rewrite text to match a specific person's email writing style.",
                backstory="You are a ghostwriter who mimics a person's tone, greetings, and sign-offs.",
                llm=LLM(model=self.model),
                verbose=False,
            )
        return self._agent

    def style_guidance(self, profile: StyleProfile) -> str:
        f = profile.style_features
        return (
            f"~{f.avg_message_length:.0f} words; greeting '{_top_key(f.greeting_patterns)}'; "
            f"sign-off '{_top_key(f.signoff_patterns)}'; formality {f.formality_level:.2f}; "
            f"question-asking {f.question_frequency:.1f}/msg"
        )

    def apply(self, draft: str, profile: StyleProfile) -> str:
        from crewai import Crew, Task

        task = Task(
            description=(
                f"Rewrite the message below to match this person's email style.\n"
                f"Style: {self.style_guidance(profile)}\n\n"
                f"Message:\n{draft}\n\n"
                "Keep all facts and [n] citations intact; only change tone, greeting, and sign-off."
            ),
            agent=self.agent,
            expected_output="The rewritten message in the target style.",
        )
        return str(Crew(agents=[self.agent], tasks=[task], verbose=False).kickoff())

    def score(self, response: str, profile: StyleProfile) -> float:
        return style_score(response, profile)
