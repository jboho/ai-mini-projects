"""Issue Triage Assistant CLI.

python run_pipeline.py --mode ingest [--data-dir ./data]   # CSVs, or synthetic sample
python run_pipeline.py --mode classify
python run_pipeline.py --mode triage --issue SPARK-1001
python run_pipeline.py --mode monitor --hours 24
python run_pipeline.py --mode report --type daily
python run_pipeline.py --mode evaluate --sample 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline  # noqa: E402, F401 -- sets env guards on import
from pipeline.config import DATA_DIR, get_settings  # noqa: E402
from pipeline.db.engine import get_engine, get_session, init_db  # noqa: E402
from pipeline.db.sample_data import build_sample  # noqa: E402


def _mode_ingest(args) -> None:
    from pipeline.ingest.loader import ingest_dir

    settings = get_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine(settings.database_url)
    init_db(engine)
    data_dir = Path(args.data_dir) if args.data_dir else DATA_DIR
    issues_csv = data_dir / "issues.csv"

    with get_session(engine) as session:
        if issues_csv.exists():
            counts = ingest_dir(data_dir, settings.project_keys, settings.chunksize, session)
            print(f"Ingested from {data_dir}: {counts}")
        else:
            build_sample(session)
            print(f"No CSVs at {data_dir}; seeded synthetic sample (14 issues).")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-powered issue triage assistant")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["ingest", "classify", "triage", "monitor", "report", "evaluate"],
    )
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--issue", default=None)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--type", default="daily")
    parser.add_argument("--sample", type=int, default=100)
    args = parser.parse_args()

    if args.mode == "ingest":
        _mode_ingest(args)
    else:
        print(f"Mode '{args.mode}' is implemented in a later phase.")


if __name__ == "__main__":
    main()
