"""Six rule-based failure metrics for a resume-job pair.

Each metric is isolated in its own function so it can be tested and
reasoned about independently. label_pair() composes them.
"""

from __future__ import annotations

import re
from datetime import datetime

from .normalizer import jaccard_similarity, normalized_skill_set
from .schemas.job import ExperienceLevel
from .schemas.labels import FailureLabels
from .schemas.pair import ResumeJobPair

_SENIORITY_RANK: dict[ExperienceLevel, int] = {
    ExperienceLevel.ENTRY: 0,
    ExperienceLevel.MID: 1,
    ExperienceLevel.SENIOR: 2,
    ExperienceLevel.LEAD: 3,
    ExperienceLevel.EXECUTIVE: 4,
}

# Title keyword → seniority level mapping.
# Ordered from most- to least-specific so the first match wins.
_TITLE_KEYWORDS: list[tuple[list[str], ExperienceLevel]] = [
    (["intern", "junior", "jr."], ExperienceLevel.ENTRY),
    (["associate", "analyst", "coordinator"], ExperienceLevel.MID),
    (["staff", "senior", "sr."], ExperienceLevel.SENIOR),
    (["lead", "principal", "architect"], ExperienceLevel.LEAD),
    (["director", "vp ", "vice president", "head of", "chief", "cto", "ceo"],
     ExperienceLevel.EXECUTIVE),
]

# AI / buzzword patterns that signal awkward LLM-generated language
_AWKWARD_PHRASES = re.compile(
    r"\b("
    r"leverage[sd]?|synerg(y|ies|ize[sd]?)|paradigm shift|"
    r"thought leader|disrupt(ive|ed|ing)?|deep dive|"
    r"holistic approach|best.in.class|cutting.edge|"
    r"results.driven|self.starter|team player|go.getter|"
    r"dynamic professional|proven track record|value.add"
    r")\b",
    re.IGNORECASE,
)

_DATE_FMTS = ("%Y-%m-%d", "%Y-%m")


def _parse_date(s: str) -> datetime | None:
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _resume_experience_years(pair: ResumeJobPair) -> float:
    total_months = 0.0
    for exp in pair.resume.experience:
        start = _parse_date(exp.start_date)
        if start is None:
            continue
        end = (
            _parse_date(exp.end_date)
            if exp.end_date and exp.end_date.lower() != "present"
            else datetime.now()
        )
        if end and end > start:
            total_months += (end.year - start.year) * 12 + (end.month - start.month)
    return total_months / 12


def _skills_overlap(pair: ResumeJobPair) -> float:
    resume_skills = normalized_skill_set([s.name for s in pair.resume.skills])
    required_skills = normalized_skill_set(pair.job.requirements.required_skills)
    return jaccard_similarity(resume_skills, required_skills)


def _experience_mismatch(pair: ResumeJobPair) -> bool:
    """True when resume years < 50% of required OR gap > 3 years above requirement."""
    required = pair.job.requirements.experience_years
    actual = _resume_experience_years(pair)
    if required == 0:
        return False
    return actual < required * 0.5


def _years_to_rank(years: float) -> int:
    """Map total experience years to a seniority rank integer."""
    if years < 2:
        return _SENIORITY_RANK[ExperienceLevel.ENTRY]
    if years < 5:
        return _SENIORITY_RANK[ExperienceLevel.MID]
    if years < 10:
        return _SENIORITY_RANK[ExperienceLevel.SENIOR]
    if years < 15:
        return _SENIORITY_RANK[ExperienceLevel.LEAD]
    return _SENIORITY_RANK[ExperienceLevel.EXECUTIVE]


def _title_rank(pair: ResumeJobPair) -> int | None:
    """Return the seniority rank signalled by the most recent job title, or None.

    'Most recent' is determined by latest start_date, not list order, because
    the LLM may not emit experience entries chronologically.
    """
    valid = [
        exp for exp in pair.resume.experience if _parse_date(exp.start_date)
    ]
    if not valid:
        return None

    most_recent = max(valid, key=lambda e: _parse_date(e.start_date))  # type: ignore[arg-type]
    title_lower = most_recent.title.lower()

    for keywords, level in _TITLE_KEYWORDS:
        if any(kw in title_lower for kw in keywords):
            return _SENIORITY_RANK[level]
    return None


def _seniority_mismatch(pair: ResumeJobPair) -> bool:
    """True when the effective seniority difference between resume and job is > 1.

    Resume seniority is resolved from two signals:
    - Years of experience  (floor — cannot claim higher than years support)
    - Most recent job title (ceiling — downward claims are trusted as-is)

    The asymmetry encodes the real-world observation that "Junior with 12 years"
    is credible (career choice, domain switch), while "Senior with 2 years" may
    be title inflation and should be capped at what the years justify.
    """
    years = _resume_experience_years(pair)
    years_rank = _years_to_rank(years)
    title = _title_rank(pair)

    if title is None:
        resume_rank = years_rank
    else:
        # Downward claim (Junior + many years) → trust title
        # Upward claim (Senior + few years) → cap at what years justify
        resume_rank = min(title, years_rank)

    job_rank = _SENIORITY_RANK[pair.job.requirements.experience_level]
    return abs(resume_rank - job_rank) > 1


def _missing_core_skills(pair: ResumeJobPair) -> bool:
    """True when any of the top-3 required skills are absent from the resume."""
    top3 = pair.job.requirements.required_skills[:3]
    from .normalizer import normalize_skill
    resume_normalized = {normalize_skill(s.name) for s in pair.resume.skills}
    return any(normalize_skill(req) not in resume_normalized for req in top3)


def _hallucinated_skills(pair: ResumeJobPair) -> bool:
    """Detect implausible skill claims via proportionality heuristics.

    Three signals, ordered from most to least sensitive:

    1. Expert density — more than 3 Expert skills per year of experience is
       unrealistic (4 months per technology is already generous).
    2. Total claimed skill-years — sum of years_used across all skills exceeds
       2× the candidate's total career length (parallel development allowed, but
       not unlimited).
    3. Quantity fallbacks — entry-level with 5+ Expert skills or 20+ total
       skills remains a hard signal for obvious fabrication.

    A single-skill years_used > career length check is also retained.
    """
    from .schemas.resume import ProficiencyLevel

    years = _resume_experience_years(pair)
    skills = pair.resume.skills

    expert_count = sum(1 for s in skills if s.proficiency_level == ProficiencyLevel.EXPERT)
    if expert_count / max(years, 0.5) > 3.0:
        return True

    # Average concurrent technology count — > 6 simultaneous tools is unrealistic
    claimed_skill_years = sum(s.years_used for s in skills if s.years_used is not None)
    if claimed_skill_years / max(years, 0.5) > 6.0 and claimed_skill_years > 5:
        return True

    if years < 2 and expert_count >= 5:
        return True

    if len(skills) >= 20:
        return True

    for skill in skills:
        if skill.years_used and skill.years_used > max(years, 1) + 1:
            return True

    return False


def _awkward_language(pair: ResumeJobPair) -> bool:
    """True when buzzword density in summary + achievements exceeds threshold.

    Threshold: 3+ distinct awkward pattern matches across summary and all
    achievement bullets. This catches resumes that read like generic AI output
    without flagging occasional legitimate uses.
    """
    corpus = pair.resume.summary
    for exp in pair.resume.experience:
        corpus += " " + " ".join(exp.achievements)

    matches = _AWKWARD_PHRASES.findall(corpus)
    return len(matches) >= 3


def label_pair(pair: ResumeJobPair) -> FailureLabels:
    """Compute all six failure metrics for a resume-job pair."""
    return FailureLabels(
        pair_id=pair.metadata.pair_id,
        skills_overlap=_skills_overlap(pair),
        experience_mismatch=_experience_mismatch(pair),
        seniority_mismatch=_seniority_mismatch(pair),
        missing_core_skills=_missing_core_skills(pair),
        hallucinated_skills=_hallucinated_skills(pair),
        awkward_language=_awkward_language(pair),
    )
