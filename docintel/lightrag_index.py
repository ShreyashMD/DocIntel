from __future__ import annotations
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docintel._config import Config
    from docintel.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class LightRAGIndex:
    """
    Graph-based retrieval index wrapping LightRAG.

    Install: pip install 'docintel[graph]'

    LightRAG extracts a knowledge graph (entities + relationships) from documents
    and uses it for retrieval — complementary to pure vector search.

    Modes passed to query():
        "local"  — answers from closely related entities
        "global" — answers from high-level themes across the graph
        "hybrid" — combination of both (recommended)
        "naive"  — plain chunked RAG without graph (for comparison)
    """

    def __init__(self, config: "Config", llm_client: "BaseLLMClient") -> None:
        try:
            from lightrag import LightRAG
            from lightrag.utils import EmbeddingFunc
        except ImportError as exc:
            raise ImportError(
                "LightRAG requires: pip install 'docintel[graph]'"
            ) from exc

        self._client = llm_client
        dim = config.embedding_dim or 768

        async def _llm_func(prompt, system_prompt=None, **kwargs) -> str:
            full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            return await asyncio.to_thread(self._client.generate, full)

        async def _embed_func(texts) -> list[list[float]]:
            return await asyncio.to_thread(self._client.embed_texts, texts)

        self._rag = LightRAG(
            working_dir=config.lightrag_dir,
            llm_model_func=_llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=dim,
                max_token_size=8192,
                func=_embed_func,
            ),
        )

    def insert(self, text: str) -> None:
        """Index a document's full text into the knowledge graph."""
        self._rag.insert(text)
        logger.debug("lightrag insert done", extra={"chars": len(text)})

    def query(self, question: str, mode: str = "hybrid") -> str:
        """Query the knowledge graph. Returns a generated answer string."""
        from lightrag import QueryParam
        answer = self._rag.query(question, param=QueryParam(mode=mode))
        logger.debug("lightrag query done", extra={"mode": mode})
        return answer
