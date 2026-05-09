"""FastAPI server endpoint tests — no real network or LLM calls."""
from __future__ import annotations
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from docintel._config import Config
from docintel.server.app import create_app
import docintel.metrics as metrics_module


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics_module.reset()
    yield
    metrics_module.reset()


@pytest.fixture
def app(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    config = Config(
        gemini_api_key="fake",
        persist_dir=str(tmp_path / "index"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )
    return create_app(config)


@pytest.fixture
def secured_app(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    config = Config(
        gemini_api_key="fake",
        persist_dir=str(tmp_path / "index"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
        api_key="secret-key",
        allowed_ingest_dirs=[str(tmp_path)],
        rate_limit_rpm=5,
    )
    return create_app(config)


@pytest.fixture
def doc_path(tmp_path):
    p = tmp_path / "manual.txt"
    p.write_text(
        "Safety Manual\n\nSafety procedure requires lockout tagout.\n\n"
        "Pump Section\n\nThe pump pressure limit is 10 bar.",
        encoding="utf-8",
    )
    return str(p)


@pytest.mark.asyncio
async def test_health_returns_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["store_backend"] == "memory"
    assert "metrics" in body


@pytest.mark.asyncio
async def test_health_adds_correlation_id_header(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert "x-correlation-id" in resp.headers
    assert "x-process-time-ms" in resp.headers


@pytest.mark.asyncio
async def test_ingest_returns_document(app, doc_path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/ingest", json={"path": doc_path, "tenant_id": "team"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == "team"
    assert body["chunk_count"] > 0
    assert body["path"] == doc_path or body["path"].endswith("manual.txt")


@pytest.mark.asyncio
async def test_ingest_missing_file_returns_404(app, tmp_path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/ingest", json={"path": str(tmp_path / "ghost.txt")})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ingest_then_search(app, doc_path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/ingest", json={"path": doc_path, "tenant_id": "search_tenant", "summarize": False})
        resp = await client.post("/search", json={"query": "pump", "tenant_id": "search_tenant", "top_k": 1})

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["score"] > 0


@pytest.mark.asyncio
async def test_ingest_then_ask(app, doc_path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/ingest", json={"path": doc_path, "tenant_id": "ask_tenant", "summarize": False})
        resp = await client.post("/ask", json={"question": "What is the pump pressure limit?", "tenant_id": "ask_tenant"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["question"] == "What is the pump pressure limit?"
    assert body["answer"].startswith("answered:")
    assert len(body["sources"]) > 0


@pytest.mark.asyncio
async def test_ask_with_no_documents_returns_fallback(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/ask", json={"question": "Anything?", "tenant_id": "empty"})

    assert resp.status_code == 200
    assert "No relevant documents" in resp.json()["answer"]


@pytest.mark.asyncio
async def test_stats_returns_counts(app, doc_path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/ingest", json={"path": doc_path, "tenant_id": "stats_t", "summarize": False})
        resp = await client.get("/stats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_chunks"] is not None
    assert "stats_t" in body["tenants"]


@pytest.mark.asyncio
async def test_delete_document(app, doc_path):
    import urllib.parse
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ingest_resp = await client.post(
            "/ingest", json={"path": doc_path, "tenant_id": "del_t", "summarize": False}
        )
        ingested_path = ingest_resp.json()["path"]
        encoded = urllib.parse.quote(ingested_path, safe="")
        await client.delete(f"/documents/{encoded}?tenant_id=del_t")

        search_resp = await client.post(
            "/search", json={"query": "pump", "tenant_id": "del_t", "top_k": 5}
        )

    results = search_resp.json()
    assert all(r["document_path"] != ingested_path for r in results)


@pytest.mark.asyncio
async def test_request_passes_correlation_id(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Correlation-Id": "my-trace-123"})
    assert resp.headers.get("x-correlation-id") == "my-trace-123"


# ---------------------------------------------------------------------------
# Security: authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(secured_app):
    async with AsyncClient(transport=ASGITransport(app=secured_app), base_url="http://test") as client:
        resp = await client.get("/stats")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_api_key_returns_401(secured_app):
    async with AsyncClient(transport=ASGITransport(app=secured_app), base_url="http://test") as client:
        resp = await client.get("/stats", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_correct_api_key_is_accepted(secured_app):
    async with AsyncClient(transport=ASGITransport(app=secured_app), base_url="http://test") as client:
        resp = await client.get("/stats", headers={"X-API-Key": "secret-key"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_exempt_from_api_key(secured_app):
    async with AsyncClient(transport=ASGITransport(app=secured_app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Security: path traversal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_outside_allowed_dir_returns_403(secured_app, tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("data", encoding="utf-8")
    async with AsyncClient(transport=ASGITransport(app=secured_app), base_url="http://test") as client:
        resp = await client.post(
            "/ingest",
            json={"path": str(outside)},
            headers={"X-API-Key": "secret-key"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ingest_inside_allowed_dir_succeeds(secured_app, tmp_path):
    doc = tmp_path / "allowed.txt"
    doc.write_text("Pump pressure limit is 10 bar.\n\nSafety lockout required.", encoding="utf-8")
    async with AsyncClient(transport=ASGITransport(app=secured_app), base_url="http://test") as client:
        resp = await client.post(
            "/ingest",
            json={"path": str(doc), "summarize": False},
            headers={"X-API-Key": "secret-key"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Security: rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_returns_429_when_exceeded(secured_app):
    async with AsyncClient(transport=ASGITransport(app=secured_app), base_url="http://test") as client:
        responses = []
        for _ in range(7):  # rpm=5, so 6th+ request should be 429
            r = await client.get("/stats", headers={"X-API-Key": "secret-key"})
            responses.append(r.status_code)
    assert 429 in responses
    assert responses.count(200) == 5
