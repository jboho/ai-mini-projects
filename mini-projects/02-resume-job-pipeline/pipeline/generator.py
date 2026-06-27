"""LLM-based job and resume generation with controlled fit levels."""

from __future__ import annotations

import logging
import random
import time
import uuid
from datetime import datetime, timezone

import instructor

from .client import get_instructor_client
from .config import Settings, get_settings
from .schemas.job import JobDescription
from .schemas.pair import FitLevel, WritingStyle
from .schemas.resume import Resume, ResumeMetadata
from .templates import SYSTEM_PROMPTS, build_resume_user_prompt

logger = logging.getLogger(__name__)

CALL_DELAY = 0.5
RETRY_DELAY_BASE = 2.0

_JOB_INDUSTRIES = [
    "Software", "Fintech", "Healthcare Tech", "E-commerce", "Cybersecurity",
    "Data Analytics", "DevOps", "Mobile", "AI/ML", "SaaS",
]
_NICHE_INDUSTRIES = [
    "Quantum Computing", "Blockchain Infrastructure", "Bioinformatics",
    "Robotics", "Edge Computing",
]
_COMPANY_SIZES = [
    "10-50 employees", "50-200 employees",
    "200-1000 employees", "1000+ employees",
]


def _job_system_prompt() -> str:
    return (
        "You are a technical recruiter writing realistic job descriptions for "
        "software and tech roles. Each job description must have a real-sounding "
        "company name, a specific role, detailed requirements, and a mix of "
        "required and preferred skills. Skills should be concrete (e.g. 'Python', "
        "'PostgreSQL', 'Kubernetes') not vague ('good communication'). "
        "Experience years must be realistic for the seniority level."
    )


def _job_user_prompt(industry: str, is_niche: bool) -> str:
    niche_note = (
        " This is a niche/specialized role — use domain-specific skills and "
        "requirements that only specialists would have."
        if is_niche
        else ""
    )
    return (
        f"Generate a job description for a {industry} company.{niche_note} "
        "Return all required fields. Use a realistic company name, location, "
        "and size. Required skills list must have 5-10 items. "
        "Set is_niche_role appropriately. "
        "Set trace_id to a UUID string and generated_at to current ISO timestamp."
    )


def generate_jobs(
    settings: Settings | None = None,
    client: instructor.Instructor | None = None,
) -> list[JobDescription]:
    """Generate ``settings.batch_size`` diverse job descriptions."""
    s = settings or get_settings()
    ic = client or get_instructor_client(s)
    jobs: list[JobDescription] = []

    for i in range(s.batch_size):
        is_niche = i % 5 == 4  # every 5th job is niche
        industry = random.choice(_NICHE_INDUSTRIES if is_niche else _JOB_INDUSTRIES)

        for attempt in range(1, s.max_correction_retries + 1):
            try:
                job: JobDescription = ic.chat.completions.create(
                    model=s.model_name,
                    response_model=JobDescription,
                    max_retries=2,
                    messages=[
                        {"role": "system", "content": _job_system_prompt()},
                        {
                            "role": "user",
                            "content": _job_user_prompt(industry, is_niche),
                        },
                    ],
                    temperature=0.9,
                )
                job.metadata.trace_id = str(uuid.uuid4())
                job.metadata.is_niche_role = is_niche
                jobs.append(job)
                logger.info("Job %d/%d [%s] OK", i + 1, s.batch_size, industry)
                break
            except Exception as exc:
                logger.warning("Job %d attempt %d failed: %s", i + 1, attempt, exc)
                if attempt < s.max_correction_retries:
                    time.sleep(RETRY_DELAY_BASE * attempt)

        time.sleep(CALL_DELAY)

    return jobs


def generate_resumes_for_job(
    job: JobDescription,
    settings: Settings | None = None,
    client: instructor.Instructor | None = None,
) -> list[tuple[Resume, FitLevel, WritingStyle]]:
    """Generate ``settings.resumes_per_job`` resumes with varied fit levels and styles.

    Fit levels are distributed evenly across the FitLevel enum so each level
    appears at least once per job when resumes_per_job >= 5.
    """
    s = settings or get_settings()
    ic = client or get_instructor_client(s)
    results: list[tuple[Resume, FitLevel, WritingStyle]] = []

    fit_levels = list(FitLevel)
    styles = list(WritingStyle)
    job_json = job.model_dump_json(indent=2)

    for i in range(s.resumes_per_job):
        fit_level = fit_levels[i % len(fit_levels)]
        style = styles[i % len(styles)]
        system_prompt = SYSTEM_PROMPTS[style]
        user_prompt = build_resume_user_prompt(job_json, fit_level.value)

        for attempt in range(1, s.max_correction_retries + 1):
            try:
                resume: Resume = ic.chat.completions.create(
                    model=s.model_name,
                    response_model=Resume,
                    max_retries=2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.9,
                )
                trace_id = str(uuid.uuid4())
                resume.metadata = ResumeMetadata(
                    trace_id=trace_id,
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    prompt_template=style.value,
                    fit_level=fit_level.value,
                    writing_style=style.value,
                )
                results.append((resume, fit_level, style))
                logger.info(
                    "Resume %d/%d [%s|%s] for job %s OK",
                    i + 1, s.resumes_per_job, fit_level.value, style.value,
                    job.metadata.trace_id[:8],
                )
                break
            except Exception as exc:
                logger.warning(
                    "Resume %d attempt %d failed: %s", i + 1, attempt, exc
                )
                if attempt < s.max_correction_retries:
                    time.sleep(RETRY_DELAY_BASE * attempt)

        time.sleep(CALL_DELAY)

    return results
