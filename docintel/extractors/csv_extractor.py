from __future__ import annotations
import csv
import pathlib
from typing import List, Tuple


class CsvExtractor:
    """Extract CSV files as Markdown tables, chunked into pages of 200 rows."""

    ROWS_PER_PAGE = 200

    def extract(self, path: str) -> List[Tuple[int, str]]:
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(text.splitlines())
        rows = [r for r in reader if any(c.strip() for c in r)]
        if not rows:
            return [(1, "")]

        headers = rows[0]
        max_cols = max(len(r) for r in rows)
        headers += [""] * (max_cols - len(headers))

        header_md = "| " + " | ".join(headers) + " |"
        sep_md    = "| " + " | ".join(["---"] * max_cols) + " |"

        pages: list[tuple[int, str]] = []
        data_rows = rows[1:]
        for i in range(0, max(1, len(data_rows)), self.ROWS_PER_PAGE):
            chunk = data_rows[i : i + self.ROWS_PER_PAGE]
            lines = [header_md, sep_md]
            for row in chunk:
                padded = row + [""] * (max_cols - len(row))
                lines.append("| " + " | ".join(padded[:max_cols]) + " |")
            pages.append((i // self.ROWS_PER_PAGE + 1, "\n".join(lines)))

        return pages
