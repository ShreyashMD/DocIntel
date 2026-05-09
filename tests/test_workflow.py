from __future__ import annotations

import docintel as di
from docintel import Config, Pipeline
import pytest


class FakeGeminiClient:
    def __init__(self, config: Config) -> None:
        self.config = config

    def summarize(self, text: str, max_words: int = 120) -> str:
        return "summary: " + text.split()[0]

    def answer(self, question: str, context: str) -> str:
        return f"answered: {question} | grounded={bool(context)}"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        lower = text.lower()
        return [
            float("pump" in lower),
            float("valve" in lower),
            float("safety" in lower),
        ]


def test_full_pipeline_workflow_with_fake_llm(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("docintel._pipeline.GeminiClient", FakeGeminiClient)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    pump_doc = docs_dir / "pump.txt"
    valve_doc = docs_dir / "valve.md"
    ignored_doc = docs_dir / "ignored.csv"
    pump_doc.write_text("Pump Manual\n\nThe pump pressure limit is 10 bar.", encoding="utf-8")
    valve_doc.write_text("# Valve Manual\n\nThe valve has a safety lock.", encoding="utf-8")
    ignored_doc.write_text("unsupported", encoding="utf-8")

    pipeline = Pipeline(
        gemini_api_key="fake-key",
        persist_dir=str(tmp_path / "index"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )

    documents = pipeline.ingest_dir(str(docs_dir), tenant_id="plant_a", verbose=False)
    stats = pipeline.stats()
    hits = pipeline.search("pump", tenant_id="plant_a", top_k=1)
    answer = pipeline.ask("What is the pump pressure limit?", tenant_id="plant_a", top_k=1)

    assert [doc.metadata["file_name"] for doc in documents] == ["pump.txt", "valve.md"]
    assert stats == {"total_chunks": 2, "tenants": ["plant_a"]}
    assert hits[0].document_path == str(pump_doc.resolve())
    assert hits[0].chunk.metadata["page"] == 2
    assert answer.answer.startswith("answered: What is the pump pressure limit?")
    assert answer.sources[0].document_path == str(pump_doc.resolve())

    reloaded = Pipeline(
        gemini_api_key="fake-key",
        persist_dir=str(tmp_path / "index"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )
    reloaded._llm = FakeGeminiClient(reloaded._config)
    reloaded._embedder._client = reloaded._llm

    assert reloaded.search("valve", tenant_id="plant_a", top_k=1)[0].document_path == str(
        valve_doc.resolve()
    )

    pipeline.delete(str(pump_doc), tenant_id="plant_a")
    remaining = pipeline.search("pump", tenant_id="plant_a", top_k=5)

    assert all(result.document_path != str(pump_doc.resolve()) for result in remaining)


def test_module_level_workflow_delegates_to_default_pipeline(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("docintel._pipeline.GeminiClient", FakeGeminiClient)
    doc = tmp_path / "manual.txt"
    doc.write_text("Safety Manual\n\nSafety procedure requires lockout.", encoding="utf-8")

    di.configure(
        gemini_api_key="fake-key",
        persist_dir=str(tmp_path / "index"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )

    ingested = di.ingest(str(doc), summarize=False, verbose=False)
    hits = di.search("safety", top_k=1)
    answer = di.ask("What does safety require?", top_k=1)

    assert ingested.metadata["sha256"]
    assert hits[0].document_path == str(doc.resolve())
    assert answer.sources[0].chunk.text == "Safety procedure requires lockout."


def test_pipeline_reports_empty_and_unsupported_workflow_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("docintel._pipeline.GeminiClient", FakeGeminiClient)
    unsupported = tmp_path / "drawing.csv"
    unsupported.write_text("ignored", encoding="utf-8")

    pipeline = Pipeline(gemini_api_key="fake-key", persist_dir=str(tmp_path / "index"))
    empty_answer = pipeline.ask("anything?", tenant_id="missing")

    assert empty_answer.sources == []
    assert "No relevant documents found" in empty_answer.answer

    with pytest.raises(ValueError, match="Unsupported file type"):
        pipeline.ingest(str(unsupported), verbose=False)
