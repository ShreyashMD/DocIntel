-- DocIntel pgvector schema — idempotent, safe to re-run.
-- Requires: PostgreSQL with the pgvector extension available.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS docintel_chunks (
    id          TEXT         PRIMARY KEY,
    tenant_id   TEXT         NOT NULL,
    doc_path    TEXT         NOT NULL,
    text        TEXT         NOT NULL,
    metadata    JSONB        NOT NULL DEFAULT '{}',
    embedding   vector(3072) NOT NULL,          -- default: gemini-embedding-001 output dim
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS docintel_chunks_tenant_idx
    ON docintel_chunks (tenant_id);

-- HNSW index for approximate nearest-neighbour cosine search.
-- Works on empty tables; no training data required.
-- Tune m / ef_construction for your recall / build-time trade-off.
CREATE INDEX IF NOT EXISTS docintel_chunks_embedding_idx
    ON docintel_chunks USING hnsw (embedding vector_cosine_ops);
