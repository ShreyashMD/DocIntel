from __future__ import annotations
import json
import os
import pathlib
import threading
from typing import Any, Dict, List, Optional

import numpy as np

from docintel.core.entities import Chunk, SearchResult
from docintel.storage.base import VectorStore


_SCHEMA_VERSION = 1


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
        self._lock = threading.RLock()
        if persist_dir:
            p = pathlib.Path(persist_dir)
            p.mkdir(parents=True, exist_ok=True)
            self._persist_path = p / "docintel_index.json"

    # ------------------------------------------------------------------

    def upsert(self, chunks: List[Chunk], tenant_id: str, doc_path: str) -> None:
        with self._lock:
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
                            "metadata": {
                                k: v for k, v in chunk.metadata.items() if k != "_embed_text"
                            },
                        },
                        "doc_path": doc_path,
                        "vector": chunk.embedding,
                    }
                )

    def search(
        self,
        vector: List[float],
        tenant_id: str,
        top_k: int,
        doc_paths: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        with self._lock:
            entries = list(self._index.get(tenant_id, []))
        if doc_paths is not None:
            allowed = set(doc_paths)
            entries = [e for e in entries if e["doc_path"] in allowed]
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
        with self._lock:
            if tenant_id in self._index:
                self._index[tenant_id] = [
                    e for e in self._index[tenant_id] if e["doc_path"] != doc_path
                ]

    # ------------------------------------------------------------------
    # Persistence

    def save(self) -> None:
        if self._persist_path is None:
            return
        payload = {"schema_version": _SCHEMA_VERSION, "index": self._index}
        tmp_path = self._persist_path.with_suffix(".tmp")
        with self._lock:
            tmp_path.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(tmp_path, self._persist_path)

    def load(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            payload = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corrupt docintel index: {self._persist_path}") from exc

        with self._lock:
            if isinstance(payload, dict) and "schema_version" in payload:
                if payload["schema_version"] != _SCHEMA_VERSION:
                    raise ValueError(
                        "Unsupported docintel index schema version: "
                        f"{payload['schema_version']}"
                    )
                self._index = payload.get("index", {})
            else:
                # Backward compatibility with the original plain-index format.
                self._index = payload

    # ------------------------------------------------------------------

    @property
    def total_chunks(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._index.values())

    def tenants(self) -> list[str]:
        with self._lock:
            return list(self._index.keys())
