import pytest

from docintel._config import Config


def test_config_rejects_missing_api_key() -> None:
    with pytest.raises(ValueError, match="gemini_api_key"):
        Config(gemini_api_key="")


def test_config_rejects_invalid_chunk_overlap() -> None:
    with pytest.raises(ValueError, match="chunk_overlap"):
        Config(gemini_api_key="key", chunk_size=100, chunk_overlap=100)


def test_config_requires_backend_urls() -> None:
    with pytest.raises(ValueError, match="db_url"):
        Config(gemini_api_key="key", vector_store="pgvector")

    with pytest.raises(ValueError, match="qdrant_url"):
        Config(gemini_api_key="key", vector_store="qdrant")

