import json

import pytest

from docintel.core.entities import Chunk
from docintel.storage.memory import MemoryVectorStore


def _chunk(text: str, vector: list[float]) -> Chunk:
    chunk = Chunk.create(text, {"page": 1, "_embed_text": "private embedding text"})
    chunk.embedding = vector
    return chunk


def test_memory_store_persists_with_schema_and_reloads(tmp_path) -> None:
    store = MemoryVectorStore(persist_dir=str(tmp_path))
    store.upsert([_chunk("pump pressure", [1.0, 0.0])], tenant_id="plant_a", doc_path="a.txt")
    store.save()

    payload = json.loads((tmp_path / "docintel_index.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert "_embed_text" not in payload["index"]["plant_a"][0]["chunk"]["metadata"]

    reloaded = MemoryVectorStore(persist_dir=str(tmp_path))
    reloaded.load()

    results = reloaded.search([1.0, 0.0], tenant_id="plant_a", top_k=1)
    assert results[0].chunk.text == "pump pressure"
    assert results[0].tenant_id == "plant_a"


def test_memory_store_keeps_tenants_isolated(tmp_path) -> None:
    store = MemoryVectorStore(persist_dir=str(tmp_path))
    store.upsert([_chunk("tenant a", [1.0, 0.0])], tenant_id="a", doc_path="a.txt")
    store.upsert([_chunk("tenant b", [0.0, 1.0])], tenant_id="b", doc_path="b.txt")

    results = store.search([1.0, 0.0], tenant_id="a", top_k=5)

    assert [result.tenant_id for result in results] == ["a"]
    assert results[0].chunk.text == "tenant a"


def test_memory_store_reports_corrupt_index(tmp_path) -> None:
    (tmp_path / "docintel_index.json").write_text("{not-json", encoding="utf-8")
    store = MemoryVectorStore(persist_dir=str(tmp_path))

    with pytest.raises(ValueError, match="Corrupt docintel index"):
        store.load()

