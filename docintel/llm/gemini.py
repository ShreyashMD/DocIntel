from __future__ import annotations
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from google import genai
from tenacity import Retrying, RetryCallState, retry_if_exception_type, stop_after_attempt, wait_exponential

from docintel._config import Config
from docintel.llm.base import BaseLLMClient
from docintel.metrics import increment

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = genai.Client(api_key=config.gemini_api_key)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        batch_size = self._config.embed_batch_size
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
        if len(batches) <= 1:
            return self._embed_batch(batches[0]) if batches else []

        results: list[list[list[float]] | None] = [None] * len(batches)
        max_workers = min(4, len(batches))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_idx = {pool.submit(self._embed_batch, b): i for i, b in enumerate(batches)}
            for fut in as_completed(future_to_idx):
                results[future_to_idx[fut]] = fut.result()
        return [v for batch in results for v in batch]

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        for attempt in self._retrying(min_wait=2, max_wait=60):
            with attempt:
                response = self._client.models.embed_content(
                    model=self._config.embedding_model,
                    contents=texts,
                )
        increment("embed_api_calls")
        return [list(e.values) for e in response.embeddings]

    def embed_query(self, text: str) -> List[float]:
        for attempt in self._retrying(min_wait=2, max_wait=60):
            with attempt:
                response = self._client.models.embed_content(
                    model=self._config.embedding_model,
                    contents=[text],
                )
        return list(response.embeddings[0].values)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, prompt: str) -> str:
        for attempt in self._retrying(min_wait=4, max_wait=120):
            with attempt:
                response = self._client.models.generate_content(
                    model=self._config.generation_model,
                    contents=prompt,
                )
        return response.text.strip()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _retrying(self, min_wait: int, max_wait: int) -> Retrying:
        return Retrying(
            retry=retry_if_exception_type(Exception),
            wait=wait_exponential(multiplier=2, min=min_wait, max=max_wait),
            stop=stop_after_attempt(self._config.max_retries),
            before_sleep=_log_retry,
            reraise=True,
        )


def _log_retry(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception()
    increment("retries")
    logger.warning(
        "API retry",
        extra={
            "attempt": retry_state.attempt_number,
            "exc_type": type(exc).__name__,
            "wait_s": round(retry_state.next_action.sleep, 1) if retry_state.next_action else 0,
        },
    )
