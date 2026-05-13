from __future__ import annotations
import mimetypes
import os
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
import threading
import logging

# Per-org rebuild lock: prevents concurrent graph rebuilds from wiping each other's work.
_rebuild_locks: dict[str, threading.Lock] = {}
_rebuild_locks_mutex = threading.Lock()


def _get_rebuild_lock(org_id: str) -> threading.Lock:
    with _rebuild_locks_mutex:
        if org_id not in _rebuild_locks:
            _rebuild_locks[org_id] = threading.Lock()
        return _rebuild_locks[org_id]

from pydantic import BaseModel

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from docintel._pipeline import Pipeline
from docintel.metrics import get_metrics
from docintel.server import db as _db

logger = logging.getLogger(__name__)
from docintel.server.deps import CurrentUser, get_current_user, get_current_user_or_token_param, require_manager
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

router = APIRouter(tags=["documents"])


# ─── Pipeline resolution ───────────────────────────────────────────────────────

def _get_pipeline(request: Request, user: CurrentUser) -> Pipeline:
    if not user.org_id:
        raise HTTPException(403, "Superadmin accounts cannot use the document pipeline. Create or join an organisation first.")
    registry = request.app.state.pipeline_registry
    secret   = request.app.state.secret_key
    with _db.get_conn() as conn:
        org = _db.get_org(conn, user.org_id)
    if not org or not org["active"]:
        raise HTTPException(403, "Organisation not found or suspended.")
    return registry.get_or_create(user.org_id, org, secret)


def _validate_ingest_path(path: str, allowed_dirs: list[str]) -> None:
    if not allowed_dirs:
        return
    try:
        resolved = os.path.realpath(path)
    except (OSError, ValueError):
        raise HTTPException(400, "Invalid path.")
    for allowed in allowed_dirs:
        base = os.path.realpath(allowed)
        if resolved == base or resolved.startswith(base + os.sep):
            return
    raise HTTPException(403, "Path is outside the allowed ingest directories.")


# ─── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthSchema)
def health(request: Request):
    backend = request.app.state.config.vector_store
    return HealthSchema(status="ok", store_backend=backend, metrics=get_metrics())


# ─── Documents ─────────────────────────────────────────────────────────────────

@router.get("/documents")
def list_documents(
    request: Request,
    collection_id: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
):
    with _db.get_conn() as conn:
        docs = _db.list_docs_by_org(conn, current.org_id, collection_id)
    return [_doc_to_dict(d) for d in docs]


@router.post("/ingest", response_model=DocumentSchema)
def ingest(request: Request, body: IngestRequest,
           current: CurrentUser = Depends(require_manager)):
    config = request.app.state.config
    _validate_ingest_path(body.path, config.allowed_ingest_dirs)

    pipeline = _get_pipeline(request, current)
    tenant   = f"{current.org_id}:{body.tenant_id}"

    # Record in document library
    path = os.path.realpath(body.path)
    filename = os.path.basename(path)
    file_size = os.path.getsize(path) if os.path.exists(path) else 0

    with _db.get_conn() as conn:
        doc_record = _db.upsert_doc_record(
            conn,
            org_id=current.org_id,
            collection_id=body.tenant_id,
            uploaded_by=current.user_id,
            filename=filename,
            file_path=path,
            file_size=file_size,
            sha256="",
            status="ingesting",
        )

    try:
        doc = pipeline.ingest(body.path, tenant_id=tenant,
                              summarize=body.summarize, index_graph=False, verbose=False)
        with _db.get_conn() as conn:
            _db.update_doc_status(conn, str(doc_record["id"]),
                                  "ready", len(doc.chunks))
    except (FileNotFoundError, ValueError) as exc:
        with _db.get_conn() as conn:
            _db.update_doc_status(conn, str(doc_record["id"]),
                                  "failed", error_message=str(exc))
        status_code = 404 if isinstance(exc, FileNotFoundError) else 400
        raise HTTPException(status_code, str(exc))

    return DocumentSchema(
        id=doc.id,
        path=doc.path,
        tenant_id=body.tenant_id,
        summary=doc.summary,
        metadata=doc.metadata,
        chunk_count=len(doc.chunks),
    )


@router.post("/upload")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection_id: str = Form("default"),
    summarize: bool = Form(False),
    current: CurrentUser = Depends(require_manager),
):
    """Save uploaded file to disk, record it, then ingest in a background thread."""
    config  = request.app.state.config
    tenant  = f"{current.org_id}:{collection_id}"

    persist_dir = config.persist_dir or ".docintel"
    upload_dir  = os.path.join(persist_dir, "uploads", current.org_id)
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = os.path.basename(file.filename or "upload")
    tmp_path  = os.path.join(upload_dir, safe_name)
    try:
        with open(tmp_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
    finally:
        await file.close()

    file_size = os.path.getsize(tmp_path)

    with _db.get_conn() as conn:
        doc_record = _db.upsert_doc_record(
            conn,
            org_id=current.org_id,
            collection_id=collection_id,
            uploaded_by=current.user_id,
            filename=safe_name,
            file_path=tmp_path,
            file_size=file_size,
            sha256="",
            status="ingesting",
        )

    pipeline = _get_pipeline(request, current)
    doc_id   = str(doc_record["id"])

    def _ingest():
        try:
            doc = pipeline.ingest(tmp_path, tenant_id=tenant,
                                  summarize=summarize, index_graph=False, verbose=False)
            with _db.get_conn() as conn:
                _db.update_doc_status(conn, doc_id, "ready", len(doc.chunks))
        except Exception as exc:
            logger.error("background ingest failed", exc_info=True)
            with _db.get_conn() as conn:
                _db.update_doc_status(conn, doc_id, "failed",
                                      error_message=str(exc)[:500])

    background_tasks.add_task(_ingest)
    return _doc_to_dict(doc_record)


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(
    doc_id: str,
    request: Request,
    collection_id: str = Query("default"),
    current: CurrentUser = Depends(require_manager),
):
    with _db.get_conn() as conn:
        record = _db.get_doc_by_id(conn, doc_id, current.org_id)
    if not record:
        raise HTTPException(404, "Document not found.")

    pipeline = _get_pipeline(request, current)
    tenant   = f"{current.org_id}:{collection_id}"

    # Remove from vector store
    try:
        pipeline.delete(record["file_path"], tenant_id=tenant)
    except Exception:
        pass

    # Remove the file from disk
    try:
        if os.path.exists(record["file_path"]):
            os.remove(record["file_path"])
    except OSError:
        pass

    # Clear the LightRAG graph for this org so stale entities are removed.
    # The user can rebuild the graph from remaining documents via POST /graph/rebuild.
    if pipeline._lightrag is not None:
        try:
            pipeline._lightrag.clear()
            # Invalidate cached pipeline so LightRAG reinitialises cleanly
            request.app.state.pipeline_registry.invalidate(current.org_id)
        except Exception:
            logger.warning("Failed to clear LightRAG graph after document delete", exc_info=True)

    with _db.get_conn() as conn:
        _db.delete_doc_record(conn, doc_id, current.org_id)


@router.get("/documents/{doc_id}/file")
def serve_document_file(
    doc_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user_or_token_param),
):
    """Stream the raw file so the browser can display it (PDFs open inline with #page=N)."""
    with _db.get_conn() as conn:
        record = _db.get_doc_by_id(conn, doc_id, current.org_id)
    if not record:
        raise HTTPException(404, "Document not found.")
    file_path = record["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found on disk.")
    media_type, _ = mimetypes.guess_type(file_path)
    media_type = media_type or "application/octet-stream"
    filename = record["filename"]
    # PDFs use inline disposition so the browser renders them; others force download
    disposition = "inline" if media_type == "application/pdf" else f'attachment; filename="{filename}"'
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )


# ─── Search ────────────────────────────────────────────────────────────────────

@router.post("/search", response_model=List[SearchResultSchema])
def search(request: Request, body: SearchRequest,
           current: CurrentUser = Depends(get_current_user)):
    pipeline  = _get_pipeline(request, current)
    tenant    = f"{current.org_id}:{body.tenant_id}"
    doc_paths = None
    if body.doc_ids:
        with _db.get_conn() as conn:
            doc_paths = _resolve_doc_paths(conn, body.doc_ids, current.org_id)
    results = pipeline.search(body.query, tenant_id=tenant, top_k=body.top_k,
                               doc_paths=doc_paths)
    unique_paths = list({r.document_path for r in results})
    doc_id_map: dict[str, str] = {}
    if unique_paths:
        with _db.get_conn() as conn:
            doc_id_map = _resolve_doc_ids_by_path(conn, unique_paths, current.org_id)
    return [_search_result_to_schema(r, doc_id_map.get(r.document_path)) for r in results]


# ─── Ask ───────────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=QueryResultSchema)
def ask(request: Request, body: AskRequest,
        current: CurrentUser = Depends(get_current_user)):
    pipeline  = _get_pipeline(request, current)
    tenant    = f"{current.org_id}:{body.tenant_id}"
    doc_paths = None
    if body.doc_ids:
        with _db.get_conn() as conn:
            doc_paths = _resolve_doc_paths(conn, body.doc_ids, current.org_id)
    t0     = time.perf_counter()
    result = pipeline.ask(body.question, tenant_id=tenant, top_k=body.top_k,
                          doc_paths=doc_paths)
    ms       = int((time.perf_counter() - t0) * 1000)

    # Batch-resolve file_path → doc_id for source citations
    unique_paths = list({r.document_path for r in result.sources})
    doc_id_map: dict[str, str] = {}
    if unique_paths:
        with _db.get_conn() as conn:
            doc_id_map = _resolve_doc_ids_by_path(conn, unique_paths, current.org_id)

    # Persist to query history
    sources_payload = [
        {"document_path": r.document_path, "score": r.score,
         "page": r.chunk.metadata.get("page")}
        for r in result.sources
    ]
    with _db.get_conn() as conn:
        _db.save_query(
            conn,
            user_id=current.user_id,
            org_id=current.org_id,
            collection_id=body.tenant_id,
            question=body.question,
            answer=result.answer,
            sources=sources_payload,
            model=result.model or "",
            duration_ms=ms,
        )

    return QueryResultSchema(
        question=result.question,
        answer=result.answer,
        sources=[_search_result_to_schema(r, doc_id_map.get(r.document_path)) for r in result.sources],
        model=result.model,
    )


# ─── Knowledge Graph ───────────────────────────────────────────────────────────

class _RebuildRequest(BaseModel):
    doc_ids: Optional[List[str]] = None


@router.post("/graph/rebuild")
def rebuild_graph(
    request: Request,
    background_tasks: BackgroundTasks,
    body: _RebuildRequest = None,
    current: CurrentUser = Depends(require_manager),
):
    """
    Clear the org's LightRAG graph and re-index documents.
    Pass doc_ids to rebuild with a specific subset; omit to rebuild with all ready docs.
    """
    pipeline = _get_pipeline(request, current)
    if pipeline._lightrag is None:
        raise HTTPException(400, "Graph mode is not enabled on this server.")

    doc_ids = body.doc_ids if body else None
    with _db.get_conn() as conn:
        if doc_ids:
            all_docs = [_db.get_doc_by_id(conn, did, current.org_id) for did in doc_ids]
            docs = [d for d in all_docs if d and d["status"] == "ready"]
        else:
            docs = [d for d in _db.list_docs_by_org(conn, current.org_id)
                    if d["status"] == "ready"]

    lock = _get_rebuild_lock(current.org_id)

    def _rebuild():
        if not lock.acquire(blocking=False):
            logger.warning("Graph rebuild skipped — another rebuild is already running for org %s", current.org_id)
            return
        try:
            pipeline._lightrag.clear()

            # Extract all documents in parallel (IO + CPU-bound text extraction)
            def _extract_text(doc):
                pages = pipeline._extract(doc["file_path"])
                return "\n\n".join(t for _, t in pages[:80])

            texts: list[str] = []
            max_workers = min(4, max(1, len(docs)))
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_to_doc = {pool.submit(_extract_text, doc): doc for doc in docs}
                for fut in as_completed(future_to_doc):
                    doc = future_to_doc[fut]
                    try:
                        texts.append(fut.result())
                        logger.info("graph_extracted", extra={"file": doc["filename"]})
                    except Exception:
                        logger.warning("extract failed for %s", doc["filename"], exc_info=True)

            # Single insert call with all texts — LightRAG's async workers
            # parallelize entity/relation extraction across chunks internally
            if texts:
                pipeline._lightrag.insert(texts)
                logger.info("graph_rebuild_done", extra={"org": current.org_id, "docs": len(texts)})
        except Exception:
            logger.error("Graph rebuild failed", exc_info=True)
        finally:
            lock.release()

    background_tasks.add_task(_rebuild)
    return {"message": f"Graph rebuild started with {len(docs)} document(s)."}


@router.get("/graph/rebuild/status")
def rebuild_status(request: Request, current: CurrentUser = Depends(get_current_user)):
    lock = _get_rebuild_lock(current.org_id)
    running = not lock.acquire(blocking=False)
    if not running:
        lock.release()
    return {"running": running}


@router.get("/graph")
def get_graph(request: Request, current: CurrentUser = Depends(get_current_user)):
    """Return LightRAG knowledge graph nodes and edges from the GraphML file."""
    import xml.etree.ElementTree as ET

    config = request.app.state.config

    if config.rag_mode == "vector":
        return {"enabled": False, "rag_mode": "vector", "nodes": [], "edges": []}

    with _db.get_conn() as conn:
        org = _db.get_org(conn, current.org_id)
    if not org:
        raise HTTPException(403, "Organisation not found.")

    graphml_path = os.path.join(
        config.lightrag_dir, org["slug"], "graph_chunk_entity_relation.graphml"
    )

    if not os.path.exists(graphml_path):
        return {
            "enabled": True, "rag_mode": config.rag_mode,
            "nodes": [], "edges": [],
            "message": "No graph built yet — upload documents first.",
        }

    try:
        tree = ET.parse(graphml_path)
        root = tree.getroot()

        # Derive namespace from root tag to handle xmlns variations (e.g.
        # LightRAG writes "http://graphml.graphdrawing.org/xmlns" not "…/graphml")
        root_tag = root.tag
        if root_tag.startswith("{"):
            ns_uri = root_tag[1:root_tag.index("}")]
        else:
            ns_uri = "http://graphml.graphdrawing.org/xmlns"
        ns = {"g": ns_uri}

        key_defs: dict[str, str] = {}
        for key_el in root.findall("g:key", ns):
            key_defs[key_el.get("id", "")] = key_el.get("attr.name", key_el.get("id", ""))

        nodes: list[dict] = []
        edges: list[dict] = []

        for graph_el in root.findall("g:graph", ns):
            for node_el in graph_el.findall("g:node", ns):
                node_id = node_el.get("id", "")
                attrs: dict[str, str] = {}
                for data in node_el.findall("g:data", ns):
                    name = key_defs.get(data.get("key", ""), data.get("key", ""))
                    attrs[name] = data.text or ""
                nodes.append({
                    "id":          node_id,
                    "label":       node_id,
                    "type":        attrs.get("entity_type", "unknown").lower(),
                    "description": attrs.get("description", ""),
                })

            for edge_el in graph_el.findall("g:edge", ns):
                attrs = {}
                for data in edge_el.findall("g:data", ns):
                    name = key_defs.get(data.get("key", ""), data.get("key", ""))
                    attrs[name] = data.text or ""
                try:
                    weight = float(attrs.get("weight", "1"))
                except (TypeError, ValueError):
                    weight = 1.0
                edges.append({
                    "source":      edge_el.get("source", ""),
                    "target":      edge_el.get("target", ""),
                    "label":       attrs.get("keywords", ""),
                    "description": attrs.get("description", ""),
                    "weight":      weight,
                })

        return {
            "enabled":  True,
            "rag_mode": config.rag_mode,
            "nodes":    nodes,
            "edges":    edges,
        }

    except Exception as exc:
        logger.warning("Failed to parse graph", exc_info=True)
        return {
            "enabled": True, "rag_mode": config.rag_mode,
            "nodes": [], "edges": [], "error": str(exc),
        }


# ─── History ───────────────────────────────────────────────────────────────────

@router.get("/history")
def query_history(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    current: CurrentUser = Depends(get_current_user),
):
    with _db.get_conn() as conn:
        rows = _db.list_query_history(conn, current.org_id,
                                      user_id=current.user_id, limit=limit)
    return [_history_row(r) for r in rows]


# ─── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsSchema)
def stats(request: Request,
          current: CurrentUser = Depends(get_current_user)):
    pipeline = _get_pipeline(request, current)
    data     = pipeline.stats()
    return StatsSchema(
        total_chunks=data.get("total_chunks"),
        tenants=data.get("tenants"),
        store=data.get("store"),
    )


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_doc_paths(conn, doc_ids: List[str], org_id: str) -> List[str]:
    """Return file_paths for the given doc UUIDs, scoped to the org."""
    if not doc_ids:
        return []
    import psycopg2.extras
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(doc_ids))
    cur.execute(
        f"SELECT file_path FROM document_library WHERE id IN ({placeholders}) AND org_id = %s",
        [*doc_ids, org_id],
    )
    return [row[0] for row in cur.fetchall()]


def _resolve_doc_ids_by_path(conn, file_paths: list[str], org_id: str) -> dict[str, str]:
    """Return a file_path → doc_id mapping for the given paths, scoped to the org."""
    if not file_paths:
        return {}
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(file_paths))
    cur.execute(
        f"SELECT id, file_path FROM document_library WHERE file_path IN ({placeholders}) AND org_id = %s",
        [*file_paths, org_id],
    )
    return {row[1]: str(row[0]) for row in cur.fetchall()}


def _search_result_to_schema(r, doc_id: Optional[str] = None) -> SearchResultSchema:
    return SearchResultSchema(
        chunk=ChunkSchema(id=r.chunk.id, text=r.chunk.text, metadata=r.chunk.metadata),
        score=r.score,
        document_path=r.document_path,
        tenant_id=r.tenant_id,
        doc_id=doc_id,
    )


def _doc_to_dict(d: dict) -> dict:
    return {
        "id":            str(d["id"]),
        "filename":      d["filename"],
        "file_path":     d["file_path"],
        "collection_id": d["collection_id"],
        "status":        d["status"],
        "chunk_count":   d["chunk_count"],
        "file_size":     d.get("file_size"),
        "created_at":    str(d.get("created_at", "")),
    }


def _history_row(r: dict) -> dict:
    return {
        "id":            str(r["id"]),
        "question":      r["question"],
        "answer":        r["answer"],
        "sources":       r.get("sources", []),
        "model":         r.get("model"),
        "duration_ms":   r.get("duration_ms"),
        "collection_id": r.get("collection_id"),
        "created_at":    str(r.get("created_at", "")),
    }
