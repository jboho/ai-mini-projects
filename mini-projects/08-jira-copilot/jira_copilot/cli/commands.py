"""Typer CLI for the Jira Copilot. All commands call the shared service layer.

``build_runtime`` is the single place that wires sessions/vector store/crew together;
tests monkeypatch it to inject an in-memory DB and stub embedder. The ``_fmt_*``
helpers are pure string formatters and are unit-tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.crew import JiraCopilotCrew
from ..config import DATA_DIR, get_settings
from ..db.engine import get_engine
from ..db.models import Base, Issue
from ..db.sample_data import build_sample
from ..schemas.responses import IssueContext, SprintPlan, SuggestionSet
from ..services.analytics import Analytics
from ..services.issue_writer import IssueWriter
from ..services.query_parser import _openai_llm
from ..services.vector_store import make_vector_store

app = typer.Typer(help="AI-powered Jira copilot over the TAWOS dataset.", no_args_is_help=True)


@dataclass
class Runtime:
    session: Session
    store: object
    crew: JiraCopilotCrew
    writer: IssueWriter
    analytics: Analytics


def build_runtime() -> Runtime:
    settings = get_settings()
    engine = get_engine()
    session = Session(engine)
    store = make_vector_store(persist_path=settings.chromadb_path)
    llm = _openai_llm if settings.openai_api_key else None
    crew = JiraCopilotCrew(session, store, llm=llm)
    return Runtime(session, store, crew, IssueWriter(session), Analytics(session))


# --- Pure formatters ---


def _fmt_search(items) -> str:
    if not items:
        return "No results."
    return "\n".join(
        f"{i.key:12} [{i.status:^12}] {i.priority:8} score={i.score:.3f}  {i.title}" for i in items
    )


def _fmt_context(ctx: IssueContext) -> str:
    lines = [
        f"{ctx.key}  {ctx.title}",
        f"  type={ctx.type} status={ctx.status} priority={ctx.priority} points={ctx.story_points}",
        f"  components: {', '.join(ctx.components) or '-'}",
    ]
    if ctx.linked_issues:
        lines.append("  links:")
        lines += [
            f"    {link.direction:8} {link.link_type:12} {link.key} ({link.title})"
            for link in ctx.linked_issues
        ]
    if ctx.comments:
        lines.append(f"  comments: {len(ctx.comments)}")
    return "\n".join(lines)


def _fmt_suggestions(sset: SuggestionSet) -> str:
    if not sset.suggestions:
        return f"No suggestions for {sset.issue_key}."
    lines = [f"Suggestions for {sset.issue_key}:"]
    for s in sset.suggestions:
        lines.append(f"  [{s.type:10}] {s.suggested!r}  (conf={s.confidence:.2f})  {s.rationale}")
    return "\n".join(lines)


def _fmt_plan(plan: SprintPlan) -> str:
    lines = [
        f"Sprint plan for {plan.project_key}: capacity={plan.capacity} "
        f"avg_velocity={plan.average_velocity} planned_points={plan.total_points}",
    ]
    for r in plan.recommended:
        lines.append(f"  {r.key:12} {r.priority:8} {r.story_points}  {r.title}")
    return "\n".join(lines)


def _fmt_chat(out: dict) -> str:
    intent = out["intent"]
    result = out["result"]
    if isinstance(result, list):
        body = "\n".join(f"  - {r.get('key', r)}" for r in result) if result else "  (no results)"
    else:
        body = f"  {result}"
    return f"[intent={intent}]\n{body}"


# --- Commands ---


@app.command()
def sync(sample: bool = typer.Option(True, help="Seed the synthetic sample dataset.")) -> None:
    """Build/refresh the SQLite DB and rebuild the vector index."""
    settings = get_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if sample:
            build_sample(session)
            session.commit()
        issues = list(session.scalars(select(Issue)))
        store = make_vector_store(persist_path=settings.chromadb_path)
        indexed = store.index_issues(issues)
    typer.echo(
        f"Synced {len(issues)} issues; indexed {indexed} vectors into {settings.chromadb_path}."
    )


@app.command()
def search(query: str, limit: int = 10) -> None:
    """Hybrid search over indexed issues."""
    rt = build_runtime()
    typer.echo(_fmt_search(rt.crew.search(query, limit=limit)))


@app.command()
def query(text: str) -> None:
    """Parse a natural-language query into intent + entities."""
    rt = build_runtime()
    parsed = rt.crew.route(text)
    typer.echo(f"intent={parsed.intent.value}")
    typer.echo(f"entities={parsed.entities.model_dump()}")
    typer.echo(f"filters={parsed.structured_filters}")


@app.command()
def context(issue_key: str) -> None:
    """Assemble full context for an issue."""
    rt = build_runtime()
    ctx = rt.crew.get_context(issue_key)
    typer.echo(_fmt_context(ctx) if ctx else f"Issue {issue_key} not found.")


@app.command()
def suggest(
    issue_key: str, type: str = typer.Option("all", help="Suggestion type or 'all'.")
) -> None:
    """Generate improvement suggestions for an issue."""
    rt = build_runtime()
    types = None if type == "all" else [type]
    result = rt.crew.suggest(issue_key, types=types)
    typer.echo(_fmt_suggestions(result))


@app.command("plan-sprint")
def plan_sprint(
    project_key: str,
    capacity: Optional[float] = typer.Option(None, help="Override capacity (story points)."),
    sprints: int = 5,
) -> None:
    """Plan a sprint within capacity (defaults to historical velocity)."""
    rt = build_runtime()
    plan = rt.crew.plan_sprint(project_key, capacity=capacity, n_sprints=sprints)
    typer.echo(_fmt_plan(plan))


@app.command()
def velocity(project_key: str, sprints: int = 5) -> None:
    """Show recent sprint velocity."""
    rt = build_runtime()
    points = rt.crew.planner.velocity(project_key, sprints)
    if not points:
        typer.echo("No closed sprints found.")
        return
    for v in points:
        typer.echo(f"  {v.sprint_name:12} {v.completed_points} pts")


@app.command("release-notes")
def release_notes(sprint_id: int) -> None:
    """Generate release notes for a sprint."""
    rt = build_runtime()
    typer.echo(rt.crew.generate_release_notes(sprint_id).markdown)


@app.command()
def chat(
    message: Optional[str] = typer.Argument(None, help="One-shot message; omit for interactive."),
) -> None:
    """Conversational mode: parse and route a message to the right pipeline."""
    rt = build_runtime()
    if message:
        typer.echo(_fmt_chat(rt.crew.chat(message)))
        return
    typer.echo("Jira Copilot chat. Type 'exit' to quit.")
    while True:
        try:
            msg = input("> ").strip()
        except EOFError:
            break
        if msg in {"exit", "quit"}:
            break
        if msg:
            typer.echo(_fmt_chat(rt.crew.chat(msg)))


@app.command()
def stats() -> None:
    """Show analytics / suggestion-quality metrics."""
    rt = build_runtime()
    metrics = rt.analytics.get_quality_metrics()
    for key, value in metrics.items():
        typer.echo(f"  {key}: {value}")


@app.command()
def pending() -> None:
    """List pending (simulated) write operations."""
    rt = build_runtime()
    ops = rt.writer.get_pending()
    if not ops:
        typer.echo("No pending operations.")
        return
    for op in ops:
        typer.echo(f"  #{op.id} {op.issue_key} {op.field}: {op.old_value!r} -> {op.new_value!r}")


@app.command()
def execute(operation_ids: list[int]) -> None:
    """Apply pending write operations by id."""
    rt = build_runtime()
    applied = rt.writer.execute_pending(operation_ids)
    rt.session.commit()
    typer.echo(f"Executed {len(applied)} operation(s).")
