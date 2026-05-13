from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional


# Sensible per-provider defaults resolved in __post_init__
_PROVIDER_DEFAULTS: dict[str, dict] = {
    "gemini": {
        "generation_model": "gemini-2.5-flash",
        "embedding_model": "gemini-embedding-001",
        "embedding_dim": 3072,
    },
    "openai": {
        "generation_model": "gpt-4o",
        "embedding_model": "text-embedding-3-large",
        "embedding_dim": 3072,
    },
    "anthropic": {
        "generation_model": "claude-opus-4-7",
        "embedding_model": None,   # no native embeddings — set by embedding_provider
        "embedding_dim": None,
    },
    "ollama": {
        "generation_model": "llama3.2",
        "embedding_model": "nomic-embed-text",
        "embedding_dim": 768,
    },
    "nvidia": {
        "generation_model": "meta/llama-3.1-70b-instruct",
        "embedding_model":  "nvidia/nv-embedqa-e5-v5",
        "embedding_dim":    1024,
    },
}

_EMBED_PROVIDER_DEFAULTS: dict[str, dict] = {
    "gemini": {"embedding_model": "gemini-embedding-001", "embedding_dim": 3072},
    "openai": {"embedding_model": "text-embedding-3-large", "embedding_dim": 3072},
    "ollama": {"embedding_model": "nomic-embed-text", "embedding_dim": 768},
    "nvidia": {"embedding_model": "nvidia/nv-embedqa-e5-v5", "embedding_dim": 1024},
}


@dataclass
class Config:
    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------
    provider: Literal["gemini", "openai", "anthropic", "ollama", "nvidia"] = "gemini"

    # When provider="anthropic" (no native embeddings), set this to "openai" or "ollama"
    embedding_provider: Optional[str] = None

    # ------------------------------------------------------------------
    # API keys / connection (all optional — required based on provider)
    # ------------------------------------------------------------------
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    # ------------------------------------------------------------------
    # LLM models (None = resolved automatically from provider defaults)
    # ------------------------------------------------------------------
    generation_model: Optional[str] = None
    embedding_model: Optional[str] = None
    summarization_model: Optional[str] = None   # falls back to generation_model if None

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------
    chunk_size: int = 600
    chunk_overlap: int = 80
    min_chunk_size: int = 80

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    top_k: int = 5

    # ------------------------------------------------------------------
    # Storage backend
    # ------------------------------------------------------------------
    vector_store: Literal["memory", "pgvector", "qdrant"] = "memory"
    db_url: Optional[str] = None
    qdrant_url: Optional[str] = None
    persist_dir: Optional[str] = None

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    embedding_dim: Optional[int] = None   # resolved from provider if None

    # ------------------------------------------------------------------
    # PostgreSQL connection pool
    # ------------------------------------------------------------------
    pg_pool_min: int = 2
    pg_pool_max: int = 10

    # ------------------------------------------------------------------
    # HTTP server security
    # ------------------------------------------------------------------
    api_key: Optional[str] = None
    allowed_ingest_dirs: list[str] = field(default_factory=list)
    rate_limit_rpm: int = 0

    # ------------------------------------------------------------------
    # LightRAG graph retrieval (rag_mode != "vector" requires lightrag-hku)
    # ------------------------------------------------------------------
    rag_mode: Literal["vector", "graph", "hybrid"] = "vector"
    lightrag_dir: str = ".docintel_graph"

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------
    # When True, PDF pages with sparse text are automatically re-processed
    # via Tesseract OCR (requires pytesseract + pdf2image + tesseract binary).
    # Image uploads (PNG/JPG/etc.) always use OCR regardless of this flag.
    ocr_enabled: bool = True
    # Pages shorter than this many characters are treated as scanned/image.
    ocr_min_chars_per_page: int = 50

    # ------------------------------------------------------------------
    # Pipeline / answer workflow
    # ------------------------------------------------------------------
    # "single"          — one LLM generates the answer directly (default)
    # "writer_reviewer" — writer drafts, reviewer fact-checks & improves
    pipeline_mode: Literal["single", "writer_reviewer"] = "single"

    # ------------------------------------------------------------------
    # API rate limiting / retry
    # ------------------------------------------------------------------
    embed_batch_size: int = 20
    max_retries: int = 5

    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        # 1. Resolve model defaults from provider
        pd = _PROVIDER_DEFAULTS[self.provider]
        if not self.generation_model:
            self.generation_model = pd["generation_model"]
        if not self.summarization_model:
            self.summarization_model = self.generation_model

        # Embedding model/dim may come from a companion embedding_provider (e.g. Anthropic)
        ep = self.embedding_provider or self.provider
        epd = _EMBED_PROVIDER_DEFAULTS.get(ep, pd)
        if not self.embedding_model:
            self.embedding_model = epd.get("embedding_model")
        if not self.embedding_dim:
            self.embedding_dim = epd.get("embedding_dim")

        # 2. Validate API keys for chosen provider
        if self.provider == "gemini" and not self.gemini_api_key:
            raise ValueError("gemini_api_key is required when provider='gemini'.")
        if self.provider == "openai" and not self.openai_api_key:
            raise ValueError("openai_api_key is required when provider='openai'.")
        if self.provider == "nvidia" and not self.nvidia_api_key:
            raise ValueError("nvidia_api_key is required when provider='nvidia'.")
        if self.provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("anthropic_api_key is required when provider='anthropic'.")
            if not self.embedding_provider:
                raise ValueError(
                    "embedding_provider is required when provider='anthropic' "
                    "(Anthropic provides no embeddings). "
                    "Set embedding_provider='openai' and openai_api_key=... or embedding_provider='ollama'."
                )
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("openai_api_key is required when embedding_provider='openai'.")

        # 3. Validate chunking / retrieval numerics
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0.")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be 0 or greater.")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")
        if self.min_chunk_size < 0:
            raise ValueError("min_chunk_size must be 0 or greater.")
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than 0.")
        if self.embed_batch_size <= 0:
            raise ValueError("embed_batch_size must be greater than 0.")
        if self.max_retries <= 0:
            raise ValueError("max_retries must be greater than 0.")
        if self.rate_limit_rpm < 0:
            raise ValueError("rate_limit_rpm must be 0 or greater.")

        # 4. Validate storage
        if self.vector_store == "pgvector" and not self.db_url:
            raise ValueError("db_url is required when vector_store='pgvector'.")
        if self.vector_store == "qdrant" and not self.qdrant_url:
            raise ValueError("qdrant_url is required when vector_store='qdrant'.")
