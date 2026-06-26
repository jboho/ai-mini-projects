"""Tests for the evaluation scoring math."""

from __future__ import annotations

import pytest

from core.scoring import confidence_score, evaluate_response, groundedness_score
from core.style_features import build_style_profile


def test_groundedness(sample_chunks):
    grounded = "A neural network learns weights via backprop"
    assert groundedness_score(grounded, sample_chunks) > 0.7
    assert groundedness_score("completely unrelated zzz qqq", sample_chunks) < 0.4


def test_confidence_hedging_penalty():
    assert confidence_score([0.9, 0.7], "a clear direct answer") == pytest.approx(0.8)
    hedged = confidence_score([0.9], "maybe perhaps i think it could be")
    direct = confidence_score([0.9], "it is exactly this")
    assert hedged < direct


def test_evaluate_grounded_beats_ungrounded(sample_emails, sample_chunks):
    profile = build_style_profile("vince.kaminski", sample_emails)
    grounded = evaluate_response(
        "A neural network learns weights via backprop and gradient descent",
        [(c, 0.9) for c in sample_chunks],
        profile,
    )
    ungrounded = evaluate_response(
        "zzz qqq totally unrelated maybe perhaps i think",
        [(sample_chunks[0], 0.1)],
        profile,
    )
    assert ungrounded.decision == "fallback"
    assert grounded.final_score > ungrounded.final_score
    assert grounded.decision in ("deliver", "fallback")
