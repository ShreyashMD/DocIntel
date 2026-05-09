from __future__ import annotations
from typing import List

from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from docintel._config import Config


class GeminiClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = genai.Client(api_key=config.gemini_api_key)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts in batches, returning a list of float vectors."""
        results: List[List[float]] = []
        batch_size = self._config.embed_batch_size
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = self._embed_batch(batch)
            results.extend(vectors)
        return results

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = self._client.models.embed_content(
            model=self._config.embedding_model,
            contents=texts,
        )
        return [list(e.values) for e in response.embeddings]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_query_raw(text)

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _embed_query_raw(self, text: str) -> List[float]:
        response = self._client.models.embed_content(
            model=self._config.embedding_model,
            contents=[text],
        )
        return list(response.embeddings[0].values)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._config.generation_model,
            contents=prompt,
        )
        return response.text.strip()

    def summarize(self, text: str, max_words: int = 120) -> str:
        prompt = (
            f"Summarize the following document in at most {max_words} words. "
            "Focus on the domain, main topics, and any key entities (equipment names, "
            "standards, procedures). Be concise.\n\n"
            f"{text[:8000]}"
        )
        return self.generate(prompt)

    def answer(self, question: str, context: str) -> str:
        prompt = (
            "You are an expert industrial document analyst. "
            "Answer the question strictly using the provided context. "
            "If the answer cannot be found in the context, say so explicitly.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}\n\n"
            "ANSWER:"
        )
        return self.generate(prompt)
