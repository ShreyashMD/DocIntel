from __future__ import annotations
import logging
from typing import List

from docintel.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """
    Generation via Anthropic Claude. Embeddings are delegated to a companion
    provider (OpenAI or Ollama) because Anthropic provides no embedding API.

    Config requirements:
        provider = "anthropic"
        anthropic_api_key = "sk-ant-..."
        embedding_provider = "openai"   # or "ollama"
        openai_api_key = "sk-..."       # if embedding_provider = "openai"
    """

    def __init__(self, config) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "Anthropic provider requires: pip install 'docintel[anthropic]'"
            ) from exc
        self._config = config
        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self._embed_client = _build_embed_client(config)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self._embed_client.embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed_client.embed_query(text)

    def generate(self, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self._config.generation_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()


def _build_embed_client(config) -> BaseLLMClient:
    ep = config.embedding_provider
    if ep == "openai":
        from docintel.llm.openai_client import OpenAIClient
        return OpenAIClient(config)
    if ep == "ollama":
        from docintel.llm.ollama_client import OllamaClient
        return OllamaClient(config)
    raise ValueError(
        f"Unsupported embedding_provider '{ep}' for Anthropic. "
        "Use 'openai' or 'ollama'."
    )
