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

-- Note: pgvector indexes (HNSW/IVFFlat) support max 2000 dimensions.
-- Default embeddings are 3072-dim (gemini-embedding-001 / text-embedding-3-large).
-- Sequential cosine scans are used instead — fine for <100k chunks.
-- To use an index, switch to a 768-dim model (text-embedding-004 / text-embedding-3-small)
-- and add: CREATE INDEX ... USING hnsw (embedding vector_cosine_ops);
