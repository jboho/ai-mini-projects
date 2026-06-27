"""PDF text extraction with interchangeable parser backends.

Three backends are supported so the grid search can measure how extraction
quality affects downstream retrieval: pdfplumber (layout-aware, primary),
PyPDF2 (simple), and PyMuPDF/fitz (fast C implementation).

Each backend returns a list of :class:`PageText` whose ``start_char`` /
``end_char`` are offsets into the document produced by :func:`extract_full_text`,
so chunkers can map any character offset back to its source page.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .config import ParserType
from .models import PageText

logger = logging.getLogger(__name__)

PAGE_SEPARATOR = "\n"


def _extract_pdfplumber(path: Path) -> list[str]:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return [(page.extract_text() or "") for page in pdf.pages]


def _extract_pypdf2(path: Path) -> list[str]:
    from PyPDF2 import PdfReader

    reader = PdfReader(str(path))
    return [(page.extract_text() or "") for page in reader.pages]


def _extract_pymupdf(path: Path) -> list[str]:
    import fitz

    with fitz.open(path) as doc:
        return [page.get_text() for page in doc]


_BACKENDS = {
    ParserType.PDFPLUMBER: _extract_pdfplumber,
    ParserType.PYPDF2: _extract_pypdf2,
    ParserType.PYMUPDF: _extract_pymupdf,
}


def parse_pdf(path: str | Path, parser: ParserType | str = ParserType.PDFPLUMBER) -> list[PageText]:
    """Extract per-page text from ``path`` using the requested backend.

    Char offsets are assigned assuming pages are later joined by
    :data:`PAGE_SEPARATOR` (see :func:`extract_full_text`).
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    parser_type = ParserType(parser)
    extractor = _BACKENDS[parser_type]
    logger.info("Parsing %s with %s", pdf_path.name, parser_type.value)
    raw_pages = extractor(pdf_path)

    pages: list[PageText] = []
    cursor = 0
    for page_number, text in enumerate(raw_pages, start=1):
        normalized = text.strip()
        start = cursor
        end = start + len(normalized)
        pages.append(
            PageText(page_number=page_number, text=normalized, start_char=start, end_char=end)
        )
        cursor = end + len(PAGE_SEPARATOR)

    logger.info("Extracted %d pages (%d chars)", len(pages), cursor)
    return pages


def extract_full_text(pages: list[PageText]) -> str:
    """Join page texts into the single document string char offsets refer to."""
    return PAGE_SEPARATOR.join(page.text for page in pages)


def page_for_offset(pages: list[PageText], offset: int) -> int:
    """Return the 1-based page number whose char span contains ``offset``."""
    for page in pages:
        if page.start_char <= offset <= page.end_char:
            return page.page_number
    return pages[-1].page_number if pages else 0
