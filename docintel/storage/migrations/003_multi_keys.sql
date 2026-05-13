-- Per-provider API key columns so organisations can store keys for multiple
-- providers simultaneously and switch between them without re-entering keys.

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS openai_api_key_enc    TEXT,
  ADD COLUMN IF NOT EXISTS gemini_api_key_enc    TEXT,
  ADD COLUMN IF NOT EXISTS anthropic_api_key_enc TEXT,
  ADD COLUMN IF NOT EXISTS nvidia_api_key_enc    TEXT;

-- Migrate any existing generic llm_api_key_enc into the provider-specific column.
UPDATE organizations
  SET openai_api_key_enc = llm_api_key_enc
  WHERE llm_provider = 'openai'
    AND llm_api_key_enc IS NOT NULL
    AND openai_api_key_enc IS NULL;

UPDATE organizations
  SET gemini_api_key_enc = llm_api_key_enc
  WHERE llm_provider = 'gemini'
    AND llm_api_key_enc IS NOT NULL
    AND gemini_api_key_enc IS NULL;

UPDATE organizations
  SET anthropic_api_key_enc = llm_api_key_enc
  WHERE llm_provider = 'anthropic'
    AND llm_api_key_enc IS NOT NULL
    AND anthropic_api_key_enc IS NULL;

UPDATE organizations
  SET nvidia_api_key_enc = llm_api_key_enc
  WHERE llm_provider = 'nvidia'
    AND llm_api_key_enc IS NOT NULL
    AND nvidia_api_key_enc IS NULL;
