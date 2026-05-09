from __future__ import annotations
import json
import pathlib
from typing import Any, Dict, List, Optional

import numpy as np

from docintel.core.entities import Chunk, SearchResult
from docintel.storage.base import VectorStore


class MemoryVectorStore(VectorStore):
    """
    In-memory vector store with optional JSON persistence.

    Index structure (per tenant):
        _index[tenant_id] = [
            {"chunk": {...}, "doc_path": str, "vector": [floats]},
            ...
        ]
    """

    def __init__(self, persist_dir: Optional[str] = None) -> None:
        self._index: Dict[str, List[Dict[str, Any]]] = {}
        self._persist_path: Optional[pathlib.Path] = None
        if persist_dir:
            p = pathlib.Path(persist_dir)
            p.mkdir(parents=True, exist_ok=True)
            self._persist_path = p / "docintel_index.json"

    # ------------------------------------------------------------------

    def upsert(self, chunks: List[Chunk], tenant_id: str, doc_path: str) -> None:
        if tenant_id not in self._index:
            self._index[tenant_id] = []
        # Remove stale entries for this doc first
        self._index[tenant_id] = [
            e for e in self._index[tenant_id] if e["doc_path"] != doc_path
        ]
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            self._index[tenant_id].append(
                {
                    "chunk": {
                        "id": chunk.id,
                        "text": chunk.text,
                        "metadata": {k: v for k, v in chunk.metadata.items() if k != "_embed_text"},
                    },
                    "doc_path": doc_path,
                    "vector": chunk.embedding,
                }
            )

    def search(self, vector: List[float], tenant_id: str, top_k: int) -> List[SearchResult]:
        entries = self._index.get(tenant_id, [])
        if not entries:
            return []

        q = np.array(vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        scores: list[tuple[float, dict]] = []
        for entry in entries:
            v = np.array(entry["vector"], dtype=np.float32)
            v_norm = np.linalg.norm(v)
            if v_norm == 0:
                continue
            score = float(np.dot(q, v) / (q_norm * v_norm))
            scores.append((score, entry))

        scores.sort(key=lambda x: x[0], reverse=True)
        results: list[SearchResult] = []
        for score, entry in scores[:top_k]:
            cd = entry["chunk"]
            chunk = Chunk(
                id=cd["id"],
                text=cd["text"],
                metadata=cd["metadata"],
            )
            results.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                    document_path=entry["doc_path"],
                    tenant_id=tenant_id,
                )
            )
        return results

    def delete_document(self, doc_path: str, tenant_id: str) -> None:
        if tenant_id in self._index:
            self._index[tenant_id] = [
                e for e in self._index[tenant_id] if e["doc_path"] != doc_path
            ]

    # ------------------------------------------------------------------
    # Persistence

    def save(self) -> None:
        if self._persist_path is None:
            return
        self._persist_path.write_text(json.dumps(self._index), encoding="utf-8")

    def load(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        self._index = json.loads(self._persist_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------

    @property
    def total_chunks(self) -> int:
        return sum(len(v) for v in self._index.values())

    def tenants(self) -> list[str]:
        return list(self._index.keys())
