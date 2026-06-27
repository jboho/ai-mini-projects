"""Download the Vectara Open RAG Benchmark (arxiv split) from HuggingFace.

The dataset ships pre-parsed corpus JSON per paper, so the full pipeline can run
without downloading any PDFs. We fetch the four metadata files plus a subset of
corpus papers (chosen from the qrels so every downloaded paper has ground truth).

Usage:
    python scripts/download_dataset.py --limit 50
    python scripts/download_dataset.py --limit 1000        # full set
    python scripts/download_dataset.py --limit 50 --with-pdfs   # also fetch PDFs
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from huggingface_hub import hf_hub_download  # noqa: E402

from rag.config import CORPUS_DIR, DATA_DIR, PAPERS_DIR  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REPO_ID = "vectara/open_ragbench"
PREFIX = "pdf/arxiv"
METADATA_FILES = ["queries.json", "qrels.json", "answers.json", "pdf_urls.json"]


def _download_json(remote_name: str, dest_dir: Path) -> dict:
    path = hf_hub_download(REPO_ID, f"{PREFIX}/{remote_name}", repo_type="dataset")
    data = json.loads(Path(path).read_text())
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / remote_name).write_text(json.dumps(data))
    return data


def _select_paper_ids(qrels: dict, limit: int) -> list[str]:
    """Ordered, de-duplicated doc_ids referenced by qrels, capped at ``limit``."""
    seen: dict[str, None] = {}
    for rel in qrels.values():
        doc_id = rel["doc_id"]
        if doc_id not in seen:
            seen[doc_id] = None
        if len(seen) >= limit:
            break
    return list(seen)


def _download_corpus(paper_ids: list[str]) -> list[str]:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for i, pid in enumerate(paper_ids, start=1):
        try:
            path = hf_hub_download(REPO_ID, f"{PREFIX}/corpus/{pid}.json", repo_type="dataset")
        except OSError as exc:  # HF HTTP/entry errors derive from OSError; skip the paper
            logger.warning("Skipping corpus %s: %s", pid, exc)
            continue
        (CORPUS_DIR / f"{pid}.json").write_text(Path(path).read_text())
        downloaded.append(pid)
        if i % 25 == 0:
            logger.info("  ... %d/%d corpus files", i, len(paper_ids))
    return downloaded


def _download_pdfs(paper_ids: list[str], pdf_urls: dict) -> None:
    import requests

    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    for pid in paper_ids:
        url = pdf_urls.get(pid)
        if not url:
            continue
        dest = PAPERS_DIR / f"{pid}.pdf"
        if dest.exists():
            continue
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        except requests.RequestException as exc:
            logger.warning("PDF download failed for %s: %s", pid, exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Vectara open_ragbench (arxiv)")
    parser.add_argument("--limit", type=int, default=50, help="number of papers to fetch")
    parser.add_argument("--with-pdfs", action="store_true", help="also download arXiv PDFs")
    args = parser.parse_args()

    logger.info("Downloading metadata to %s", DATA_DIR)
    queries = _download_json("queries.json", DATA_DIR)
    qrels = _download_json("qrels.json", DATA_DIR)
    _download_json("answers.json", DATA_DIR)
    pdf_urls = _download_json("pdf_urls.json", DATA_DIR)

    paper_ids = _select_paper_ids(qrels, args.limit)
    logger.info("Selected %d papers; downloading corpus...", len(paper_ids))
    downloaded = _download_corpus(paper_ids)

    selected = set(downloaded)
    eval_queries = [qid for qid, rel in qrels.items() if rel["doc_id"] in selected]
    logger.info(
        "Done: %d papers, %d/%d queries have ground truth in this subset.",
        len(downloaded),
        len(eval_queries),
        len(queries),
    )

    if args.with_pdfs:
        logger.info("Downloading %d PDFs...", len(downloaded))
        _download_pdfs(downloaded, pdf_urls)


if __name__ == "__main__":
    main()
