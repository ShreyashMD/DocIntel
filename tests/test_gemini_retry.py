"""Tests for Tenacity retry logic in GeminiClient."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

from docintel._config import Config
from docintel.llm.gemini import GeminiClient
import docintel.metrics as metrics_module


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics_module.reset()
    yield
    metrics_module.reset()


def _make_client(max_retries: int = 3) -> GeminiClient:
    cfg = Config(gemini_api_key="fake", max_retries=max_retries)
    client = GeminiClient.__new__(GeminiClient)
    client._config = cfg
    return client


def test_embed_batch_retries_on_transient_error():
    call_count = 0

    class FakeEmbedding:
        values = [0.1, 0.2, 0.3]

    class FakeResponse:
        embeddings = [FakeEmbedding()]

    def fake_embed(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("transient")
        return FakeResponse()

    client = _make_client(max_retries=5)
    mock_models = MagicMock()
    mock_models.embed_content.side_effect = fake_embed
    client._client = MagicMock(models=mock_models)

    result = client._embed_batch(["test text"])
    assert call_count == 3
    assert result == [[0.1, 0.2, 0.3]]


def test_embed_batch_raises_after_max_retries():
    client = _make_client(max_retries=3)
    mock_models = MagicMock()
    mock_models.embed_content.side_effect = RuntimeError("persistent error")
    client._client = MagicMock(models=mock_models)

    with pytest.raises(RuntimeError, match="persistent error"):
        client._embed_batch(["text"])

    assert mock_models.embed_content.call_count == 3


def test_retry_increments_metrics():
    call_count = 0

    class FakeResp:
        embeddings = [MagicMock(values=[0.0])]

    def raise_once(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("blip")
        return FakeResp()

    client = _make_client(max_retries=5)
    mock_models = MagicMock()
    mock_models.embed_content.side_effect = raise_once
    client._client = MagicMock(models=mock_models)

    client._embed_batch(["text"])
    m = metrics_module.get_metrics()
    assert m["retries"] >= 1


def test_generate_retries_then_succeeds():
    call_count = 0

    def fake_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TimeoutError("timeout")
        resp = MagicMock()
        resp.text = "  answer  "
        return resp

    client = _make_client(max_retries=5)
    mock_models = MagicMock()
    mock_models.generate_content.side_effect = fake_generate
    client._client = MagicMock(models=mock_models)

    result = client.generate("prompt")
    assert result == "answer"
    assert call_count == 2
