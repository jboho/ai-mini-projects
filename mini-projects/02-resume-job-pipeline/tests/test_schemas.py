"""Schema validation tests — Pydantic constraints and custom validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.schemas.resume import ContactInfo, Education, Experience, Resume


def test_contact_info_rejects_short_phone():
    with pytest.raises(ValidationError, match="10 digits"):
        ContactInfo(name="A", email="a@b.com", phone="123", location="NY")


def test_contact_info_accepts_formatted_phone():
    c = ContactInfo(name="A", email="a@b.com", phone="(415) 555-1234", location="NY")
    assert c.phone == "(415) 555-1234"


def test_education_rejects_invalid_date():
    with pytest.raises(ValidationError, match="YYYY-MM"):
        Education(degree="BS", institution="MIT", graduation_date="01/2020")


def test_education_accepts_year_month():
    edu = Education(degree="BS", institution="MIT", graduation_date="2020-05")
    assert edu.graduation_date == "2020-05"


def test_education_gpa_range():
    with pytest.raises(ValidationError):
        Education(degree="BS", institution="MIT", graduation_date="2020-05", gpa=5.0)


def test_experience_end_before_start_rejected():
    with pytest.raises(ValidationError, match="end_date must be after"):
        Experience(
            company="Acme",
            title="Dev",
            start_date="2022-06",
            end_date="2021-01",
            responsibilities=["coding"],
        )


def test_experience_present_is_valid():
    exp = Experience(
        company="Acme",
        title="Dev",
        start_date="2022-06",
        end_date="Present",
        responsibilities=["coding"],
    )
    assert exp.end_date == "Present"


def test_resume_requires_at_least_one_education(sample_resume):
    with pytest.raises(ValidationError):
        data = sample_resume.model_dump()
        data["education"] = []
        Resume.model_validate(data)


def test_resume_requires_summary_min_length(sample_resume):
    with pytest.raises(ValidationError):
        data = sample_resume.model_dump()
        data["summary"] = "Short"
        Resume.model_validate(data)
