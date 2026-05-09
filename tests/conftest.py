"""Shared fixtures for the docintel test suite."""
from __future__ import annotations
import pytest

from docintel._config import Config


class FakeGeminiClient:
    """Deterministic LLM/embedding client — no network calls required."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def generate(self, prompt: str) -> str:
        return f"answered: {prompt[:80]}"

    def summarize(self, text: str, max_words: int = 120) -> str:
        words = text.split()
        return "summary: " + (words[0] if words else "empty")

    def answer(self, question: str, context: str) -> str:
        return f"answered: {question} | grounded={bool(context)}"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

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


@pytest.fixture
def fake_gemini_cls():
    """Returns the FakeGeminiClient class for monkeypatching."""
    return FakeGeminiClient


@pytest.fixture
def tmp_text_file(tmp_path):
    """A temp .txt file with a predictable structure."""
    p = tmp_path / "doc.txt"
    p.write_text(
        "Safety Manual\n\nSafety procedure requires lockout tagout.\n\n"
        "Pump Section\n\nThe pump pressure limit is 10 bar.",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def base_config(tmp_path):
    """Minimal pipeline Config backed by the memory store."""
    return Config(
        gemini_api_key="fake-key",
        persist_dir=str(tmp_path / "index"),
        chunk_size=20,
        chunk_overlap=0,
        min_chunk_size=0,
    )
