"""Batch-embed issues from SQLite into the persistent ChromaDB vector store.

Usage:
    python scripts/seed_vectors.py [--project APACHE] [--batch-size 128] [--limit N]

Reads issues from the SQLite DB built by ``convert_tawos.py``, embeds them with the
configured embedder (OpenAI when ``OPENAI_API_KEY`` is set, otherwise the offline
stub), and upserts them into ChromaDB at ``CHROMADB_PATH``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

import jira_copilot  # noqa: E402, F401 -- sets OpenMP / telemetry guards on import
from jira_copilot.config import get_settings  # noqa: E402
from jira_copilot.db.engine import get_engine, get_session  # noqa: E402
from jira_copilot.db.models import Issue, Project  # noqa: E402
from jira_copilot.services.vector_store import make_vector_store  # noqa: E402


def seed(project_key: str | None, batch_size: int, limit: int | None) -> int:
    settings = get_settings()
    engine = get_engine()
    store = make_vector_store(persist_path=settings.chromadb_path)
    with get_session(engine) as session:
        stmt = select(Issue)
        if project_key:
            proj = session.scalar(select(Project).where(Project.key == project_key))
            if proj is None:
                raise SystemExit(f"Project {project_key!r} not found in {settings.database_url}")
            stmt = stmt.where(Issue.project_id == proj.id)
        if limit:
            stmt = stmt.limit(limit)
        issues = list(session.scalars(stmt))
        if not issues:
            raise SystemExit("No issues to index. Run scripts/convert_tawos.py --sample first.")

        print(f"Embedding {len(issues)} issues (batch size {batch_size})...")
        return store.index_issues(issues, batch_size=batch_size)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ChromaDB with issue embeddings.")
    parser.add_argument("--project", default=None, help="Limit to one project key.")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--limit", type=int, default=None, help="Cap issues indexed (debug).")
    args = parser.parse_args()

    count = seed(args.project, args.batch_size, args.limit)
    print(f"Indexed {count} issues into {get_settings().chromadb_path}")


if __name__ == "__main__":
    main()
