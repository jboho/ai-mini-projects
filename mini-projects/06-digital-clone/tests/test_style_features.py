"""Tests for style feature extraction, vectorization, and incremental learning."""

from __future__ import annotations

import numpy as np

from core.style_features import (
    GREETINGS,
    build_style_profile,
    extract_features,
    incremental_update,
    vectorize_features,
)


def test_extract_features(sample_emails):
    f = extract_features(sample_emails)
    assert f.avg_message_length > 0
    assert 0 <= f.vocabulary_richness <= 1
    assert 0 <= f.capitalization_ratio <= 1
    # both sample emails start with "Hi"
    assert f.greeting_patterns["hi"] == 1.0
    # both contain a reasoning connector (because / therefore / however)
    assert sum(f.reasoning_patterns.values()) > 0
    assert f.question_frequency > 0  # second email asks a question (mean per email)


def test_vectorize_is_fixed_length(sample_emails):
    f1 = extract_features(sample_emails)
    f2 = extract_features(sample_emails[:1])
    v1, v2 = vectorize_features(f1), vectorize_features(f2)
    assert v1.shape == v2.shape
    expected = 6 + len(GREETINGS) + 5 + 4 + 5 + 3
    assert v1.shape[0] == expected


def test_incremental_update_ema():
    cur = np.array([1.0, 1.0])
    new = np.array([0.0, 0.0])
    updated = incremental_update(cur, new, alpha=0.3)
    assert np.allclose(updated, [0.7, 0.7])
    # empty current -> adopt new
    assert np.array_equal(incremental_update(np.array([]), new, 0.3), new)


def test_build_style_profile(sample_emails):
    profile = build_style_profile("vince.kaminski", sample_emails, alpha=0.3)
    assert profile.employee_name == "vince.kaminski"
    assert profile.email_count == 2
    assert len(profile.style_embedding) == vectorize_features(profile.style_features).shape[0]
