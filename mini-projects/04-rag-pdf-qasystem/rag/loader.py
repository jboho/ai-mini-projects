"""Document loading from the pre-parsed corpus JSON (primary) or PDFs (app use).

A corpus paper is ``{title, sections: [{section_id, text}, ...]}``. We join the
section texts into one document string and record each section's character span,
so a chunk's overlapping section ids can be computed for qrel ground-truth
matching (a chunk is relevant to a query if it overlaps the qrel's section).
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import CORPUS_DIR
from .models import Document, Section

SECTION_SEPARATOR = "\n\n"


def load_corpus_document(path: str | Path) -> Document:
    """Load one ``corpus/{paper_id}.json`` into a Document with section spans."""
    path = Path(path)
    raw = json.loads(path.read_text())
    doc_id = path.stem

    parts: list[str] = []
    sections: list[Section] = []
    cursor = 0
    for sec in raw.get("sections", []):
        text = sec.get("text", "")
        start = cursor
        end = start + len(text)
        sections.append(
            Section(index=int(sec["section_id"]), title="", start_char=start, end_char=end)
        )
        parts.append(text)
        cursor = end + len(SECTION_SEPARATOR)

    return Document(
        doc_id=doc_id,
        text=SECTION_SEPARATOR.join(parts),
        title=raw.get("title", ""),
        sections=sections,
    )


def load_corpus(corpus_dir: str | Path | None = None) -> list[Document]:
    """Load every downloaded corpus paper."""
    corpus_dir = Path(corpus_dir) if corpus_dir else CORPUS_DIR
    return [load_corpus_document(p) for p in sorted(corpus_dir.glob("*.json"))]


def load_pdf_document(path: str | Path) -> Document:
    """Load a PDF into a single-section Document (for the Streamlit upload path)."""
    import fitz

    path = Path(path)
    with fitz.open(path) as doc:
        text = "\n".join(page.get_text() for page in doc)
    return Document(
        doc_id=path.stem,
        text=text,
        sections=[Section(index=0, start_char=0, end_char=len(text))],
    )


def sections_for_span(sections: list[Section], start: int, end: int) -> list[int]:
    """Return the indices of sections whose char span overlaps ``[start, end)``."""
    return [s.index for s in sections if s.start_char < end and start < s.end_char]
