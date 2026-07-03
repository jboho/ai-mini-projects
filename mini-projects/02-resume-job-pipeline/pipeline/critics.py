"""Quality critics for Resume-Job Pipeline.

Validates generated resume/job pairs before they enter the judgment pipeline.
Catches format issues, hallucinations, and schema violations early.

Usage:
    from pipeline.critics import PairCritic, FailureModeCritic

    pair_critic = PairCritic()
    verdict = pair_critic.evaluate_pair(resume, job)
    if not verdict.pass_:
        print(f"FAILED: {verdict.reason}")

    failure_critic = FailureModeCritic()
    verdict = failure_critic.evaluate_failures(["hallucinated_skills", "awkward_language"])
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels for critic violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CriticVerdict:
    """Result of a critic evaluation."""
    pass_: bool
    severity: Severity
    reason: str
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        status = "✓ PASS" if self.pass_ else f"✗ {self.severity.value.upper()}"
        msg = f"{status}: {self.reason}"
        if self.suggestion:
            msg += f" → {self.suggestion}"
        return msg


class PairCritic:
    """Validates resume/job pair structure and content."""

    MIN_RESUME_LEN = 100
    MAX_RESUME_LEN = 5000
    MIN_JOB_LEN = 50
    MAX_JOB_LEN = 3000

    def evaluate_pair(self, resume: str, job: str) -> CriticVerdict:
        """Evaluate a resume/job pair.

        Args:
            resume: Resume text
            job: Job description text

        Returns:
            CriticVerdict
        """
        # Check resume length
        if not isinstance(resume, str) or len(resume) < self.MIN_RESUME_LEN:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Resume too short ({len(resume)} chars)",
                suggestion=f"Resume must be {self.MIN_RESUME_LEN}+ chars",
            )

        if len(resume) > self.MAX_RESUME_LEN:
            return CriticVerdict(
                pass_=False,
                severity=Severity.WARNING,
                reason=f"Resume unusually long ({len(resume)} chars)",
                suggestion=f"Typical resumes are <{self.MAX_RESUME_LEN} chars",
            )

        # Check job length
        if not isinstance(job, str) or len(job) < self.MIN_JOB_LEN:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Job description too short ({len(job)} chars)",
                suggestion=f"Job must be {self.MIN_JOB_LEN}+ chars",
            )

        if len(job) > self.MAX_JOB_LEN:
            return CriticVerdict(
                pass_=False,
                severity=Severity.WARNING,
                reason=f"Job description unusually long ({len(job)} chars)",
                suggestion=f"Typical jobs are <{self.MAX_JOB_LEN} chars",
            )

        # Check for suspicious patterns
        if resume.lower().count("llm") > 3 or resume.lower().count("gpt") > 3:
            return CriticVerdict(
                pass_=False,
                severity=Severity.WARNING,
                reason="Resume mentions LLM/AI suspiciously often (hallucination risk)",
                suggestion="Review for genuine experience vs. fabrication",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid pair: resume {len(resume)} chars, job {len(job)} chars",
        )


class FailureModeCritic:
    """Validates failure mode labels."""

    VALID_MODES = {
        "experience_mismatch",
        "seniority_mismatch",
        "missing_core_skills",
        "hallucinated_skills",
        "awkward_language",
    }

    def evaluate_failures(self, failures: list[str]) -> CriticVerdict:
        """Evaluate a list of failure modes.

        Args:
            failures: List of failure mode labels

        Returns:
            CriticVerdict
        """
        if not isinstance(failures, list):
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Failures must be a list, got {type(failures).__name__}",
            )

        # Check for invalid modes
        invalid = [f for f in failures if f not in self.VALID_MODES]
        if invalid:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Invalid failure modes: {invalid}",
                suggestion=f"Use only: {self.VALID_MODES}",
            )

        # Check for duplicates
        if len(failures) != len(set(failures)):
            return CriticVerdict(
                pass_=False,
                severity=Severity.WARNING,
                reason="Duplicate failure modes detected",
                suggestion="Remove duplicates for cleaner analysis",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid failure modes: {failures}",
        )


class FitLevelCritic:
    """Validates fit level classifications."""

    VALID_LEVELS = {"Excellent", "Good", "Poor"}

    def evaluate_fit(self, fit_level: str) -> CriticVerdict:
        """Evaluate a fit level classification.

        Args:
            fit_level: Classification (Excellent, Good, Poor)

        Returns:
            CriticVerdict
        """
        if fit_level not in self.VALID_LEVELS:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Invalid fit level '{fit_level}'",
                suggestion=f"Use: {self.VALID_LEVELS}",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid fit level: {fit_level}",
        )
