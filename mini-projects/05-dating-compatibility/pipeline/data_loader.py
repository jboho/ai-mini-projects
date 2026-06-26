"""JSONL loading with per-record Pydantic validation and distribution stats."""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from .models import DatingPair

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_pairs(path: str | Path) -> list[DatingPair]:
    """Load and validate a JSONL file of dating pairs, failing fast on bad records."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Generate data with `python scripts/generate_data.py`."
        )
    pairs: list[DatingPair] = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            pairs.append(DatingPair.model_validate_json(line))
        except ValidationError as exc:
            raise ValueError(f"Invalid record at {path.name}:{lineno}: {exc}") from exc
    return pairs


def load_dataset(data_dir: str | Path | None = None) -> tuple[list[DatingPair], list[DatingPair]]:
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    return load_pairs(data_dir / "dating_pairs.jsonl"), load_pairs(data_dir / "eval_pairs.jsonl")


def distribution_stats(pairs: list[DatingPair]) -> dict:
    n = len(pairs)
    compatible = sum(p.label for p in pairs)
    stats = {
        "total": n,
        "compatible": compatible,
        "incompatible": n - compatible,
        "label_balance": round(compatible / n, 3) if n else 0.0,
        "by_category": dict(Counter(p.category for p in pairs)),
        "by_pair_type": dict(Counter(p.pair_type for p in pairs)),
    }
    return stats


def log_distribution(pairs: list[DatingPair], name: str = "dataset") -> dict:
    stats = distribution_stats(pairs)
    logger.info(
        "%s: %d pairs (%d compatible, balance %.2f)",
        name,
        stats["total"],
        stats["compatible"],
        stats["label_balance"],
    )
    logger.info("  categories: %s", stats["by_category"])
    return stats
