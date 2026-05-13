-- Migration 002: Organizations, users, invitations, document library, query history
-- Idempotent — safe to run multiple times.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Organizations ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS organizations (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name           TEXT        NOT NULL,
    slug           TEXT        NOT NULL UNIQUE,
    llm_provider   TEXT        NOT NULL DEFAULT 'gemini',
    -- companion embedding provider when llm_provider='anthropic'
    embedding_provider TEXT,
    -- API keys stored encrypted with server SECRET_KEY (Fernet)
    llm_api_key_enc       TEXT,
    embedding_api_key_enc TEXT,
    ollama_url     TEXT        NOT NULL DEFAULT 'http://localhost:11434',
    plan           TEXT        NOT NULL DEFAULT 'standard',
    active         BOOLEAN     NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Users ────────────────────────────────────────────────────────────────────
-- Roles: superadmin | org_admin | manager | user | viewer
-- superadmin rows have org_id = NULL
CREATE TABLE IF NOT EXISTS users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT        NOT NULL UNIQUE,
    password_hash TEXT        NOT NULL,
    full_name     TEXT        NOT NULL DEFAULT '',
    org_id        UUID        REFERENCES organizations(id) ON DELETE CASCADE,
    role          TEXT        NOT NULL DEFAULT 'user',
    active        BOOLEAN     NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email  ON users(email);

-- ─── Invitations ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invitations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT        NOT NULL,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role        TEXT        NOT NULL DEFAULT 'user',
    token       TEXT        NOT NULL UNIQUE,
    invited_by  UUID        REFERENCES users(id) ON DELETE SET NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_invitations_token  ON invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_org_id ON invitations(org_id);

-- ─── Document Library ─────────────────────────────────────────────────────────
-- Tracks every file ingested per org / collection.
-- collection_id maps to the Pipeline's tenant_id.
CREATE TABLE IF NOT EXISTS document_library (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    collection_id TEXT        NOT NULL DEFAULT 'default',
    uploaded_by   UUID        REFERENCES users(id) ON DELETE SET NULL,
    filename      TEXT        NOT NULL,
    file_path     TEXT        NOT NULL,
    file_size     BIGINT,
    sha256        TEXT,
    -- status: pending | ingesting | ready | failed
    status        TEXT        NOT NULL DEFAULT 'pending',
    chunk_count   INTEGER     NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doc_lib_org_id        ON document_library(org_id);
CREATE INDEX IF NOT EXISTS idx_doc_lib_collection_id ON document_library(org_id, collection_id);

-- ─── Query History ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS query_history (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        REFERENCES users(id) ON DELETE SET NULL,
    org_id        UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    collection_id TEXT        NOT NULL DEFAULT 'default',
    question      TEXT        NOT NULL,
    answer        TEXT        NOT NULL,
    sources       JSONB       NOT NULL DEFAULT '[]',
    model         TEXT,
    duration_ms   INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_qh_org_id  ON query_history(org_id);
CREATE INDEX IF NOT EXISTS idx_qh_user_id ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_qh_created ON query_history(org_id, created_at DESC);
