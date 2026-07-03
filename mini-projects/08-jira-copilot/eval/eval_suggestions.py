"""Suggestion-quality evaluation against the synthetic sample.

Metrics (leave-one-out against the issue's own ground truth):
- estimate_mae: mean absolute error of weighted story-point estimate vs actual
- priority_agreement: fraction where suggested priority == actual priority
- component_accuracy: fraction where the top neighbour-derived component is one the
  issue actually has
- assignee_accuracy: fraction where the top neighbour-derived assignee == actual

    python eval/eval_suggestions.py            # deterministic metrics
    python eval/eval_suggestions.py --judge    # also LLM-judge summary rewrites

Writes eval/results_suggestions.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from eval.common import build_sample_env, mean  # noqa: E402
from jira_copilot.agents.suggestion_agent import (  # noqa: E402
    SuggestionEngine,
    rank_by_frequency,
)
from jira_copilot.db.models import Issue  # noqa: E402
from jira_copilot.services.vector_store import build_issue_content  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_PATH = EVAL_DIR / "results_suggestions.json"


def _neighbors(store, issue, limit: int = 5) -> list[dict]:
    hits = store.hybrid_search(build_issue_content(issue), limit=limit + 1)
    return [h for h in hits if h["key"] != issue.issue_key][:limit]


def run_eval(judge_llm=None) -> dict:
    session, issues_svc, store = build_sample_env()
    engine = SuggestionEngine(issues_svc, store)
    issues = list(session.scalars(select(Issue)))

    abs_errors, priority_hits, comp_hits, assignee_hits = [], [], [], []
    comp_evaluated = assignee_evaluated = 0

    for issue in issues:
        key = issue.issue_key

        est = engine.suggest_estimate(key)
        if est is not None and issue.story_points is not None:
            abs_errors.append(abs(float(est.suggested) - issue.story_points))

        pri = engine.suggest_priority(key)
        if pri is not None:
            priority_hits.append(1.0 if pri.suggested == issue.priority else 0.0)

        neighbors = _neighbors(store, issue)
        actual_components = {c.name for c in issue.components}
        if actual_components:
            comp_names: list[str] = []
            for hit in neighbors:
                comp_names.extend(c for c in hit["metadata"].get("components", "").split(",") if c)
            ranked = rank_by_frequency(comp_names)
            if ranked:
                comp_evaluated += 1
                comp_hits.append(1.0 if ranked[0][0] in actual_components else 0.0)

        if issue.assignee_id is not None:
            assignee_ids = [
                str(hit["metadata"].get("assignee_id"))
                for hit in neighbors
                if hit["metadata"].get("assignee_id") not in (None, -1)
            ]
            ranked = rank_by_frequency(assignee_ids)
            if ranked:
                assignee_evaluated += 1
                assignee_hits.append(1.0 if int(ranked[0][0]) == issue.assignee_id else 0.0)

    results = {
        "n_issues": len(issues),
        "estimate_mae": round(mean(abs_errors), 3),
        "priority_agreement": round(mean(priority_hits), 3),
        "component_accuracy": round(mean(comp_hits), 3),
        "component_evaluated": comp_evaluated,
        "assignee_accuracy": round(mean(assignee_hits), 3),
        "assignee_evaluated": assignee_evaluated,
    }

    if judge_llm is not None:
        engine_llm = SuggestionEngine(issues_svc, store, llm=judge_llm)
        scores = []
        for issue in issues:
            suggestion = engine_llm.suggest_summary(issue.issue_key)
            if suggestion is None:
                continue
            scores.append(_judge_summary(judge_llm, issue.title, suggestion.suggested))
        results["summary_judge_mean"] = round(mean(scores), 2)
        results["summary_judged"] = len(scores)

    return results


def _judge_summary(llm, original: str, suggested: str) -> float:
    prompt = (
        "Rate the rewritten Jira title from 1-5 for clarity and actionability vs the original. "
        "Return only the integer.\n"
        f"Original: {original}\nRewritten: {suggested}"
    )
    try:
        return float("".join(ch for ch in llm(prompt) if ch.isdigit())[:1] or 0)
    except Exception:
        return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate suggestion quality.")
    parser.add_argument("--judge", action="store_true", help="LLM-judge summary rewrites.")
    args = parser.parse_args()

    judge_llm = None
    if args.judge:
        from jira_copilot.services.query_parser import _openai_llm

        judge_llm = _openai_llm

    results = run_eval(judge_llm=judge_llm)
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")
    for key, value in results.items():
        print(f"  {key}: {value}")
    print(f"Wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
