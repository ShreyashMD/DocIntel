from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class Config:
    gemini_api_key: str

    # LLM models  (use model IDs exactly as listed by client.models.list())
    generation_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"   # 3072-dim, free tier
    summarization_model: str = "gemini-2.5-flash"

    # Chunking
    chunk_size: int = 600           # target tokens per chunk
    chunk_overlap: int = 80         # overlap tokens between adjacent chunks
    min_chunk_size: int = 80        # discard chunks smaller than this

    # Retrieval
    top_k: int = 5                  # chunks to retrieve per query

    # Storage backend
    vector_store: Literal["memory", "pgvector", "qdrant"] = "memory"
    db_url: Optional[str] = None    # required for pgvector
    qdrant_url: Optional[str] = None
    persist_dir: Optional[str] = None  # where memory store saves its index

    # Rate limiting
    embed_batch_size: int = 20      # max texts per embedding API call
    max_retries: int = 5
