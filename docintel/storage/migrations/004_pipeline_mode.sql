-- Pipeline mode: controls how LLM calls are orchestrated when answering questions.
-- 'single'          — one LLM generates the answer directly (default, current behavior)
-- 'writer_reviewer' — writer drafts, reviewer fact-checks and improves

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS pipeline_mode TEXT NOT NULL DEFAULT 'single';
