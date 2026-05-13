from __future__ import annotations
import threading

from docintel._config import Config
from docintel._pipeline import Pipeline


class PipelineRegistry:
    """Maintains one Pipeline instance per organisation, created on first access."""

    def __init__(self, base_config: Config) -> None:
        self._base   = base_config
        self._cache: dict[str, Pipeline] = {}
        self._lock   = threading.Lock()

    def get_or_create(self, org_id: str, org_settings: dict,
                      secret_key: str) -> Pipeline:
        with self._lock:
            if org_id not in self._cache:
                self._cache[org_id] = self._build(org_settings, secret_key)
            return self._cache[org_id]

    def invalidate(self, org_id: str) -> None:
        with self._lock:
            pipeline = self._cache.pop(org_id, None)
        if pipeline is not None:
            store = getattr(pipeline, "_store", None)
            if store and hasattr(store, "close"):
                store.close()

    def shutdown(self) -> None:
        with self._lock:
            orgs = list(self._cache.keys())
        for org_id in orgs:
            self.invalidate(org_id)

    def _build(self, org: dict, secret_key: str) -> Pipeline:
        from docintel.server import auth as _auth

        provider       = org.get("llm_provider") or self._base.provider
        embed_provider = org.get("embedding_provider") or self._base.embedding_provider

        def _decrypt(enc: str | None) -> str | None:
            if enc and secret_key:
                return _auth.decrypt_api_key(enc, secret_key)
            return None

        # Start from server-level base keys
        gemini_key    = self._base.gemini_api_key
        openai_key    = self._base.openai_api_key
        anthropic_key = self._base.anthropic_api_key
        nvidia_key    = self._base.nvidia_api_key

        # Override with org-specific per-provider keys (provider-specific column
        # takes precedence; fall back to legacy generic llm_api_key_enc when
        # the provider matches).
        legacy_enc = org.get("llm_api_key_enc")

        if org.get("openai_api_key_enc"):
            openai_key = _decrypt(org["openai_api_key_enc"])
        elif provider == "openai" and legacy_enc:
            openai_key = _decrypt(legacy_enc)

        if org.get("gemini_api_key_enc"):
            gemini_key = _decrypt(org["gemini_api_key_enc"])
        elif provider == "gemini" and legacy_enc:
            gemini_key = _decrypt(legacy_enc)

        if org.get("anthropic_api_key_enc"):
            anthropic_key = _decrypt(org["anthropic_api_key_enc"])
        elif provider == "anthropic" and legacy_enc:
            anthropic_key = _decrypt(legacy_enc)

        if org.get("nvidia_api_key_enc"):
            nvidia_key = _decrypt(org["nvidia_api_key_enc"])
        elif provider == "nvidia" and legacy_enc:
            nvidia_key = _decrypt(legacy_enc)

        # Embedding companion for Anthropic: prefer stored openai key, fall back
        # to legacy embedding_api_key_enc.
        if embed_provider == "openai" and not openai_key:
            enc_emb = org.get("embedding_api_key_enc")
            if enc_emb:
                openai_key = _decrypt(enc_emb)

        persist_dir = f"{self._base.persist_dir or '.docintel'}/{org['slug']}"

        config = Config(
            provider=provider,
            embedding_provider=embed_provider,
            gemini_api_key=gemini_key,
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            nvidia_api_key=nvidia_key,
            ollama_base_url=org.get("ollama_url") or self._base.ollama_base_url,
            vector_store=self._base.vector_store,
            db_url=self._base.db_url,
            persist_dir=persist_dir,
            chunk_size=self._base.chunk_size,
            chunk_overlap=self._base.chunk_overlap,
            min_chunk_size=self._base.min_chunk_size,
            top_k=self._base.top_k,
            embed_batch_size=self._base.embed_batch_size,
            max_retries=self._base.max_retries,
            rag_mode=self._base.rag_mode,
            lightrag_dir=f"{self._base.lightrag_dir}/{org['slug']}",
            pipeline_mode=org.get("pipeline_mode") or "single",
        )
        return Pipeline(config)
