from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional
import uuid


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict[str, Any]
    embedding: Optional[List[float]] = None

    @classmethod
    def create(cls, text: str, metadata: dict | None = None) -> "Chunk":
        return cls(id=str(uuid.uuid4()), text=text, metadata=metadata or {})

    def context_text(self) -> str:
        """Return text prefixed with its breadcrumb path for richer embedding."""
        breadcrumb = self.metadata.get("breadcrumb", "")
        return f"[{breadcrumb}]\n{self.text}" if breadcrumb else self.text


@dataclass
class Document:
    id: str
    path: str
    tenant_id: str
    chunks: List[Chunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @classmethod
    def create(cls, path: str, tenant_id: str = "default") -> "Document":
        return cls(id=str(uuid.uuid4()), path=path, tenant_id=tenant_id)


@dataclass
class SearchResult:
    chunk: Chunk
    score: float
    document_path: str
    tenant_id: str


@dataclass
class QueryResult:
    question: str
    answer: str
    sources: List[SearchResult]
    model: str = ""
