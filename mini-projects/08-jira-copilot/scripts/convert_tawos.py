"""Build the SQLite DB for the Jira copilot.

    python scripts/convert_tawos.py --sample          # synthetic dev dataset (no dump needed)
    python scripts/convert_tawos.py --dump tawos.sql  # convert a TAWOS MySQL dump (best-effort)

The real TAWOS dataset ships as a MySQL dump. For development the --sample mode
seeds a small TAWOS-shaped dataset so the full pipeline runs without it.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jira_copilot.config import DATA_DIR, get_settings  # noqa: E402
from jira_copilot.db.engine import get_engine, get_session, init_db  # noqa: E402
from jira_copilot.db.sample_data import build_sample  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Jira copilot SQLite DB")
    parser.add_argument("--sample", action="store_true", help="seed a synthetic dev dataset")
    parser.add_argument("--dump", default=None, help="path to a TAWOS MySQL .sql dump")
    parser.add_argument("--projects", default=None, help="comma-separated project keys to keep")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine(get_settings().database_url)
    init_db(engine)

    if args.sample or not args.dump:
        with get_session(engine) as session:
            build_sample(session)
        logger.info("Seeded synthetic TAWOS sample into the SQLite DB.")
        return

    logger.error(
        "MySQL dump conversion is not yet implemented. Use --sample for development, "
        "or load the dump into MySQL and export tables to CSV, then import. Dump: %s",
        args.dump,
    )


if __name__ == "__main__":
    main()
