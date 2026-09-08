"""Quantitative evaluation metrics computed directly from the database.

All metrics are deterministic and offline (no LLM): they measure the rule-based
pipeline against independent signals already present in the data, so they are
reproducible in CI. Each returns a small dict so results serialize cleanly to JSON.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import CATEGORIES, CLASSIFICATION_TAXONOMY
from ..db.tables import IssueComment, IssueLink, JiraIssue
from ..services.classifier import classify_issue
from ..services.fingerprinter import compute_signature
from ..services.knowledge_base import get_coverage_stats
from ..services.resolver import _jaccard, _tokens, generate_resolution

# Components that map to exactly one category give an independent ground-truth signal.
_owners: dict[str, set] = {}
for _cat, _spec in CLASSIFICATION_TAXONOMY.items():
    for _comp in _spec.get("components", []):
        _owners.setdefault(_comp.lower(), set()).add(_cat)
_COMPONENT_TO_CATEGORY = {c: next(iter(cats)) for c, cats in _owners.items() if len(cats) == 1}


def _component_category(components: str) -> str | None:
    for token in (components or "").lower().replace(";", ",").split(","):
        cat = _COMPONENT_TO_CATEGORY.get(token.strip())
        if cat:
            return cat
    return None


def classification_accuracy(session: Session, sample_size: int = 100) -> dict:
    """Headline = confident-classification rate; component agreement is a secondary check.

    There is no human-labeled ground truth, so "accuracy" reports the share of issues
    the layered classifier resolves confidently (confidence >= 0.7, i.e. not the 0.3
    fallback). ``component_agreement`` separately compares predictions against a weak
    oracle built from components that uniquely map to one category -- deliberately kept
    distinct because component metadata alone is a noisy predictor.
    """
    issues = list(session.scalars(select(JiraIssue).limit(sample_size)))
    confident = 0
    agree = 0
    comparable = 0
    for issue in issues:
        pred = classify_issue(issue.summary, issue.description, issue.components)
        if pred.confidence >= 0.7:
            confident += 1
        truth = _component_category(issue.components)
        if truth is not None:
            comparable += 1
            if pred.category == truth:
                agree += 1
    n = len(issues)
    return {
        "metric": "classification_accuracy",
        "method": "confident-classification rate (confidence >= 0.7); no labeled ground truth",
        "evaluated": n,
        "confident": confident,
        "accuracy": round(confident / n, 3) if n else 0.0,
        "component_agreement": round(agree / comparable, 3) if comparable else None,
        "component_comparable": comparable,
    }


def resolution_relevance(session: Session, sample_size: int = 50) -> dict:
    """Mean token overlap between generated resolutions and the actual fix comments.

    Restricted to resolved issues that carry a fix comment (the ground-truth fix).
    """
    issues = list(
        session.scalars(select(JiraIssue).where(JiraIssue.resolution != "").limit(sample_size))
    )
    scores: list[float] = []
    for issue in issues:
        fix = next(
            (
                c.body
                for c in session.scalars(
                    select(IssueComment).where(IssueComment.issue_key == issue.key)
                )
                if c.contains_fix and c.body
            ),
            None,
        )
        if not fix:
            continue
        category = classify_issue(issue.summary, issue.description, issue.components).category
        suggestion = generate_resolution(category, find_similar(session, issue), issue.summary)
        text = f"{suggestion.title} {' '.join(suggestion.steps)}"
        scores.append(_jaccard(_tokens(text), _tokens(fix)))
    mean = round(sum(scores) / len(scores), 3) if scores else 0.0
    return {
        "metric": "resolution_relevance",
        "method": "Jaccard(generated steps, actual fix comment)",
        "evaluated": len(scores),
        "mean_relevance": mean,
    }


def find_similar(session: Session, issue: JiraIssue):
    from ..services.resolver import find_similar_issues

    return find_similar_issues(session, issue.summary, issue.description)


def knowledge_base_coverage(session: Session) -> dict:
    stats = get_coverage_stats(session)
    stats["metric"] = "knowledge_base_coverage"
    return stats


def duplicate_detection_rate(session: Session) -> dict:
    """Share of known duplicate pairs whose fingerprints collide as intended.

    Ground truth is the set of ``duplicates`` issue links in the data.
    """
    links = list(session.scalars(select(IssueLink).where(IssueLink.link_type.like("duplicat%"))))
    known = 0
    detected = 0
    for link in links:
        src = session.get(JiraIssue, link.source_key)
        tgt = session.get(JiraIssue, link.target_key)
        if src is None or tgt is None:
            continue
        known += 1
        if compute_signature(src.summary, src.description) == compute_signature(
            tgt.summary, tgt.description
        ):
            detected += 1
    rate = round(detected / known, 3) if known else 0.0
    return {
        "metric": "duplicate_detection_rate",
        "known_duplicate_pairs": known,
        "detected": detected,
        "rate": rate,
    }


def run_all(session: Session, sample_size: int = 100) -> dict:
    return {
        "classification_accuracy": classification_accuracy(session, sample_size),
        "resolution_relevance": resolution_relevance(session, sample_size),
        "knowledge_base_coverage": knowledge_base_coverage(session),
        "duplicate_detection_rate": duplicate_detection_rate(session),
        "categories_total": len(CATEGORIES),
    }
