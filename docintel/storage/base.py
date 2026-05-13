from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from docintel.core.entities import Chunk, SearchResult


class VectorStore(ABC):

    @abstractmethod
    def upsert(self, chunks: List[Chunk], tenant_id: str, doc_path: str) -> None: ...

    @abstractmethod
    def search(
        self,
        vector: List[float],
        tenant_id: str,
        top_k: int,
        doc_paths: Optional[List[str]] = None,
    ) -> List[SearchResult]: ...

    @abstractmethod
    def delete_document(self, doc_path: str, tenant_id: str) -> None: ...

    @abstractmethod
    def save(self) -> None: ...

    @abstractmethod
    def load(self) -> None: ...
