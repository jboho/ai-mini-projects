"""Generate the synthetic dating dataset into data/.

python scripts/generate_data.py                 # 6000 train + 1469 eval
python scripts/generate_data.py --train 6000 --eval 1469
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.data_gen import dataset_metadata, generate_pairs  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _write(pairs: list[dict], name: str) -> None:
    path = DATA_DIR / name
    path.write_text("\n".join(json.dumps(p) for p in pairs))
    meta = dataset_metadata(pairs)
    (DATA_DIR / name.replace(".jsonl", "_metadata.json")).write_text(json.dumps(meta, indent=2))
    logger.info("%s: %d pairs (%d compatible)", name, meta["count"], meta["compatible"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic dating dataset")
    parser.add_argument("--train", type=int, default=6000)
    parser.add_argument("--eval", type=int, default=1469)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write(generate_pairs(args.train, seed=42), "dating_pairs.jsonl")
    _write(generate_pairs(args.eval, seed=99), "eval_pairs.jsonl")


if __name__ == "__main__":
    main()
