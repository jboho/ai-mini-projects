"""CLI: chunk + embed + index the corpus (or a PDF dir) and persist the index.

python scripts/ingest.py                       # corpus -> data/indices/corpus
python scripts/ingest.py --pdf-dir data/papers --name papers
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.chunkers import get_chunker  # noqa: E402
from rag.config import INDICES_DIR, load_default_config  # noqa: E402
from rag.embedder import embed_chunks, get_embedder  # noqa: E402
from rag.loader import load_corpus, load_pdf_document  # noqa: E402
from rag.vector_store import VectorStore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into a FAISS index")
    parser.add_argument("--config", default=None)
    parser.add_argument(
        "--pdf-dir", default=None, help="ingest PDFs from this dir instead of corpus"
    )
    parser.add_argument("--name", default="corpus", help="index name under data/indices/")
    args = parser.parse_args()

    config = load_default_config(args.config)
    if args.pdf_dir:
        documents = [load_pdf_document(p) for p in sorted(Path(args.pdf_dir).glob("*.pdf"))]
    else:
        documents = load_corpus()
    logger.info("Loaded %d documents", len(documents))

    embedder = get_embedder(config.embedder)
    chunker = get_chunker(config.chunker, embedder=embedder)
    chunks = [c for doc in documents for c in chunker.chunk(doc)]
    logger.info("Chunked into %d chunks (%s)", len(chunks), config.chunker.name)

    embeddings = embed_chunks(embedder, chunks, config.cache_key)
    store = VectorStore.from_embeddings(embeddings, chunks)
    out = INDICES_DIR / args.name
    store.save(out)
    logger.info("Saved index to %s.faiss (+ .json)", out)


if __name__ == "__main__":
    main()
