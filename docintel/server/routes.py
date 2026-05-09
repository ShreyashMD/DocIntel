from __future__ import annotations
import os
from typing import List

from fastapi import APIRouter, HTTPException, Request

from docintel._pipeline import Pipeline
from docintel.metrics import get_metrics
from docintel.server.schemas import (
    AskRequest,
    ChunkSchema,
    DocumentSchema,
    HealthSchema,
    IngestRequest,
    QueryResultSchema,
    SearchRequest,
    SearchResultSchema,
    StatsSchema,
)

router = APIRouter()


def _pipeline(request: Request) -> Pipeline:
    return request.app.state.pipeline


def _validate_ingest_path(path: str, allowed_dirs: list[str]) -> None:
    """Raise 403 if path escapes the configured allowed directories."""
    if not allowed_dirs:
        return
    try:
        resolved = os.path.realpath(path)
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid path.")
    for allowed in allowed_dirs:
        base = os.path.realpath(allowed)
        if resolved == base or resolved.startswith(base + os.sep):
            return
    raise HTTPException(status_code=403, detail="Path is outside the allowed ingest directories.")


@router.get("/health", response_model=HealthSchema)
def health(request: Request):
    pipeline = _pipeline(request)
    backend = pipeline._config.vector_store
    return HealthSchema(
        status="ok",
        store_backend=backend,
        metrics=get_metrics(),
    )


@router.post("/ingest", response_model=DocumentSchema)
def ingest(request: Request, body: IngestRequest):
    pipeline = _pipeline(request)
    _validate_ingest_path(body.path, pipeline._config.allowed_ingest_dirs)
    try:
        doc = pipeline.ingest(body.path, tenant_id=body.tenant_id, summarize=body.summarize, verbose=False)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DocumentSchema(
        id=doc.id,
        path=doc.path,
        tenant_id=doc.tenant_id,
        summary=doc.summary,
        metadata=doc.metadata,
        chunk_count=len(doc.chunks),
    )


@router.post("/search", response_model=List[SearchResultSchema])
def search(request: Request, body: SearchRequest):
    pipeline = _pipeline(request)
    results = pipeline.search(body.query, tenant_id=body.tenant_id, top_k=body.top_k)
    return [
        SearchResultSchema(
            chunk=ChunkSchema(id=r.chunk.id, text=r.chunk.text, metadata=r.chunk.metadata),
            score=r.score,
            document_path=r.document_path,
            tenant_id=r.tenant_id,
        )
        for r in results
    ]


@router.post("/ask", response_model=QueryResultSchema)
def ask(request: Request, body: AskRequest):
    pipeline = _pipeline(request)
    result = pipeline.ask(body.question, tenant_id=body.tenant_id, top_k=body.top_k)
    return QueryResultSchema(
        question=result.question,
        answer=result.answer,
        sources=[
            SearchResultSchema(
                chunk=ChunkSchema(id=r.chunk.id, text=r.chunk.text, metadata=r.chunk.metadata),
                score=r.score,
                document_path=r.document_path,
                tenant_id=r.tenant_id,
            )
            for r in result.sources
        ],
        model=result.model,
    )


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(request: Request, doc_id: str, tenant_id: str = "default"):
    pipeline = _pipeline(request)
    pipeline.delete(doc_id, tenant_id=tenant_id)


@router.get("/stats", response_model=StatsSchema)
def stats(request: Request):
    pipeline = _pipeline(request)
    data = pipeline.stats()
    return StatsSchema(
        total_chunks=data.get("total_chunks"),
        tenants=data.get("tenants"),
        store=data.get("store"),
    )
