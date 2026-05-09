"""Pipeline error-path tests."""
from __future__ import annotations
import pytest

from docintel import Pipeline


def test_ingest_raises_on_missing_file(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    pipeline = Pipeline(gemini_api_key="fake", persist_dir=str(tmp_path / "idx"))
    with pytest.raises(FileNotFoundError, match="does not exist"):
        pipeline.ingest(str(tmp_path / "ghost.txt"))


def test_ingest_raises_on_directory_path(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    pipeline = Pipeline(gemini_api_key="fake", persist_dir=str(tmp_path / "idx"))
    with pytest.raises(ValueError, match="must be a file"):
        pipeline.ingest(str(tmp_path))


def test_ingest_raises_on_unsupported_extension(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    bad = tmp_path / "drawing.xlsx"
    bad.write_text("data", encoding="utf-8")
    pipeline = Pipeline(gemini_api_key="fake", persist_dir=str(tmp_path / "idx"))
    with pytest.raises(ValueError, match="Unsupported file type"):
        pipeline.ingest(str(bad))


def test_ingest_raises_when_extraction_returns_empty(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    monkeypatch.setattr("docintel._pipeline.TextExtractor.extract", lambda self, p: [])
    doc = tmp_path / "empty.txt"
    doc.write_text("", encoding="utf-8")
    pipeline = Pipeline(gemini_api_key="fake", persist_dir=str(tmp_path / "idx"))
    with pytest.raises(ValueError, match="No extractable text"):
        pipeline.ingest(str(doc))


def test_ingest_raises_when_no_chunks_produced(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    # Use a very high min_chunk_size so every chunk is discarded
    doc = tmp_path / "short.txt"
    doc.write_text("Hi.", encoding="utf-8")
    pipeline = Pipeline(
        gemini_api_key="fake",
        persist_dir=str(tmp_path / "idx"),
        min_chunk_size=10000,
        chunk_size=10001,
        chunk_overlap=0,
    )
    with pytest.raises(ValueError, match="No chunks"):
        pipeline.ingest(str(doc), summarize=False)


def test_embed_api_failure_propagates(monkeypatch, fake_gemini_cls, tmp_path):
    def bad_embed_texts(self, texts):
        raise RuntimeError("API quota exceeded")

    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    monkeypatch.setattr(fake_gemini_cls, "embed_texts", bad_embed_texts)

    doc = tmp_path / "manual.txt"
    doc.write_text("Safety procedure requires lockout.", encoding="utf-8")
    pipeline = Pipeline(
        gemini_api_key="fake",
        persist_dir=str(tmp_path / "idx"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )
    with pytest.raises(RuntimeError, match="API quota"):
        pipeline.ingest(str(doc), summarize=False)


def test_search_on_unknown_tenant_returns_empty(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    pipeline = Pipeline(gemini_api_key="fake", persist_dir=str(tmp_path / "idx"))
    results = pipeline.search("anything", tenant_id="nonexistent")
    assert results == []


def test_ask_no_documents_returns_fallback(monkeypatch, fake_gemini_cls, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    pipeline = Pipeline(gemini_api_key="fake", persist_dir=str(tmp_path / "idx"))
    result = pipeline.ask("What is X?", tenant_id="empty_tenant")
    assert "No relevant documents" in result.answer
    assert result.sources == []
