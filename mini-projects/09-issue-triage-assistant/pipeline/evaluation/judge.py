"""LLM-as-judge scoring for root-cause and resolution quality.

The judge is optional: every function takes an injectable ``llm`` callable and
returns ``{"skipped": True}`` when none is provided, so evaluation still runs fully
offline. Scores are on a 1-5 scale and parsed tolerantly from the model's reply.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_scores(reply: str, keys: list[str]) -> dict:
    """Extract the first JSON object from the reply; clamp requested keys to 1-5."""
    match = _JSON_RE.search(reply or "")
    raw: dict = {}
    if match:
        try:
            raw = json.loads(match.group(0))
        except json.JSONDecodeError:
            raw = {}
    scores = {}
    for key in keys:
        if key not in raw:
            scores[key] = 0
            continue
        try:
            scores[key] = max(1, min(5, int(round(float(raw[key])))))
        except (TypeError, ValueError):
            scores[key] = 0
    scored = [v for v in scores.values() if v]
    scores["overall"] = round(sum(scored) / len(scored), 2) if scored else 0.0
    return scores


def judge_root_cause(
    issue_summary: str, root_cause: str, llm: Callable[[str], str] | None = None
) -> dict:
    if llm is None:
        return {"skipped": True}
    prompt = (
        "Score this root-cause analysis on clarity, accuracy, and actionability "
        "(integers 1-5). Reply ONLY with JSON like "
        '{"clarity": n, "accuracy": n, "actionability": n}.\n\n'
        f"Issue: {issue_summary}\nRoot cause: {root_cause}"
    )
    return _parse_scores(llm(prompt), ["clarity", "accuracy", "actionability"])


def judge_resolution(
    issue_summary: str, resolution: str, llm: Callable[[str], str] | None = None
) -> dict:
    if llm is None:
        return {"skipped": True}
    prompt = (
        "Score this proposed resolution on relevance and applicability (integers 1-5). "
        'Reply ONLY with JSON like {"relevance": n, "applicability": n}.\n\n'
        f"Issue: {issue_summary}\nResolution: {resolution}"
    )
    return _parse_scores(llm(prompt), ["relevance", "applicability"])


def compare_with_actual(
    proposed: str, actual: str, llm: Callable[[str], str] | None = None
) -> dict:
    if llm is None:
        return {"skipped": True}
    prompt = (
        "Compare the proposed fix to the actual fix. Score agreement 1-5 and give a "
        'one-line gap note. Reply ONLY with JSON like {"agreement": n, "gap": "..."}.\n\n'
        f"Proposed: {proposed}\nActual: {actual}"
    )
    match = _JSON_RE.search(llm(prompt) or "")
    if not match:
        return {"agreement": 0, "gap": ""}
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"agreement": 0, "gap": ""}
    try:
        agreement = max(1, min(5, int(round(float(raw.get("agreement", 0))))))
    except (TypeError, ValueError):
        agreement = 0
    return {"agreement": agreement, "gap": str(raw.get("gap", ""))}
