"""Tests for structured JSON logging and correlation ID propagation."""
from __future__ import annotations
import json
import logging
import io

import pytest

from docintel.logging import (
    _JsonFormatter,
    configure_logging,
    get_correlation_id,
    set_correlation_id,
)
import docintel.metrics as metrics_module
from docintel import Pipeline


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics_module.reset()
    yield
    metrics_module.reset()


def _capture_log(level: int = logging.DEBUG) -> tuple[logging.Handler, io.StringIO]:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(_JsonFormatter())
    handler.setLevel(level)
    return handler, buf


def test_json_formatter_emits_required_fields():
    handler, buf = _capture_log()
    log = logging.getLogger("test_json_fields")
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    log.info("hello world")

    output = json.loads(buf.getvalue().strip())
    assert output["level"] == "INFO"
    assert output["msg"] == "hello world"
    assert "time" in output
    assert "logger" in output

    log.removeHandler(handler)


def test_json_formatter_includes_extra_fields():
    handler, buf = _capture_log()
    log = logging.getLogger("test_extras")
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    log.info("op done", extra={"tenant": "plant_a", "ms": 42})

    output = json.loads(buf.getvalue().strip())
    assert output["tenant"] == "plant_a"
    assert output["ms"] == 42

    log.removeHandler(handler)


def test_correlation_id_appears_in_log():
    handler, buf = _capture_log()
    log = logging.getLogger("test_cid")
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    token = set_correlation_id("abc-123")
    log.info("tracing test")

    output = json.loads(buf.getvalue().strip())
    assert output.get("correlation_id") == "abc-123"

    # Reset
    from docintel.logging import _correlation_id
    _correlation_id.reset(token)
    log.removeHandler(handler)


def test_no_correlation_id_when_unset():
    from docintel.logging import _correlation_id
    token = _correlation_id.set(None)
    handler, buf = _capture_log()
    log = logging.getLogger("test_no_cid")
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    log.info("no cid")
    output = json.loads(buf.getvalue().strip())
    assert "correlation_id" not in output

    _correlation_id.reset(token)
    log.removeHandler(handler)


def test_pipeline_sets_correlation_id_on_ingest(monkeypatch, fake_gemini_cls, tmp_text_file, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    # Reset correlation id
    from docintel.logging import _correlation_id
    token = _correlation_id.set(None)

    pipeline = Pipeline(
        gemini_api_key="fake",
        persist_dir=str(tmp_path / "idx"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )
    pipeline.ingest(str(tmp_text_file), summarize=False, verbose=False)

    # Correlation ID should have been set during ingest
    cid = get_correlation_id()
    assert cid is not None
    assert len(cid) > 0

    _correlation_id.reset(token)


def test_metrics_increment_on_ingest(monkeypatch, fake_gemini_cls, tmp_text_file, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    pipeline = Pipeline(
        gemini_api_key="fake",
        persist_dir=str(tmp_path / "idx"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )
    pipeline.ingest(str(tmp_text_file), summarize=False, verbose=False)

    m = metrics_module.get_metrics()
    assert m["docs_ingested"] == 1
    assert m["chunks_indexed"] > 0


def test_metrics_increment_on_query(monkeypatch, fake_gemini_cls, tmp_text_file, tmp_path):
    monkeypatch.setattr("docintel._pipeline.GeminiClient", fake_gemini_cls)
    pipeline = Pipeline(
        gemini_api_key="fake",
        persist_dir=str(tmp_path / "idx"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )
    pipeline.ingest(str(tmp_text_file), summarize=False, verbose=False)
    pipeline.ask("What is lockout?")

    m = metrics_module.get_metrics()
    assert m["queries"] >= 1
