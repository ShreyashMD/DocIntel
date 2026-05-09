from __future__ import annotations
import re
from typing import List

from docintel.core.entities import Chunk


# Patterns that identify section headings
_HEADING_PATTERNS = [
    re.compile(r"^#{1,6}\s+(.+)$"),                        # Markdown: ## Title
    re.compile(r"^([A-Z][A-Z\s\-]{4,80})$"),               # ALL CAPS heading
    re.compile(r"^(\d+(?:\.\d+)*)\s{1,4}([A-Z].{3,80})$"), # 1.2.3 Heading
    re.compile(r"^([A-Z][a-z].{3,60}):?\s*$"),              # Title Case line
]


def _is_heading(line: str) -> str | None:
    """Return cleaned heading text if line looks like a heading, else None."""
    line = line.strip()
    if not line or len(line) > 120:
        return None
    for pat in _HEADING_PATTERNS:
        m = pat.match(line)
        if m:
            return m.group(1) if m.lastindex else line
    return None


def _split_into_token_chunks(text: str, size: int, overlap: int) -> List[str]:
    """Split text into overlapping word-based chunks approximating token count."""
    words = text.split()
    if not words:
        return []
    chunks, start = [], 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += size - overlap
    return chunks


class HierarchicalChunker:
    """
    Parses raw document text into contextualised chunks.

    Algorithm:
    1. Walk each line, detecting section headings.
    2. Maintain a breadcrumb stack (heading hierarchy).
    3. Accumulate paragraph text under the current heading.
    4. When accumulated text exceeds chunk_size, split into overlapping sub-chunks.
    5. Each chunk carries its breadcrumb path and page number in metadata.

    If a document-level summary is provided it is prepended to every chunk's
    embedding text (Contextual Retrieval / Pseudo-Instruction Chunking).
    """

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 80, min_chunk_size: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(
        self,
        text: str,
        doc_path: str = "",
        page: int | None = None,
        doc_summary: str = "",
    ) -> List[Chunk]:
        lines = text.splitlines()
        breadcrumbs: list[str] = []
        buffer: list[str] = []
        chunks: list[Chunk] = []

        def flush(current_breadcrumbs: list[str]) -> None:
            raw = " ".join(buffer).strip()
            if not raw:
                return
            sub_chunks = _split_into_token_chunks(raw, self.chunk_size, self.chunk_overlap)
            for idx, sc in enumerate(sub_chunks):
                if len(sc.split()) < self.min_chunk_size // 4:
                    continue
                breadcrumb = " > ".join(current_breadcrumbs) if current_breadcrumbs else doc_path
                meta = {
                    "breadcrumb": breadcrumb,
                    "doc_path": doc_path,
                    "sub_chunk_index": idx,
                }
                if page is not None:
                    meta["page"] = page

                # Prepend doc summary for Contextual Retrieval
                embed_text = f"[Document: {doc_summary}]\n[Section: {breadcrumb}]\n{sc}" if doc_summary else sc
                chunk = Chunk.create(sc, meta)
                chunk.metadata["_embed_text"] = embed_text
                chunks.append(chunk)

        for line in lines:
            heading = _is_heading(line)
            if heading:
                flush(list(breadcrumbs))
                buffer.clear()
                # Update breadcrumb depth heuristic: markdown # depth
                md_match = re.match(r"^(#{1,6})\s+", line)
                if md_match:
                    depth = len(md_match.group(1)) - 1
                    breadcrumbs = breadcrumbs[:depth]
                else:
                    # Non-markdown: treat as same-level unless stack empty
                    if len(breadcrumbs) > 2:
                        breadcrumbs = breadcrumbs[:2]
                breadcrumbs.append(heading)
            else:
                buffer.append(line)

        flush(list(breadcrumbs))
        return chunks

    def chunk_pages(
        self,
        pages: list[tuple[int, str]],
        doc_path: str = "",
        doc_summary: str = "",
    ) -> List[Chunk]:
        all_chunks: list[Chunk] = []
        for page_num, text in pages:
            page_chunks = self.chunk(text, doc_path=doc_path, page=page_num, doc_summary=doc_summary)
            all_chunks.extend(page_chunks)
        return all_chunks
