from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional

import numpy as np

from docintel.core.entities import Chunk, SearchResult
from docintel.storage.base import VectorStore

logger = logging.getLogger(__name__)

_INSERT_SQL = """
INSERT INTO docintel_chunks (id, tenant_id, doc_path, text, metadata, embedding)
VALUES (%s, %s, %s, %s, %s, %s)
"""

_DELETE_SQL = """
DELETE FROM docintel_chunks WHERE doc_path = %s AND tenant_id = %s
"""

_SEARCH_SQL = """
SELECT id, text, metadata, doc_path, tenant_id,
       1 - (embedding <=> %s) AS score
FROM docintel_chunks
WHERE tenant_id = %s
ORDER BY embedding <=> %s
LIMIT %s
"""

_SEARCH_FILTERED_SQL = """
SELECT id, text, metadata, doc_path, tenant_id,
       1 - (embedding <=> %s) AS score
FROM docintel_chunks
WHERE tenant_id = %s
  AND doc_path = ANY(%s)
ORDER BY embedding <=> %s
LIMIT %s
"""

_TOTAL_SQL = "SELECT COUNT(*) FROM docintel_chunks"
_TENANTS_SQL = "SELECT DISTINCT tenant_id FROM docintel_chunks ORDER BY tenant_id"


class _PooledConn:
    """Context manager: checks out a connection, registers vector adapter, returns it."""

    def __init__(self, pool: Any, register_vector: Any) -> None:
        self._pool = pool
        self._register_vector = register_vector
        self._conn = None
        self._cur = None

    def __enter__(self):
        self._conn = self._pool.getconn()
        self._register_vector(self._conn)
        self._cur = self._conn.cursor()
        return self._conn, self._cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cur.close()
        if exc_type is not None:
            self._conn.rollback()
        self._pool.putconn(self._conn)
        return False


class PgVectorStore(VectorStore):
    """
    PostgreSQL + pgvector backed vector store.

    Install extras: pip install 'docintel[postgres]'
    """

    def __init__(
        self,
        db_url: str,
        embedding_dim: int = 3072,
        pool_min: int = 2,
        pool_max: int = 10,
    ) -> None:
        try:
            import psycopg2
            import psycopg2.pool
            from pgvector.psycopg2 import register_vector
        except ImportError as exc:
            raise ImportError(
                "pgvector backend requires extra packages. "
                "Install with: pip install 'docintel[postgres]'"
            ) from exc

        self._dim = embedding_dim
        self._register_vector = register_vector
        self._pool = psycopg2.pool.ThreadedConnectionPool(pool_min, pool_max, dsn=db_url)
        self._migrate()

    # ------------------------------------------------------------------

    def _conn(self) -> _PooledConn:
        return _PooledConn(self._pool, self._register_vector)

    def _migrate(self) -> None:
        with self._conn() as (conn, cur):
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Check if the table already exists and what embedding dim it was built with.
            cur.execute("""
                SELECT a.atttypmod
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                WHERE c.relname = 'docintel_chunks'
                  AND a.attname = 'embedding'
                  AND a.attnum > 0
            """)
            row = cur.fetchone()
            existing_dim: int | None = row[0] if row else None

            if existing_dim is not None and existing_dim != self._dim:
                # Embedding provider changed — old vectors live in a different space
                # and cannot be mixed with or compared to new embeddings.
                # Drop everything so the table is recreated with the correct dim.
                logger.warning(
                    "Embedding dim changed %d → %d: dropping docintel_chunks "
                    "and document_library records so documents can be re-ingested.",
                    existing_dim, self._dim,
                )
                cur.execute("DROP TABLE IF EXISTS docintel_chunks CASCADE")
                cur.execute(
                    "DELETE FROM document_library WHERE status IN ('ready', 'ingesting', 'failed')"
                )
                conn.commit()

            cur.execute(
                "CREATE TABLE IF NOT EXISTS docintel_chunks ("
                "  id         TEXT         PRIMARY KEY,"
                "  tenant_id  TEXT         NOT NULL,"
                "  doc_path   TEXT         NOT NULL,"
                "  text       TEXT         NOT NULL,"
                "  metadata   JSONB        NOT NULL DEFAULT '{}',"
                f" embedding  vector({self._dim}) NOT NULL,"
                "  created_at TIMESTAMPTZ  NOT NULL DEFAULT now()"
                ")"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS docintel_chunks_tenant_idx "
                "ON docintel_chunks (tenant_id)"
            )
            # HNSW/IVFFlat indexes are capped at 2000 dims by pgvector.
            # For higher-dim providers (Gemini/OpenAI at 3072) we fall back to
            # sequential scans, which are fine up to ~100k chunks.
            if self._dim <= 2000:
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS docintel_chunks_embedding_idx "
                    "ON docintel_chunks USING hnsw (embedding vector_cosine_ops)"
                )
            conn.commit()
        logger.info("pgvector migration applied", extra={"dim": self._dim})

    # ------------------------------------------------------------------

    def upsert(self, chunks: List[Chunk], tenant_id: str, doc_path: str) -> None:
        rows = [
            (
                chunk.id,
                tenant_id,
                doc_path,
                chunk.text,
                json.dumps({k: v for k, v in chunk.metadata.items() if k != "_embed_text"}),
                np.array(chunk.embedding, dtype=np.float32),
            )
            for chunk in chunks
            if chunk.embedding is not None
        ]
        if not rows:
            return
        with self._conn() as (conn, cur):
            cur.execute(_DELETE_SQL, (doc_path, tenant_id))
            cur.executemany(_INSERT_SQL, rows)
            conn.commit()
        logger.debug(
            "upserted chunks",
            extra={"count": len(rows), "tenant": tenant_id, "doc": doc_path},
        )

    def search(
        self,
        vector: List[float],
        tenant_id: str,
        top_k: int,
        doc_paths: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        vec = np.array(vector, dtype=np.float32)
        with self._conn() as (conn, cur):
            if doc_paths is not None:
                cur.execute(_SEARCH_FILTERED_SQL, (vec, tenant_id, list(doc_paths), vec, top_k))
            else:
                cur.execute(_SEARCH_SQL, (vec, tenant_id, vec, top_k))
            rows = cur.fetchall()

        results: List[SearchResult] = []
        for chunk_id, text, metadata, doc_path, tid, score in rows:
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            chunk = Chunk(id=chunk_id, text=text, metadata=metadata or {})
            results.append(
                SearchResult(
                    chunk=chunk,
                    score=float(score),
                    document_path=doc_path,
                    tenant_id=tid,
                )
            )
        return results

    def delete_document(self, doc_path: str, tenant_id: str) -> None:
        with self._conn() as (conn, cur):
            cur.execute(_DELETE_SQL, (doc_path, tenant_id))
            conn.commit()

    def save(self) -> None:
        pass  # every write is immediately durable in PostgreSQL

    def load(self) -> None:
        pass  # data already lives in PostgreSQL

    # ------------------------------------------------------------------

    @property
    def total_chunks(self) -> int:
        with self._conn() as (conn, cur):
            cur.execute(_TOTAL_SQL)
            return cur.fetchone()[0]

    def tenants(self) -> List[str]:
        with self._conn() as (conn, cur):
            cur.execute(_TENANTS_SQL)
            return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        self._pool.closeall()
