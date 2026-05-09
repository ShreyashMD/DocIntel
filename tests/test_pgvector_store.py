"""Integration tests for PgVectorStore — skipped unless DOCINTEL_TEST_PG_URL is set."""
from __future__ import annotations
import os
import pytest

from docintel.core.entities import Chunk
from docintel.storage.pgvector import PgVectorStore

PG_URL = os.environ.get("DOCINTEL_TEST_PG_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="DOCINTEL_TEST_PG_URL not set")


@pytest.fixture
def store():
    s = PgVectorStore(db_url=PG_URL, embedding_dim=3, pool_min=1, pool_max=2)
    # Clean slate
    with s._conn() as (conn, cur):
        cur.execute("DELETE FROM docintel_chunks WHERE tenant_id LIKE 'test_%'")
        conn.commit()
    yield s
    s.close()


def _chunk(text: str, embedding: list[float]) -> Chunk:
    c = Chunk.create(text, {"source": "test"})
    c.embedding = embedding
    return c


def test_upsert_and_search(store):
    chunks = [
        _chunk("pump pressure", [1.0, 0.0, 0.0]),
        _chunk("valve safety", [0.0, 1.0, 0.0]),
    ]
    store.upsert(chunks, tenant_id="test_tenant", doc_path="/pump.txt")

    results = store.search([1.0, 0.0, 0.0], tenant_id="test_tenant", top_k=1)
    assert len(results) == 1
    assert results[0].chunk.text == "pump pressure"
    assert results[0].score > 0.9


def test_delete_document(store):
    c = _chunk("to be deleted", [0.5, 0.5, 0.0])
    store.upsert([c], tenant_id="test_del", doc_path="/del.txt")
    store.delete_document("/del.txt", tenant_id="test_del")

    results = store.search([0.5, 0.5, 0.0], tenant_id="test_del", top_k=5)
    assert all(r.document_path != "/del.txt" for r in results)


def test_tenant_isolation(store):
    a = _chunk("tenant a doc", [1.0, 0.0, 0.0])
    b = _chunk("tenant b doc", [1.0, 0.0, 0.0])
    store.upsert([a], tenant_id="test_ta", doc_path="/a.txt")
    store.upsert([b], tenant_id="test_tb", doc_path="/b.txt")

    results_a = store.search([1.0, 0.0, 0.0], tenant_id="test_ta", top_k=10)
    results_b = store.search([1.0, 0.0, 0.0], tenant_id="test_tb", top_k=10)

    assert all(r.tenant_id == "test_ta" for r in results_a)
    assert all(r.tenant_id == "test_tb" for r in results_b)


def test_upsert_replaces_existing_doc_chunks(store):
    c1 = _chunk("original version", [1.0, 0.0, 0.0])
    store.upsert([c1], tenant_id="test_repl", doc_path="/replace.txt")

    c2 = _chunk("updated version", [0.0, 1.0, 0.0])
    store.upsert([c2], tenant_id="test_repl", doc_path="/replace.txt")

    results = store.search([1.0, 0.0, 0.0], tenant_id="test_repl", top_k=10)
    texts = [r.chunk.text for r in results]
    assert "original version" not in texts


def test_save_and_load_are_noops(store):
    store.save()  # should not raise
    store.load()  # should not raise


def test_total_chunks_and_tenants(store):
    c = _chunk("stats test", [0.1, 0.2, 0.3])
    store.upsert([c], tenant_id="test_stats", doc_path="/stats.txt")

    total = store.total_chunks
    tenants = store.tenants()
    assert total >= 1
    assert "test_stats" in tenants
