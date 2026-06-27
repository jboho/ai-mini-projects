"""Skill normalization and set-similarity utilities."""

from __future__ import annotations

import re

# Version suffixes to strip: "Python 3", "React.js", "Node.js v18", "AWS S3"
_VERSION_RE = re.compile(r"\s+v?\d[\d.]*$", re.IGNORECASE)
# Common suffixes that don't distinguish skills
_SUFFIX_RE = re.compile(r"\.(js|ts|py|rb|go|net|io)$", re.IGNORECASE)


def normalize_skill(skill: str) -> str:
    """Lowercase, strip version numbers and common file-extension suffixes."""
    s = skill.strip().lower()
    s = _VERSION_RE.sub("", s)
    s = _SUFFIX_RE.sub("", s)
    return s.strip()


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard index between two sets; returns 0.0 when both are empty."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


def normalized_skill_set(skills: list[str]) -> set[str]:
    return {normalize_skill(s) for s in skills}
