from __future__ import annotations
from typing import List

from docintel.core.entities import Chunk
from docintel.llm.gemini import GeminiClient


class Embedder:
    def __init__(self, client: GeminiClient) -> None:
        self._client = client

    def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Embed all chunks in-place and return them."""
        # Use the richer _embed_text if available (contains breadcrumb + summary)
        texts = [c.metadata.get("_embed_text", c.text) for c in chunks]
        vectors = self._client.embed_texts(texts)
        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector
        return chunks

    def embed_query(self, query: str) -> List[float]:
        return self._client.embed_query(query)
