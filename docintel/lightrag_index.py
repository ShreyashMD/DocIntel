from __future__ import annotations
import asyncio
import logging
import os
import shutil
import glob as _glob
from typing import TYPE_CHECKING, Union, List

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
        self._working_dir = config.lightrag_dir
        self._dim = config.embedding_dim or 768
        self._LightRAG = LightRAG
        self._EmbeddingFunc = EmbeddingFunc

        self._rag = self._make_rag()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_rag(self):
        """Create a fresh LightRAG instance with clean in-memory state."""
        client = self._client

        async def _llm_func(prompt, system_prompt=None, **kwargs) -> str:
            full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            return await asyncio.to_thread(client.generate, full)

        async def _embed_func(texts):
            import numpy as np
            result = await asyncio.to_thread(client.embed_texts, texts)
            return np.array(result, dtype=np.float32)

        try:
            rag = self._LightRAG(
                working_dir=self._working_dir,
                llm_model_func=_llm_func,
                embedding_func=self._EmbeddingFunc(
                    embedding_dim=self._dim,
                    max_token_size=8192,
                    func=_embed_func,
                ),
            )
        except AssertionError as exc:
            if "Embedding dim mismatch" in str(exc):
                # Provider switched — stale vdb files have wrong dimensions.
                stale = (
                    _glob.glob(os.path.join(self._working_dir, "vdb_*.json"))
                    + _glob.glob(os.path.join(self._working_dir, "*.graphml"))
                )
                for f in stale:
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                logger.warning(
                    "LightRAG embedding dim mismatch — cleared stale vector stores in %s.",
                    self._working_dir,
                )
                rag = self._LightRAG(
                    working_dir=self._working_dir,
                    llm_model_func=_llm_func,
                    embedding_func=self._EmbeddingFunc(
                        embedding_dim=self._dim,
                        max_token_size=8192,
                        func=_embed_func,
                    ),
                )
            else:
                raise
        return rag

    def _run(self, coro, timeout: int = 600):
        """Run a coroutine, handling both async and non-async calling contexts."""
        try:
            loop = asyncio.get_running_loop()
            # Called from inside a running event loop (e.g. FastAPI async handler)
            import concurrent.futures
            fut = asyncio.run_coroutine_threadsafe(coro, loop)
            return fut.result(timeout=timeout)
        except RuntimeError:
            # No running loop — safe to create one (thread pool context)
            return asyncio.run(coro)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def insert(self, text: Union[str, List[str]]) -> None:
        """Index one or more document texts into the knowledge graph."""
        async def _do():
            # Always initialize in the same loop as the operation to avoid
            # event-loop-binding issues with LightRAG's async storage objects.
            await self._rag.initialize_storages()
            await self._rag.ainsert(text)

        chars = len(text) if isinstance(text, str) else sum(len(t) for t in text)
        self._run(_do())
        logger.debug("lightrag insert done", extra={"chars": chars})

    def query(self, question: str, mode: str = "hybrid") -> str:
        """Query the knowledge graph. Returns a generated answer string."""
        from lightrag import QueryParam

        async def _do():
            await self._rag.initialize_storages()
            return await self._rag.aquery(question, param=QueryParam(mode=mode))

        answer = self._run(_do(), timeout=300)
        logger.debug("lightrag query done", extra={"mode": mode})
        return answer

    def clear(self) -> None:
        """Wipe the working directory and reset LightRAG's in-memory state."""
        if os.path.exists(self._working_dir):
            shutil.rmtree(self._working_dir)
        os.makedirs(self._working_dir, exist_ok=True)
        # Recreate the LightRAG instance to discard all cached document hashes
        # and in-memory state — otherwise insert() will reject docs as duplicates.
        self._rag = self._make_rag()
        logger.info("lightrag graph cleared", extra={"dir": self._working_dir})
