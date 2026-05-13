from __future__ import annotations
from typing import List, Tuple
import pathlib


class HtmlExtractor:
    """Extract readable text from HTML files, stripping tags."""

    def extract(self, path: str) -> List[Tuple[int, str]]:
        raw = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style", "head", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
        except ImportError:
            # Fallback: naive tag strip
            import re
            text = re.sub(r"<[^>]+>", " ", raw)

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return [(i + 1, para) for i, para in enumerate(paragraphs)] or [(1, "")]
