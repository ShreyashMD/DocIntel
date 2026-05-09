from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class IngestRequest(BaseModel):
    path: str
    tenant_id: str = "default"
    summarize: bool = True


class AskRequest(BaseModel):
    question: str
    tenant_id: str = "default"
    top_k: Optional[int] = None


class SearchRequest(BaseModel):
    query: str
    tenant_id: str = "default"
    top_k: Optional[int] = None


class ChunkSchema(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]


class SearchResultSchema(BaseModel):
    chunk: ChunkSchema
    score: float
    document_path: str
    tenant_id: str


class QueryResultSchema(BaseModel):
    question: str
    answer: str
    sources: List[SearchResultSchema]
    model: str


class DocumentSchema(BaseModel):
    id: str
    path: str
    tenant_id: str
    summary: str
    metadata: Dict[str, Any]
    chunk_count: int


class StatsSchema(BaseModel):
    total_chunks: Optional[int] = None
    tenants: Optional[List[str]] = None
    store: Optional[str] = None


class HealthSchema(BaseModel):
    status: str
    store_backend: str
    metrics: Dict[str, Any]
