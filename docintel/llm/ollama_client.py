from __future__ import annotations
import logging
from typing import List

from docintel.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """
    LLM + embedding provider backed by a local Ollama server.
    No API key needed — just a running Ollama instance.

    Config:
        provider = "ollama"
        ollama_base_url = "http://localhost:11434"   # default
        generation_model = "llama3.2"                # default
        embedding_model = "nomic-embed-text"         # default
    """

    def __init__(self, config) -> None:
        self._config = config
        self._base = config.ollama_base_url.rstrip("/")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        import requests
        resp = requests.post(
            f"{self._base}/api/embed",
            json={"model": self._config.embedding_model, "input": texts},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    def generate(self, prompt: str) -> str:
        import requests
        resp = requests.post(
            f"{self._base}/api/chat",
            json={
                "model": self._config.generation_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
