"""Tests for each of the 6 failure labeling metrics."""

from __future__ import annotations

import copy

import pytest

from pipeline.labeler import (
    _awkward_language,
    _experience_mismatch,
    _hallucinated_skills,
    _missing_core_skills,
    _seniority_mismatch,
    _skills_overlap,
    label_pair,
)
from pipeline.schemas.resume import ProficiencyLevel, Skill


def test_skills_overlap_perfect_match(sample_pair):
    overlap = _skills_overlap(sample_pair)
    # Resume has all 5 required skills; Jaccard should be 1.0 (no extras)
    assert overlap == pytest.approx(1.0)


def test_skills_overlap_no_match(sample_pair):
    pair = copy.deepcopy(sample_pair)
    pair.resume.skills = [
        Skill(name="Java", proficiency_level=ProficiencyLevel.EXPERT),
        Skill(name="Spring", proficiency_level=ProficiencyLevel.ADVANCED),
    ]
    overlap = _skills_overlap(pair)
    assert overlap == 0.0


def test_experience_mismatch_sufficient_years(sample_pair):
    # Sample resume has ~6 years; job requires 5 → no mismatch
    assert _experience_mismatch(sample_pair) is False


def test_experience_mismatch_insufficient_years(sample_pair):
    pair = copy.deepcopy(sample_pair)
    # Replace with a very short stint
    pair.resume.experience = [
        pair.resume.experience[0].__class__(
            company="X",
            title="Dev",
            start_date="2023-01",
            end_date="2023-06",
            responsibilities=["coding"],
        )
    ]
    # 0.5 years < 5 * 0.5 = 2.5
    assert _experience_mismatch(pair) is True


def test_seniority_mismatch_aligned(sample_pair):
    # ~6 years + "Senior Software Engineer" title → SENIOR rank; job is SENIOR → diff=0
    assert _seniority_mismatch(sample_pair) is False


def test_seniority_mismatch_junior_title_with_many_years(sample_pair):
    # "Junior Developer" title + 12 years → downward claim is trusted → ENTRY rank
    # Job requires SENIOR (rank 2); abs(0-2)=2 > 1 → mismatch
    pair = copy.deepcopy(sample_pair)
    for exp in pair.resume.experience:
        exp.title = "Junior Developer"
    assert _seniority_mismatch(pair) is True


def test_seniority_mismatch_senior_title_with_few_years(sample_pair):
    # "Senior Engineer" title + <2 years experience → title rank (2) is capped
    # at years-based rank (0, ENTRY); job is SENIOR (2); abs(0-2)=2 > 1 → mismatch
    pair = copy.deepcopy(sample_pair)
    pair.resume.experience = [
        pair.resume.experience[0].__class__(
            company="Acme",
            title="Senior Engineer",
            start_date="2025-07",
            end_date="Present",
            responsibilities=["coding"],
        )
    ]
    assert _seniority_mismatch(pair) is True


def test_seniority_mismatch_uses_most_recent_title(sample_pair):
    # Two entries: an old "Junior" role followed by a recent "Senior" role
    # Most-recent title is "Senior", years ~6 → both converge at SENIOR → no mismatch
    pair = copy.deepcopy(sample_pair)
    pair.resume.experience[0].title = "Junior Software Engineer"  # older entry
    pair.resume.experience[1].title = "Senior Software Engineer"  # newer entry
    assert _seniority_mismatch(pair) is False


def test_missing_core_skills_false_when_all_present(sample_pair):
    assert _missing_core_skills(sample_pair) is False


def test_missing_core_skills_true_when_top3_absent(sample_pair):
    pair = copy.deepcopy(sample_pair)
    # Replace all skills with unrelated ones
    pair.resume.skills = [
        Skill(name="Haskell", proficiency_level=ProficiencyLevel.BEGINNER),
    ]
    assert _missing_core_skills(pair) is True


def test_hallucinated_skills_false_normal_profile(sample_pair):
    assert _hallucinated_skills(sample_pair) is False


def test_hallucinated_skills_true_too_many_skills(sample_pair):
    pair = copy.deepcopy(sample_pair)
    pair.resume.skills = [
        Skill(name=f"Skill{i}", proficiency_level=ProficiencyLevel.ADVANCED)
        for i in range(21)
    ]
    assert _hallucinated_skills(pair) is True


def test_hallucinated_skills_expert_density_too_high(sample_pair):
    # ~3 years experience (2023-01 to Mar 2026), 13 Expert skills → 13/3 > 3.0 threshold
    pair = copy.deepcopy(sample_pair)
    pair.resume.experience = [
        pair.resume.experience[0].__class__(
            company="TechCo",
            title="Software Engineer",
            start_date="2023-01",
            end_date="Present",
            responsibilities=["coding"],
        )
    ]
    pair.resume.skills = [
        Skill(name=f"Tool{i}", proficiency_level=ProficiencyLevel.EXPERT)
        for i in range(13)
    ]
    assert _hallucinated_skills(pair) is True


def test_hallucinated_skills_total_claimed_years_too_high(sample_pair):
    # 2-year career; 3 skills each claiming 5 years_used → density=15/2=7.5 > 6.0 and > 5
    pair = copy.deepcopy(sample_pair)
    pair.resume.experience = [
        pair.resume.experience[0].__class__(
            company="Corp",
            title="Developer",
            start_date="2024-01",
            end_date="Present",
            responsibilities=["coding"],
        )
    ]
    pair.resume.skills = [
        Skill(name=f"Lang{i}", proficiency_level=ProficiencyLevel.ADVANCED, years_used=5.0)
        for i in range(3)
    ]
    assert _hallucinated_skills(pair) is True


def test_hallucinated_skills_single_skill_exceeds_career(sample_pair):
    # 2-year career; one skill claims 5 years_used → 5 > max(2,1)+1=3 → True
    pair = copy.deepcopy(sample_pair)
    pair.resume.experience = [
        pair.resume.experience[0].__class__(
            company="Corp",
            title="Developer",
            start_date="2023-01",
            end_date="Present",
            responsibilities=["coding"],
        )
    ]
    pair.resume.skills = [
        Skill(name="Python", proficiency_level=ProficiencyLevel.ADVANCED, years_used=5.0),
    ]
    assert _hallucinated_skills(pair) is True


def test_hallucinated_skills_entry_level_many_expert(sample_pair):
    pair = copy.deepcopy(sample_pair)
    # Make experience very short (entry-level)
    pair.resume.experience = [
        pair.resume.experience[0].__class__(
            company="X",
            title="Intern",
            start_date="2023-09",
            end_date="2024-01",
            responsibilities=["learning"],
        )
    ]
    pair.resume.skills = [
        Skill(name=f"Skill{i}", proficiency_level=ProficiencyLevel.EXPERT)
        for i in range(12)
    ]
    assert _hallucinated_skills(pair) is True


def test_awkward_language_false_clean_resume(sample_pair):
    assert _awkward_language(sample_pair) is False


def test_awkward_language_true_buzzword_heavy(sample_pair):
    pair = copy.deepcopy(sample_pair)
    pair.resume.summary = (
        "A results-driven thought leader who leverages synergies to create "
        "paradigm shifts through holistic approaches and cutting-edge solutions."
    )
    assert _awkward_language(pair) is True


def test_label_pair_returns_all_fields(sample_pair):
    labels = label_pair(sample_pair)
    assert labels.pair_id == sample_pair.metadata.pair_id
    assert 0.0 <= labels.skills_overlap <= 1.0
    assert isinstance(labels.experience_mismatch, bool)
    assert isinstance(labels.seniority_mismatch, bool)
    assert isinstance(labels.missing_core_skills, bool)
    assert isinstance(labels.hallucinated_skills, bool)
    assert isinstance(labels.awkward_language, bool)
