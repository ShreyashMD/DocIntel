from __future__ import annotations
from typing import List, Tuple
import pathlib


class TextExtractor:
    """Extract text from plain-text files (.txt, .md, .rst, etc.)."""

    SUPPORTED = {".txt", ".md", ".rst", ".log", ".csv"}

    def extract(self, path: str) -> List[Tuple[int, str]]:
        """Return list of (chunk_index, text) tuples split by blank lines."""
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return [(i + 1, para) for i, para in enumerate(paragraphs)]

    def extract_full(self, path: str) -> str:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
