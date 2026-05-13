from __future__ import annotations
import logging
from typing import List

from docintel.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaClient(BaseLLMClient):
    """LLM + embedding provider backed by the NVIDIA NIM API (OpenAI-compatible)."""

    def __init__(self, config) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "NVIDIA provider requires: pip install 'docintel[openai]'"
            ) from exc
        self._config = config
        self._client = openai.OpenAI(
            api_key=config.nvidia_api_key,
            base_url=_BASE_URL,
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        batch_size = self._config.embed_batch_size
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = self._client.embeddings.create(
                model=self._config.embedding_model,
                input=batch,
                encoding_format="float",
                extra_body={"input_type": "passage", "truncate": "END"},
            )
            results.extend(list(e.embedding) for e in resp.data)
        return results

    def embed_query(self, text: str) -> List[float]:
        resp = self._client.embeddings.create(
            model=self._config.embedding_model,
            input=[text],
            encoding_format="float",
            extra_body={"input_type": "query", "truncate": "END"},
        )
        return list(resp.data[0].embedding)

    def generate(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._config.generation_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            top_p=0.7,
        )
        return resp.choices[0].message.content.strip()
