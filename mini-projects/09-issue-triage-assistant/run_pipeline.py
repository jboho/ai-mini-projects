"""Issue Triage Assistant CLI.

python run_pipeline.py --mode ingest [--data-dir ./data]   # CSVs, or synthetic sample
python run_pipeline.py --mode classify
python run_pipeline.py --mode triage [--issue SPARK-1001]   # one issue, or all
python run_pipeline.py --mode monitor [--project SPARK]
python run_pipeline.py --mode report [--type daily] [--project SPARK]
python run_pipeline.py --mode evaluate [--sample 100]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline  # noqa: E402, F401 -- sets env guards on import
from pipeline.config import DATA_DIR, get_settings  # noqa: E402
from pipeline.db.engine import get_engine, get_session, init_db  # noqa: E402
from pipeline.db.sample_data import build_sample  # noqa: E402

ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "evaluation" / "results.json"


def _engine():
    settings = get_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine(settings.database_url)
    init_db(engine)
    return engine


def _mode_ingest(args) -> None:
    from pipeline.ingest.loader import ingest_dir

    settings = get_settings()
    engine = _engine()
    data_dir = Path(args.data_dir) if args.data_dir else DATA_DIR
    issues_csv = data_dir / "issues.csv"

    with get_session(engine) as session:
        if issues_csv.exists():
            counts = ingest_dir(data_dir, settings.project_keys, settings.chunksize, session)
            print(f"Ingested from {data_dir}: {counts}")
        else:
            build_sample(session)
            print(f"No CSVs at {data_dir}; seeded synthetic sample (14 issues).")


def _mode_classify(args) -> None:
    from sqlalchemy import select

    from pipeline.client import get_llm
    from pipeline.db.tables import JiraIssue
    from pipeline.services.classifier import classify_issue

    llm = get_llm()
    counts: dict[str, int] = {}
    with get_session(_engine()) as session:
        issues = list(session.scalars(select(JiraIssue)))
        for issue in issues:
            result = classify_issue(issue.summary, issue.description, issue.components, llm=llm)
            issue.classification = result.category
            issue.confidence = result.confidence
            counts[result.category] = counts.get(result.category, 0) + 1
    print(f"Classified {sum(counts.values())} issues (llm={'on' if llm else 'off'}):")
    for category, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {category:18} {n}")


def _mode_triage(args) -> None:
    from sqlalchemy import select

    from pipeline.agents.crew import TriageCrew
    from pipeline.client import get_llm
    from pipeline.db.tables import JiraIssue

    with get_session(_engine()) as session:
        crew = TriageCrew(session, llm=get_llm())
        if args.issue:
            result = crew.run_triage(args.issue)
            print(
                json.dumps(result, indent=2, default=str)
                if result
                else f"Issue {args.issue} not found."
            )
        else:
            keys = [i.key for i in session.scalars(select(JiraIssue))]
            results = crew.run_batch_triage(keys)
            recurring = sum(1 for r in results if r.get("is_recurring"))
            print(f"Triaged {len(results)} issues; {recurring} recurring (duplicate signature).")
            for r in results:
                print(f"  {r['issue_key']:14} {r['classification']:16} conf={r['confidence']:.2f}")


def _default_alert_rules():
    from pipeline.models import AlertRule

    return [
        AlertRule(
            name="high-severity",
            priority_threshold="Critical",
            channels=["slack", "pagerduty"],
            cooldown_minutes=60,
        ),
        AlertRule(
            name="memory-issues",
            priority_threshold="Major",
            categories=["memory"],
            channels=["slack"],
            cooldown_minutes=120,
        ),
    ]


def _mode_monitor(args) -> None:
    from pipeline.agents.crew import TriageCrew
    from pipeline.client import get_llm
    from pipeline.db.tables import Incident
    from pipeline.services.notifier import NotificationManager

    rules = _default_alert_rules()
    manager = NotificationManager()  # dry-run by default -> simulated sends
    with get_session(_engine()) as session:
        crew = TriageCrew(session, llm=get_llm())
        results = crew.run_monitoring_cycle(project_key=args.project)
        print(f"Monitoring cycle triaged {len(results)} active issues.")
        notifications = []
        for r in results:
            incident = session.get(Incident, r["incident_id"])
            if incident is not None:
                notifications.extend(manager.notify_for_incident(incident, rules))
        print(
            f"Dispatched {len(notifications)} notifications ({manager.dry_run and 'simulated' or 'live'}):"
        )
        for n in notifications:
            print(f"  [{n['rule']}] {n['channel']:10} {n['status']}")


def _mode_report(args) -> None:
    from pipeline.agents.crew import TriageCrew
    from pipeline.db.tables import Report

    with get_session(_engine()) as session:
        crew = TriageCrew(session)
        report = crew.report(project_key=args.project)
        session.add(
            Report(
                report_type=args.type,
                title=f"{args.type.title()} triage report",
                content=json.dumps(report, indent=2, default=str),
                metrics_json=json.dumps(report, default=str),
                project_key=args.project or "",
            )
        )
    print(json.dumps(report, indent=2, default=str))


def _mode_evaluate(args) -> None:
    from pipeline.client import get_llm
    from pipeline.evaluation import metrics

    llm = get_llm()
    with get_session(_engine()) as session:
        results = metrics.run_all(session, sample_size=args.sample)
        results["judge_enabled"] = llm is not None
        if llm is not None:
            results["judge_sample"] = _judge_sample(session, llm)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps(results, indent=2, default=str))
    print(f"\nWrote {RESULTS_PATH.relative_to(ROOT)}")


def _judge_sample(session, llm) -> list[dict]:
    """Judge root-cause quality for a few triaged incidents (live LLM only)."""
    from sqlalchemy import select

    from pipeline.db.tables import Incident
    from pipeline.evaluation.judge import judge_root_cause

    out = []
    for incident in session.scalars(select(Incident).limit(3)):
        if not incident.root_cause:
            continue
        out.append(
            {
                "incident_id": incident.id,
                "scores": judge_root_cause(incident.title, incident.root_cause, llm),
            }
        )
    return out


_MODES = {
    "ingest": _mode_ingest,
    "classify": _mode_classify,
    "triage": _mode_triage,
    "monitor": _mode_monitor,
    "report": _mode_report,
    "evaluate": _mode_evaluate,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-powered issue triage assistant")
    parser.add_argument("--mode", required=True, choices=list(_MODES))
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--issue", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--type", default="daily")
    parser.add_argument("--sample", type=int, default=100)
    args = parser.parse_args()
    _MODES[args.mode](args)


if __name__ == "__main__":
    main()
