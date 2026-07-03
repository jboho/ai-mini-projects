"""Quality critics for Embedding Matching.

Validates match predictions and confidence scores before presenting to users.
Enforces false positive rate targets to prevent bad matches.

Usage:
    from pipeline.critics import MatchCritic, ConfidenceCritic

    critic = MatchCritic()
    verdict = critic.evaluate_match(is_match, confidence, category)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CriticVerdict:
    """Result of evaluation."""
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


class MatchCritic:
    """Validates match predictions."""

    def evaluate_match(
        self,
        is_match: bool,
        confidence: float,
        category: str = "overall",
    ) -> CriticVerdict:
        """Evaluate a match prediction.

        Args:
            is_match: Predicted match (True/False)
            confidence: Confidence score (0-1)
            category: Category (interests, dealbreakers, etc.)

        Returns:
            CriticVerdict
        """
        if not isinstance(is_match, bool):
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"is_match must be bool, got {type(is_match).__name__}",
            )

        if not 0.0 <= confidence <= 1.0:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"Confidence {confidence} out of range [0, 1]",
            )

        # Warn on low confidence matches
        if is_match and confidence < 0.6:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason=f"Low-confidence match prediction ({confidence:.2f})",
                suggestion="Consider requiring higher confidence for positive matches",
            )

        # Warn on high confidence non-matches
        if not is_match and confidence > 0.4:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason=f"High-confidence non-match prediction ({confidence:.2f} confidence in no-match)",
                suggestion="Review edge cases near decision boundary",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Valid match prediction: {is_match} @ {confidence:.2f}",
        )


class ConfidenceCritic:
    """Validates confidence calibration."""

    def evaluate_calibration(
        self,
        predicted_confidence: float,
        empirical_accuracy: float,
        bucket_size: int = 100,
    ) -> CriticVerdict:
        """Evaluate if confidence is well-calibrated.

        Args:
            predicted_confidence: Mean predicted confidence in this bucket
            empirical_accuracy: Actual accuracy in this bucket
            bucket_size: Number of examples in this bucket

        Returns:
            CriticVerdict
        """
        # Expected: if we say 0.8 confidence, actual accuracy should ~0.8
        calibration_error = abs(predicted_confidence - empirical_accuracy)

        if bucket_size < 30:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason=f"Small bucket ({bucket_size} examples); calibration unreliable",
                suggestion="Combine buckets for more stable estimates",
            )

        if calibration_error > 0.15:
            return CriticVerdict(
                pass_=False,
                severity=Severity.WARNING,
                reason=f"Poor calibration: predicted {predicted_confidence:.2f}, actual {empirical_accuracy:.2f}",
                suggestion="Model is overconfident or underconfident; may need retraining",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Well-calibrated: {predicted_confidence:.2f} vs {empirical_accuracy:.2f}",
        )


class FalsePositiveRateCritic:
    """Validates false positive rate thresholds."""

    TARGET_FPR = 0.010  # 1% FPR target

    def evaluate_fpr(
        self,
        false_positive_rate: float,
        category: str = "overall",
    ) -> CriticVerdict:
        """Evaluate false positive rate.

        Args:
            false_positive_rate: FPR metric (0-1)
            category: Category for context

        Returns:
            CriticVerdict
        """
        if not 0.0 <= false_positive_rate <= 1.0:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"FPR {false_positive_rate} out of range [0, 1]",
            )

        if false_positive_rate > 0.05:
            return CriticVerdict(
                pass_=False,
                severity=Severity.ERROR,
                reason=f"FPR {false_positive_rate:.1%} too high for {category}",
                suggestion="Retrain model or increase confidence threshold",
            )

        if false_positive_rate > self.TARGET_FPR:
            return CriticVerdict(
                pass_=True,
                severity=Severity.WARNING,
                reason=f"FPR {false_positive_rate:.2%} above target {self.TARGET_FPR:.2%}",
                suggestion="Monitor for user complaints about bad matches",
            )

        return CriticVerdict(
            pass_=True,
            severity=Severity.INFO,
            reason=f"Excellent FPR: {false_positive_rate:.2%}",
        )
