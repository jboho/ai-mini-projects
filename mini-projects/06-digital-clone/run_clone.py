"""CLI for the digital clone system.

Modes:
  learn        Download emails + textbooks, build the style profile + RAG index
  query        Answer a single question (needs a chat key)
  demo         Run a few sample questions
  test-agents  Offline smoke test of the orchestration (no LLM)

    python run_clone.py --mode learn --employee vince.kaminski
    python run_clone.py --mode query --employee vince.kaminski --question "What is gradient descent?"
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rich.console import Console

from agents.planner import DigitalClone
from core.chunker import load_textbook_chunks
from core.email_loader import load_employee_emails
from core.models import StyleProfile
from core.style_features import build_style_profile
from core.vectorstore import KnowledgeStore

console = Console()
ROOT = Path(__file__).resolve().parent
PROFILE_DIR = ROOT / "data" / "models"


def _profile_path(employee: str) -> Path:
    return PROFILE_DIR / f"style_profile_{employee}.json"


def mode_learn(employee: str, n_emails: int, n_chunks: int) -> None:
    emails = load_employee_emails(employee, limit=n_emails)
    if not emails:
        console.print(f"[red]No sent emails found for {employee}.[/red]")
        return
    profile = build_style_profile(employee, emails)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _profile_path(employee).write_text(profile.model_dump_json(indent=2))
    console.print(
        f"[green]Learned style from {len(emails)} emails -> {_profile_path(employee).name}[/green]"
    )

    chunks = load_textbook_chunks(target_chunks=n_chunks)
    KnowledgeStore.build(chunks).save()
    console.print(f"[green]Built knowledge index with {len(chunks)} chunks.[/green]")


def _load_clone(employee: str) -> DigitalClone:
    profile = StyleProfile.model_validate_json(_profile_path(employee).read_text())
    store = KnowledgeStore.load()
    return DigitalClone(store, profile, employee)


def _print_result(result) -> None:
    ev = result.evaluation
    console.print(f"\n[bold]Decision:[/bold] {ev.decision}  [dim]({ev.reasoning})[/dim]")
    if result.response:
        console.print(f"\n[bold green]Response:[/bold green]\n{result.response}")
    if result.fallback:
        fb = result.fallback
        console.print(f"\n[bold yellow]Fallback:[/bold yellow] {fb.trigger_reason}")
        console.print(f"Book a call: {fb.calendar_link}")
        for slot in fb.available_slots:
            console.print(f"  • {slot}")
    console.print(f"[dim]{result.processing_time_ms:.0f} ms[/dim]")


def mode_query(employee: str, question: str) -> None:
    _print_result(_load_clone(employee).query(question))


def mode_demo(employee: str) -> None:
    clone = _load_clone(employee)
    for q in [
        "What is gradient descent and how does it work?",
        "Explain how a hash table achieves constant-time lookup.",
        "What is the airspeed velocity of an unladen swallow?",
    ]:
        console.print(f"\n[bold cyan]Q:[/bold cyan] {q}")
        _print_result(clone.query(q))


def mode_test_agents() -> None:
    from agents.evaluator_agent import EvaluatorAgent
    from agents.fallback_agent import FallbackAgent

    fb = FallbackAgent().build("test", "demo query", "demo@example.com")
    assert fb.available_slots and fb.calendar_link
    assert EvaluatorAgent().config.deliver_threshold == 0.75
    console.print("[green]Agent wiring OK (evaluator + fallback verified offline).[/green]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Digital clone CLI")
    parser.add_argument("--mode", choices=["learn", "query", "demo", "test-agents"], default="demo")
    parser.add_argument("--employee", default="vince.kaminski")
    parser.add_argument("--question", default="What is gradient descent?")
    parser.add_argument("--n-emails", type=int, default=300)
    parser.add_argument("--n-chunks", type=int, default=900)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s"
    )

    if args.mode == "learn":
        mode_learn(args.employee, args.n_emails, args.n_chunks)
    elif args.mode == "query":
        mode_query(args.employee, args.question)
    elif args.mode == "demo":
        mode_demo(args.employee)
    else:
        mode_test_agents()


if __name__ == "__main__":
    main()
