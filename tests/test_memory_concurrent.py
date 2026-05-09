"""Thread-safety tests for MemoryVectorStore."""
from __future__ import annotations
import threading

import pytest

from docintel.core.entities import Chunk
from docintel.storage.memory import MemoryVectorStore


def _make_chunk(text: str, idx: int) -> Chunk:
    c = Chunk.create(text)
    c.embedding = [float(idx % 2), float((idx + 1) % 2), 0.0]
    return c


def test_concurrent_upserts_do_not_corrupt(tmp_path):
    store = MemoryVectorStore(persist_dir=str(tmp_path))

    errors: list[Exception] = []

    def upsert_batch(thread_id: int) -> None:
        try:
            chunks = [_make_chunk(f"text-{thread_id}-{i}", thread_id + i) for i in range(10)]
            store.upsert(chunks, tenant_id="shared", doc_path=f"/doc{thread_id}.txt")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=upsert_batch, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Exceptions during concurrent upsert: {errors}"
    assert store.total_chunks > 0


def test_concurrent_search_during_upsert(tmp_path):
    store = MemoryVectorStore(persist_dir=str(tmp_path))
    # Pre-populate
    chunks = [_make_chunk(f"base text {i}", i) for i in range(20)]
    store.upsert(chunks, tenant_id="t1", doc_path="/base.txt")

    errors: list[Exception] = []
    query_vec = [1.0, 0.0, 0.0]

    def search_repeatedly() -> None:
        try:
            for _ in range(50):
                store.search(query_vec, tenant_id="t1", top_k=5)
        except Exception as exc:
            errors.append(exc)

    def upsert_repeatedly() -> None:
        try:
            for i in range(20):
                c = _make_chunk(f"new {i}", i)
                store.upsert([c], tenant_id="t1", doc_path=f"/new{i}.txt")
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=search_repeatedly),
        threading.Thread(target=upsert_repeatedly),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Exceptions during concurrent access: {errors}"


def test_concurrent_save_does_not_corrupt_file(tmp_path):
    store = MemoryVectorStore(persist_dir=str(tmp_path))
    chunks = [_make_chunk(f"doc {i}", i) for i in range(10)]
    store.upsert(chunks, tenant_id="t1", doc_path="/doc.txt")

    errors: list[Exception] = []

    def save_loop() -> None:
        try:
            for _ in range(10):
                store.save()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=save_loop) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors

    # File should still be loadable
    store2 = MemoryVectorStore(persist_dir=str(tmp_path))
    store2.load()
    assert store2.total_chunks == 10
