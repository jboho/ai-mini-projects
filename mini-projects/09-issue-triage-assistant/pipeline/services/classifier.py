"""Layered issue classifier: keyword/regex -> component -> composite pattern -> LLM.

The rule layers are pure and deterministic (fully unit-tested). The LLM fallback is
injectable (``llm`` callable taking a prompt, returning text) so tests run offline.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from ..config import CATEGORIES, CLASSIFICATION_TAXONOMY, COMPOSITE_PATTERNS
from ..models import ClassificationResult


def _keyword_match(text: str) -> ClassificationResult | None:
    """High-confidence regex/keyword match (>0.9)."""
    lowered = text.lower()
    for category, spec in CLASSIFICATION_TAXONOMY.items():
        for pattern in spec["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return ClassificationResult(
                    category=category,
                    confidence=0.95,
                    method="keyword",
                    evidence=f"regex:{pattern}",
                )
    for category, spec in CLASSIFICATION_TAXONOMY.items():
        for keyword in spec["keywords"]:
            if keyword in lowered:
                return ClassificationResult(
                    category=category,
                    confidence=0.9,
                    method="keyword",
                    evidence=f"keyword:{keyword}",
                )
    return None


def _component_match(components: str | list[str] | None) -> ClassificationResult | None:
    """Medium-high confidence (~0.85) from the JIRA components field."""
    if not components:
        return None
    text = components.lower() if isinstance(components, str) else " ".join(components).lower()
    for category, spec in CLASSIFICATION_TAXONOMY.items():
        for fragment in spec["components"]:
            if fragment in text:
                return ClassificationResult(
                    category=category,
                    confidence=0.85,
                    method="component",
                    evidence=f"component:{fragment}",
                )
    return None


def _pattern_match(text: str) -> ClassificationResult | None:
    """Medium confidence (~0.7) composite patterns: all fragments must appear."""
    lowered = text.lower()
    for fragments, category in COMPOSITE_PATTERNS:
        if all(fragment in lowered for fragment in fragments):
            return ClassificationResult(
                category=category,
                confidence=0.7,
                method="pattern",
                evidence=f"composite:{'+'.join(fragments)}",
            )
    return None


def _llm_classify(
    summary: str, description: str, llm: Callable[[str], str]
) -> ClassificationResult | None:
    prompt = (
        "Classify this software issue into exactly ONE category from this list:\n"
        f"{', '.join(CATEGORIES)}\n"
        "Return only the category name.\n\n"
        f"Summary: {summary}\nDescription: {description[:800]}"
    )
    try:
        raw = llm(prompt).strip().lower()
    except Exception:
        return None
    for category in CATEGORIES:
        if category in raw:
            return ClassificationResult(
                category=category, confidence=0.6, method="llm", evidence="llm-fallback"
            )
    return None


def classify_issue(
    summary: str,
    description: str = "",
    components: str | list[str] | None = None,
    llm: Callable[[str], str] | None = None,
) -> ClassificationResult:
    """Classify through the layers in order; first confident match wins."""
    text = f"{summary}\n{description}"

    result = _keyword_match(text)
    if result is not None:
        return result

    result = _component_match(components)
    if result is not None:
        return result

    result = _pattern_match(text)
    if result is not None:
        return result

    if llm is not None:
        result = _llm_classify(summary, description, llm)
        if result is not None:
            return result

    return ClassificationResult(
        category="other", confidence=0.3, method="fallback", evidence="no rule matched"
    )
