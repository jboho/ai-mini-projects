"""Chunked CSV ingestion with early project filtering.

Designed for the real ~1.7GB Apache JIRA export (read in 50k-row chunks, filtered to
the target projects before accumulating) but tolerant of column-name variations. When
no real CSVs are present, ``write_sample_csvs`` materializes the synthetic dataset to
the same schema so the chunked path can run and be tested end-to-end.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ..db.sample_data import build_sample
from ..db.tables import IssueComment, IssueLink, JiraIssue, StatusTransition

# Accept either our canonical column or common JIRA-export aliases.
_ISSUE_ALIASES = {
    "key": ["key", "issue_key", "issuekey"],
    "project_key": ["project_key", "project", "projectkey"],
    "summary": ["summary", "title"],
    "description": ["description", "body"],
    "issuetype": ["issuetype", "type", "issue_type"],
    "priority": ["priority"],
    "status": ["status"],
    "resolution": ["resolution"],
    "components": ["components", "component"],
    "created_at": ["created_at", "created", "created_date"],
    "resolved_at": ["resolved_at", "resolved", "resolutiondate"],
}


def _pick(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row and pd.notna(row[name]):
            return str(row[name])
    return ""


def _parse_dt(row: pd.Series, names: list[str]) -> datetime.datetime | None:
    raw = _pick(row, names)
    if not raw:
        return None
    ts = pd.to_datetime(raw, utc=True, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.tz_localize(None).to_pydatetime() if ts.tzinfo else ts.to_pydatetime()


def _project_of(row: pd.Series) -> str:
    project = _pick(row, _ISSUE_ALIASES["project_key"])
    if project:
        return project
    key = _pick(row, _ISSUE_ALIASES["key"])
    return key.split("-")[0] if "-" in key else ""


def _read_chunks(csv_path: str | Path, chunksize: int):
    return pd.read_csv(csv_path, chunksize=chunksize, dtype=str, keep_default_na=False)


def load_issues(csv_path, projects, chunksize: int = 50_000, session: Session | None = None) -> int:
    """Chunked load of issues filtered to ``projects``; returns rows inserted."""
    wanted = set(projects)
    inserted = 0
    existing = {k for (k,) in session.execute(select(JiraIssue.key))}
    for chunk in _read_chunks(csv_path, chunksize):
        rows = []
        for _, row in chunk.iterrows():
            project = _project_of(row)
            if project not in wanted:
                continue  # early filter -- keeps peak memory bounded
            key = _pick(row, _ISSUE_ALIASES["key"])
            if not key or key in existing:
                continue
            existing.add(key)
            rows.append(
                {
                    "key": key,
                    "project_key": project,
                    "summary": _pick(row, _ISSUE_ALIASES["summary"]),
                    "description": _pick(row, _ISSUE_ALIASES["description"]),
                    "issuetype": _pick(row, _ISSUE_ALIASES["issuetype"]) or "Bug",
                    "priority": _pick(row, _ISSUE_ALIASES["priority"]) or "Major",
                    "status": _pick(row, _ISSUE_ALIASES["status"]) or "Open",
                    "resolution": _pick(row, _ISSUE_ALIASES["resolution"]),
                    "components": _pick(row, _ISSUE_ALIASES["components"]),
                    "created_at": _parse_dt(row, _ISSUE_ALIASES["created_at"]),
                    "resolved_at": _parse_dt(row, _ISSUE_ALIASES["resolved_at"]),
                }
            )
        if rows:
            session.bulk_insert_mappings(JiraIssue, rows)
            inserted += len(rows)
    session.flush()
    return inserted


def _load_child(csv_path, issue_keys, chunksize, mapper, model, session) -> int:
    wanted = set(issue_keys)
    inserted = 0
    for chunk in _read_chunks(csv_path, chunksize):
        rows = [m for _, row in chunk.iterrows() if (m := mapper(row, wanted)) is not None]
        if rows:
            session.bulk_insert_mappings(model, rows)
            inserted += len(rows)
    session.flush()
    return inserted


def load_comments(
    csv_path, issue_keys, chunksize: int = 50_000, session: Session | None = None
) -> int:
    def _map(row, wanted):
        key = _pick(row, ["issue_key", "key"])
        if key not in wanted:
            return None
        flag = lambda c: str(row.get(c, "")).strip().lower() in ("1", "true", "yes")  # noqa: E731
        return {
            "issue_key": key,
            "author": _pick(row, ["author"]),
            "body": _pick(row, ["body", "comment"]),
            "created_at": _parse_dt(row, ["created_at", "created"]),
            "contains_error": flag("contains_error"),
            "contains_stacktrace": flag("contains_stacktrace"),
            "contains_fix": flag("contains_fix"),
        }

    return _load_child(csv_path, issue_keys, chunksize, _map, IssueComment, session)


def load_changelog(
    csv_path, issue_keys, chunksize: int = 50_000, session: Session | None = None
) -> int:
    def _map(row, wanted):
        key = _pick(row, ["issue_key", "key"])
        if key not in wanted:
            return None
        return {
            "issue_key": key,
            "field": _pick(row, ["field"]) or "status",
            "from_value": _pick(row, ["from_value", "from"]),
            "to_value": _pick(row, ["to_value", "to"]),
            "author": _pick(row, ["author"]),
            "created_at": _parse_dt(row, ["created_at", "created"]),
        }

    return _load_child(csv_path, issue_keys, chunksize, _map, StatusTransition, session)


def load_issuelinks(
    csv_path, issue_keys, chunksize: int = 50_000, session: Session | None = None
) -> int:
    def _map(row, wanted):
        src = _pick(row, ["source_key", "source"])
        if src not in wanted:
            return None
        return {
            "source_key": src,
            "target_key": _pick(row, ["target_key", "target"]),
            "link_type": _pick(row, ["link_type", "type"]) or "relates to",
            "target_status": _pick(row, ["target_status"]),
        }

    return _load_child(csv_path, issue_keys, chunksize, _map, IssueLink, session)


def write_sample_csvs(out_dir: str | Path) -> Path:
    """Materialize the synthetic dataset to issues/comments/changelog/issuelinks CSVs.

    Bridges the synthetic seeder to the chunked CSV loader so the real ingest path is
    exercised in dev and tests without the multi-GB export.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    engine = create_engine("sqlite:///:memory:")
    JiraIssue.metadata.create_all(engine)
    with Session(engine) as s:
        build_sample(s)
        s.commit()
        issues = list(s.scalars(select(JiraIssue)))
        comments = list(s.scalars(select(IssueComment)))
        links = list(s.scalars(select(IssueLink)))
        transitions = list(s.scalars(select(StatusTransition)))

        pd.DataFrame(
            [
                {
                    "key": i.key,
                    "project_key": i.project_key,
                    "summary": i.summary,
                    "description": i.description,
                    "issuetype": i.issuetype,
                    "priority": i.priority,
                    "status": i.status,
                    "resolution": i.resolution,
                    "components": i.components,
                    "created": i.created_at,
                    "resolved": i.resolved_at,
                }
                for i in issues
            ]
        ).to_csv(out / "issues.csv", index=False)
        pd.DataFrame(
            [
                {
                    "issue_key": c.issue_key,
                    "author": c.author,
                    "body": c.body,
                    "created": c.created_at,
                    "contains_error": c.contains_error,
                    "contains_stacktrace": c.contains_stacktrace,
                    "contains_fix": c.contains_fix,
                }
                for c in comments
            ]
        ).to_csv(out / "comments.csv", index=False)
        pd.DataFrame(
            [
                {
                    "issue_key": t.issue_key,
                    "field": t.field,
                    "from_value": t.from_value,
                    "to_value": t.to_value,
                    "author": t.author,
                    "created": t.created_at,
                }
                for t in transitions
            ]
        ).to_csv(out / "changelog.csv", index=False)
        pd.DataFrame(
            [
                {
                    "source_key": link.source_key,
                    "target_key": link.target_key,
                    "link_type": link.link_type,
                    "target_status": link.target_status,
                }
                for link in links
            ]
        ).to_csv(out / "issuelinks.csv", index=False)
    return out


def ingest_dir(data_dir, projects, chunksize: int, session: Session) -> dict[str, int]:
    """Load all four CSVs from ``data_dir`` in dependency order. Returns per-file counts."""
    data = Path(data_dir)
    counts = {"issues": 0, "comments": 0, "changelog": 0, "issuelinks": 0}
    counts["issues"] = load_issues(data / "issues.csv", projects, chunksize, session)
    issue_keys = {k for (k,) in session.execute(select(JiraIssue.key))}
    for name, fn in (
        ("comments", load_comments),
        ("changelog", load_changelog),
        ("issuelinks", load_issuelinks),
    ):
        path = data / f"{name}.csv"
        if path.exists():
            counts[name] = fn(path, issue_keys, chunksize, session)
    return counts
