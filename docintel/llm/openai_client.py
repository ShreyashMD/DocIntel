from __future__ import annotations
import logging
from typing import List

from docintel.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """LLM + embedding provider backed by the OpenAI API."""

    def __init__(self, config) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "OpenAI provider requires: pip install 'docintel[openai]'"
            ) from exc
        self._config = config
        self._client = openai.OpenAI(api_key=config.openai_api_key)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        resp = self._client.embeddings.create(
            model=self._config.embedding_model,
            input=texts,
        )
        return [list(e.embedding) for e in resp.data]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    def generate(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._config.generation_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
