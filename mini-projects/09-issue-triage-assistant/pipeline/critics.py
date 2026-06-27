"""Automated critics for quality evaluation in Issue Triage Assistant.

Critics validate outputs at key stages without requiring LLM calls. They implement
deterministic rules for format, schema, and basic correctness checks.

Usage:
    from pipeline.critics import ClassificationCritic, ResolutionCritic

    critic = ClassificationCritic()
    verdict = critic.evaluate(category="api_compatibility", confidence=0.85)
    if not verdict.pass_:
        print(f"FAILED: {verdict.reason}")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


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


class ClassificationCritic:
    """Validates classification outputs."""

    VALID_CATEGORIES = {
        "api_compatibility",
        "build",
        "concurrency",
        "configuration",
        "data_processing",
        "dependency",
        "io_storage",
        "memory",
        "network",
        "other",
        "performance",
        "security",
        "serialization",
    }

    def evaluate(self, category: str, confidence: float) -> CriticVerdict:
        """Evaluate a classification decision.

        Args:
            category: The assigned category
            confidence: Confidence score (0-1)

        Returns:
            CriticVerdict with pass/fail status
        """
        # Check category validity
        if category not in self.VALID_CATEGORIES:
            return CriticVerdict(
                pass_=False,
                severity=Severity.CRITICAL,
                reason=f"Invalid category '{category}'",
                suggestion=f"Must be one of {self.VALID_CATEGORIES}",
            )

        # Check confidence range
        if not 0.0 <= confidence <= 1.0:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Confidence {confidence} out of valid range [0, 1]",
                suggestion="Ensure confidence is normalized to 0-1 range",
            )

        # Warn on low confidence
        if confidence < 0.5:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason=f"Low confidence classification ({confidence})",
                suggestion="Consider manual review for low-confidence decisions",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid classification: {category} @ {confidence:.2f}",
        )


class ResolutionCritic:
    """Validates resolution suggestions."""

    MIN_STEPS = 1
    MAX_STEPS = 10
    MIN_STEP_LENGTH = 10  # characters

    def evaluate(self, resolution_steps: list[str]) -> CriticVerdict:
        """Evaluate a set of resolution steps.

        Args:
            resolution_steps: List of resolution steps

        Returns:
            CriticVerdict with pass/fail status
        """
        # Check step count
        if not self.MIN_STEPS <= len(resolution_steps) <= self.MAX_STEPS:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Got {len(resolution_steps)} steps; expect {self.MIN_STEPS}-{self.MAX_STEPS}",
                suggestion="Ensure resolution includes 1-10 concrete steps",
            )

        # Check each step
        for i, step in enumerate(resolution_steps):
            if not isinstance(step, str):
                return CriticVerdict(
                    pass_=False,
                    severity=Severity.ERROR,
                    reason=f"Step {i}: expected string, got {type(step).__name__}",
                    suggestion="All steps must be strings",
                )

            if len(step) < self.MIN_STEP_LENGTH:
                return CriticVerdict(
                    pass_=False,
                    severity=Severity.WARNING,
                    reason=f"Step {i}: too short ({len(step)} chars)",
                    suggestion=f"Expand steps to be descriptive (>{self.MIN_STEP_LENGTH} chars)",
                )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid resolution: {len(resolution_steps)} steps",
        )


class WorkflowTransitionCritic:
    """Validates approval workflow state transitions."""

    VALID_STATES = {"PENDING", "APPROVED", "EXECUTING", "COMPLETED", "REJECTED"}
    VALID_TRANSITIONS = {
        "PENDING": {"APPROVED", "REJECTED"},
        "APPROVED": {"EXECUTING", "REJECTED"},
        "EXECUTING": {"COMPLETED", "REJECTED"},
        "COMPLETED": set(),
        "REJECTED": set(),
    }

    def evaluate(self, from_state: str, to_state: str) -> CriticVerdict:
        """Evaluate a state transition.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            CriticVerdict with pass/fail status
        """
        # Check valid states
        if from_state not in self.VALID_STATES:
            return CriticVerdict(
                pass_=False,
                severity=Severity.CRITICAL,
                reason=f"Invalid from_state '{from_state}'",
                suggestion=f"Must be one of {self.VALID_STATES}",
            )

        if to_state not in self.VALID_STATES:
            return CriticVerdict(
                pass_=False,
                severity=Severity.CRITICAL,
                reason=f"Invalid to_state '{to_state}'",
                suggestion=f"Must be one of {self.VALID_STATES}",
            )

        # Check valid transition
        if to_state not in self.VALID_TRANSITIONS.get(from_state, set()):
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Invalid transition: {from_state} → {to_state}",
                suggestion=f"Valid transitions from {from_state}: {self.VALID_TRANSITIONS[from_state]}",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid transition: {from_state} → {to_state}",
        )


class ResponseStructureCritic:
    """Validates response structure from agents."""

    def evaluate(self, response: BaseModel) -> CriticVerdict:
        """Evaluate a Pydantic response for schema compliance.

        Args:
            response: Pydantic model instance

        Returns:
            CriticVerdict with pass/fail status
        """
        try:
            # Pydantic validation already happened on instantiation
            # This is a placeholder for additional structural checks
            return CriticVerdict(
                pass_=True,
                severity=Severity.INFO,
                reason=f"Valid response structure: {response.__class__.__name__}",
            )
        except Exception as e:
            return CriticVerdict(
                pass_=False,
                severity=Severity.CRITICAL,
                reason=f"Response validation failed: {e}",
                suggestion="Check that response conforms to schema",
            )


class CompositeCritic:
    """Runs multiple critics and aggregates results."""

    def __init__(self, critics: list[tuple[str, CriticVerdict]]):
        """Initialize with critic verdicts.

        Args:
            critics: List of (name, verdict) tuples
        """
        self.critics = critics

    def all_pass(self) -> bool:
        """Check if all critics passed."""
        return all(verdict.pass_ for _, verdict in self.critics)

    def critical_failures(self) -> list[str]:
        """Get list of critical failures."""
        return [
            name for name, verdict in self.critics
            if not verdict.pass_ and verdict.severity == Severity.CRITICAL
        ]

    def summary(self) -> str:
        """Get a summary of all critic results."""
        lines = ["Critic Results:"]
        for name, verdict in self.critics:
            lines.append(f"  {name}: {verdict}")
        return "\n".join(lines)
