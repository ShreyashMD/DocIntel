from __future__ import annotations
from typing import List, Tuple


class PdfExtractor:
    """Extract text from PDF files page-by-page using pypdf."""

    def extract(self, path: str) -> List[Tuple[int, str]]:
        """Return list of (page_number, text) tuples (1-indexed)."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("Install pypdf: pip install pypdf")

        reader = PdfReader(path)
        pages: List[Tuple[int, str]] = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages.append((i, text))
        return pages

    def extract_full(self, path: str) -> str:
        """Return the entire document as a single string with page markers."""
        pages = self.extract(path)
        return "\n\n".join(f"[Page {n}]\n{text}" for n, text in pages)
