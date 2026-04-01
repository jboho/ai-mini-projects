"""Shared fixtures for the test suite."""

from __future__ import annotations

import pytest

from pipeline.schemas.job import (
    Company,
    ExperienceLevel,
    JobDescription,
    JobMetadata,
    JobRequirements,
)
from pipeline.schemas.pair import FitLevel, PairMetadata, ResumeJobPair, WritingStyle
from pipeline.schemas.resume import (
    ContactInfo,
    Education,
    Experience,
    ProficiencyLevel,
    Resume,
    ResumeMetadata,
    Skill,
)


@pytest.fixture
def sample_job() -> JobDescription:
    return JobDescription(
        company=Company(
            name="Acme Corp",
            industry="Software",
            size="50-200 employees",
            location="San Francisco, CA",
        ),
        title="Senior Python Developer",
        description="Build scalable backend services using Python and FastAPI.",
        requirements=JobRequirements(
            required_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
            preferred_skills=["Kubernetes", "AWS"],
            min_education="Bachelor's in Computer Science",
            experience_years=5,
            experience_level=ExperienceLevel.SENIOR,
        ),
        metadata=JobMetadata(trace_id="job-001", is_niche_role=False),
    )


@pytest.fixture
def sample_resume() -> Resume:
    return Resume(
        contact=ContactInfo(
            name="Jane Smith",
            email="jane@example.com",
            phone="415-555-1234",
            location="San Francisco, CA",
        ),
        education=[
            Education(
                degree="Bachelor of Science in Computer Science",
                institution="UC Berkeley",
                graduation_date="2018-05",
                gpa=3.8,
            )
        ],
        experience=[
            Experience(
                company="TechStartup Inc",
                title="Software Engineer",
                start_date="2018-06",
                end_date="2021-06",
                responsibilities=["Built REST APIs", "Managed PostgreSQL databases"],
                achievements=["Reduced API latency by 35%"],
            ),
            Experience(
                company="ScaleUp Co",
                title="Senior Software Engineer",
                start_date="2021-07",
                end_date="Present",
                responsibilities=["Led backend architecture", "Mentored junior devs"],
                achievements=["Increased throughput by 50%"],
            ),
        ],
        skills=[
            Skill(
                name="Python", proficiency_level=ProficiencyLevel.EXPERT, years_used=6.0
            ),
            Skill(
                name="FastAPI",
                proficiency_level=ProficiencyLevel.ADVANCED,
                years_used=3.0,
            ),
            Skill(
                name="PostgreSQL",
                proficiency_level=ProficiencyLevel.ADVANCED,
                years_used=5.0,
            ),
            Skill(
                name="Docker",
                proficiency_level=ProficiencyLevel.INTERMEDIATE,
                years_used=3.0,
            ),
            Skill(
                name="Redis",
                proficiency_level=ProficiencyLevel.INTERMEDIATE,
                years_used=2.0,
            ),
        ],
        summary=(
            "Backend engineer with 6+ years of Python experience building"
            " high-performance APIs."
        ),
        metadata=ResumeMetadata(
            trace_id="resume-001",
            prompt_template="formal",
            fit_level="Excellent",
            writing_style="formal",
        ),
    )


@pytest.fixture
def sample_pair(sample_resume: Resume, sample_job: JobDescription) -> ResumeJobPair:
    return ResumeJobPair(
        resume=sample_resume,
        job=sample_job,
        metadata=PairMetadata(
            pair_id="pair-001",
            fit_level=FitLevel.EXCELLENT,
            writing_style=WritingStyle.FORMAL,
        ),
    )
