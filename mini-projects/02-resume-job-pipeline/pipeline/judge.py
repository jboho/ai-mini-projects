"""LLM-as-Judge: structured qualitative evaluation of resume-job pairs.

Toggled by ``settings.enable_judge``. Returns a JudgeResult with numeric
scores for hallucination severity, language quality, overall fit, and
actionable recommendations. Using Instructor here keeps the output
schema-valid without prompt engineering fragility.
"""

from __future__ import annotations

import logging

import instructor

from .client import get_instructor_client
from .config import Settings, get_settings
from .schemas.labels import JudgeResult
from .schemas.pair import ResumeJobPair

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a senior technical recruiter and resume quality analyst.
You evaluate resume-job pairs for:
1. Hallucinations — skills or experience that seem fabricated or implausible
2. Awkward language — AI buzzwords, robotic phrasing, lack of authenticity
3. Overall quality — does this resume represent the candidate clearly and honestly?
4. Fit — does the candidate's background align with the role's requirements?

Respond with precise numeric scores and concise, actionable recommendations.
"""


def _build_judge_prompt(pair: ResumeJobPair) -> str:
    return (
        f"Evaluate the following resume against this job description.\n\n"
        f"JOB TITLE: {pair.job.title}\n"
        f"REQUIRED SKILLS: {', '.join(pair.job.requirements.required_skills)}\n"
        f"EXPERIENCE REQUIRED: {pair.job.requirements.experience_years} years "
        f"({pair.job.requirements.experience_level.value})\n\n"
        f"RESUME SUMMARY: {pair.resume.summary}\n\n"
        f"RESUME SKILLS: {', '.join(s.name for s in pair.resume.skills)}\n\n"
        f"EXPERIENCE ENTRIES: {len(pair.resume.experience)} positions\n\n"
        "Score the resume on:\n"
        "- hallucination_score (0=none, 5=severe)\n"
        "- awkward_language_score (0=natural, 5=very robotic)\n"
        "- quality_score (0=very poor, 10=excellent)\n"
        "- fit_assessment (1-2 sentence plain-language fit summary)\n"
        "- recommendations (list of 2-3 specific improvements)\n\n"
        f"Set pair_id to: {pair.metadata.pair_id}"
    )


def judge_pair(
    pair: ResumeJobPair,
    settings: Settings | None = None,
    client: instructor.Instructor | None = None,
) -> JudgeResult | None:
    """Run LLM-as-Judge evaluation; returns None if judge is disabled or call fails."""
    s = settings or get_settings()
    if not s.enable_judge:
        return None

    ic = client or get_instructor_client(s)

    try:
        result: JudgeResult = ic.chat.completions.create(
            model=s.model_name,
            response_model=JudgeResult,
            max_retries=2,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_judge_prompt(pair)},
            ],
            temperature=0.2,
        )
        result.pair_id = pair.metadata.pair_id
        logger.info(
            "Judge pair %s: quality=%d hallucination=%d",
            pair.metadata.pair_id[:8],
            result.quality_score,
            result.hallucination_score,
        )
        return result
    except Exception as exc:
        logger.warning("Judge failed for pair %s: %s", pair.metadata.pair_id[:8], exc)
        return None
