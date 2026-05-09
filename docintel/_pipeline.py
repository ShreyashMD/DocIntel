from __future__ import annotations
import hashlib
import logging
import pathlib
import time
import uuid
from typing import Iterable, List, Optional

from docintel._config import Config
from docintel.core.entities import Document, QueryResult, SearchResult
from docintel.extractors.pdf import PdfExtractor
from docintel.extractors.text import TextExtractor
from docintel.llm.gemini import GeminiClient  # kept at module level so tests can monkeypatch it
from docintel.llm.base import BaseLLMClient
from docintel.logging import get_correlation_id, set_correlation_id
from docintel.metrics import increment
from docintel.processing.chunker import HierarchicalChunker
from docintel.processing.embedder import Embedder
from docintel.storage.base import VectorStore
from docintel.storage.memory import MemoryVectorStore


_EXTRACTOR_MAP = {
    ".pdf": PdfExtractor,
    ".txt": TextExtractor,
    ".md": TextExtractor,
    ".rst": TextExtractor,
    ".log": TextExtractor,
}

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Central orchestrator for the docintel framework.

    Usage
    -----
    >>> import docintel as di
    >>> di.configure(gemini_api_key="...")
    >>> di.ingest("manual.pdf")
    >>> answer = di.ask("What is the maximum operating pressure?")

    Or class-based:
    >>> from docintel import Pipeline
    >>> p = Pipeline(gemini_api_key="...")
    >>> p.ingest("schematic.pdf", tenant_id="plant_a")
    >>> result = p.search("hydraulic pump")
    """

    def __init__(self, config: Config | None = None, **kwargs) -> None:
        if config is None:
            config = Config(**kwargs)
        self._config = config

        self._llm = _build_llm_client(config)
        self._lightrag = _build_lightrag(config, self._llm) if config.rag_mode != "vector" else None
        self._chunker = HierarchicalChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            min_chunk_size=config.min_chunk_size,
        )
        self._embedder = Embedder(self._llm)
        self._store: VectorStore = self._build_store()
        self._store.load()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def ingest(
        self,
        path: str,
        tenant_id: str = "default",
        summarize: bool = True,
        verbose: bool = True,
    ) -> Document:
        """
        Ingest a document: extract → summarize → chunk → embed → store.

        Parameters
        ----------
        path       : Path to the document file (PDF, TXT, MD, …).
        tenant_id  : Logical namespace / organisation identifier.
        summarize  : Whether to generate a document-level summary for
                     Contextual Retrieval. Counts toward Gemini quota.
        verbose    : Print progress to stdout.
        """
        if get_correlation_id() is None:
            set_correlation_id(str(uuid.uuid4()))

        resolved = pathlib.Path(path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Document does not exist: {resolved}")
        if not resolved.is_file():
            raise ValueError(f"Document path must be a file: {resolved}")

        path = str(resolved)
        doc = Document.create(path, tenant_id=tenant_id)
        doc.metadata.update(
            {
                "file_name": resolved.name,
                "file_suffix": resolved.suffix.lower(),
                "file_size": resolved.stat().st_size,
                "sha256": _sha256(resolved),
            }
        )
        t_total = time.perf_counter()

        # 1. Extract
        t0 = time.perf_counter()
        if verbose:
            logger.info("extract", extra={"path": path, "tenant": tenant_id})
        pages = self._extract(path)
        if not pages:
            raise ValueError(f"No extractable text found in document: {path}")
        logger.debug("extract_done", extra={"pages": len(pages), "ms": _ms(t0)})

        # 2. Summarize (Contextual Retrieval)
        doc_summary = ""
        if summarize:
            full_text = "\n\n".join(t for _, t in pages)
            t0 = time.perf_counter()
            if verbose:
                logger.info("summarize", extra={"path": path})
            doc_summary = self._llm.summarize(full_text)
            doc.summary = doc_summary
            logger.debug("summarize_done", extra={"ms": _ms(t0)})

        # 3. Hierarchical chunk
        t0 = time.perf_counter()
        if verbose:
            logger.info("chunk", extra={"path": path})
        chunks = self._chunker.chunk_pages(pages, doc_path=path, doc_summary=doc_summary)
        if not chunks:
            raise ValueError(f"No chunks were produced for document: {path}")
        doc.chunks = chunks
        logger.debug("chunk_done", extra={"chunks": len(chunks), "ms": _ms(t0)})

        # 4. Embed
        t0 = time.perf_counter()
        if verbose:
            logger.info("embed", extra={"chunks": len(chunks), "path": path})
        embedded = self._embedder.embed_chunks(chunks)
        logger.debug("embed_done", extra={"ms": _ms(t0)})

        # 5. Store in vector index
        t0 = time.perf_counter()
        self._store.upsert(embedded, tenant_id=tenant_id, doc_path=path)
        self._store.save()
        logger.debug("store_done", extra={"ms": _ms(t0)})

        # 6. Also index into LightRAG knowledge graph (graph / hybrid modes)
        if self._lightrag is not None:
            t0 = time.perf_counter()
            full_text = "\n\n".join(t for _, t in pages)
            self._lightrag.insert(full_text)
            logger.debug("lightrag_done", extra={"ms": _ms(t0)})

        increment("docs_ingested")
        increment("chunks_indexed", by=len(embedded))
        logger.info(
            "ingest_done",
            extra={
                "path": path,
                "tenant": tenant_id,
                "chunks": len(embedded),
                "ms": _ms(t_total),
            },
        )
        return doc

    def ingest_dir(
        self,
        path: str,
        tenant_id: str = "default",
        summarize: bool = True,
        recursive: bool = True,
        verbose: bool = True,
    ) -> list[Document]:
        """Ingest all supported files in a directory."""
        root = pathlib.Path(path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Directory does not exist: {root}")
        if not root.is_dir():
            raise ValueError(f"Path must be a directory: {root}")

        documents: list[Document] = []
        for file_path in self._iter_supported_files(root, recursive=recursive):
            documents.append(
                self.ingest(
                    str(file_path),
                    tenant_id=tenant_id,
                    summarize=summarize,
                    verbose=verbose,
                )
            )
        return documents

    def search(
        self,
        query: str,
        tenant_id: str = "default",
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """Semantic similarity search. Returns ranked SearchResult objects."""
        if get_correlation_id() is None:
            set_correlation_id(str(uuid.uuid4()))
        k = top_k or self._config.top_k
        t0 = time.perf_counter()
        vector = self._embedder.embed_query(query)
        results = self._store.search(vector, tenant_id=tenant_id, top_k=k)
        increment("queries")
        logger.debug("search_done", extra={"hits": len(results), "ms": _ms(t0), "tenant": tenant_id})
        return results

    def ask(
        self,
        question: str,
        tenant_id: str = "default",
        top_k: Optional[int] = None,
    ) -> QueryResult:
        """
        RAG query: retrieve relevant chunks, then generate an answer with Gemini.

        Returns a QueryResult with .answer (str) and .sources (list[SearchResult]).
        """
        if get_correlation_id() is None:
            set_correlation_id(str(uuid.uuid4()))
        t0 = time.perf_counter()
        mode = self._config.rag_mode

        # Graph-only: skip vector store entirely, let LightRAG answer
        if mode == "graph" and self._lightrag is not None:
            answer = self._lightrag.query(question, mode="hybrid")
            logger.info("ask_done", extra={"tenant": tenant_id, "mode": "graph", "ms": _ms(t0)})
            return QueryResult(
                question=question,
                answer=answer,
                sources=[],
                model=self._config.generation_model,
            )

        # Vector or hybrid: always do vector search for structured sources
        results = self.search(question, tenant_id=tenant_id, top_k=top_k)
        if not results:
            return QueryResult(
                question=question,
                answer="No relevant documents found. Please ingest documents first.",
                sources=[],
                model=self._config.generation_model,
            )

        if mode == "hybrid" and self._lightrag is not None:
            # Graph answer is richer (entity/relationship reasoning); vector sources provide citations
            answer = self._lightrag.query(question, mode="hybrid")
        else:
            context = self._build_context(results)
            answer = self._llm.answer(question, context)

        logger.info("ask_done", extra={"tenant": tenant_id, "sources": len(results), "ms": _ms(t0)})
        return QueryResult(
            question=question,
            answer=answer,
            sources=results,
            model=self._config.generation_model,
        )

    def delete(self, path: str, tenant_id: str = "default") -> None:
        """Remove all chunks for a specific document from the store."""
        path = str(pathlib.Path(path).resolve())
        self._store.delete_document(path, tenant_id=tenant_id)
        self._store.save()

    def stats(self) -> dict:
        """Return basic store statistics."""
        store = self._store
        if hasattr(store, "total_chunks"):
            return {"total_chunks": store.total_chunks, "tenants": store.tenants()}
        return {"store": type(store).__name__}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _extract(self, path: str) -> list[tuple[int, str]]:
        suffix = pathlib.Path(path).suffix.lower()
        extractor_cls = _EXTRACTOR_MAP.get(suffix)
        if extractor_cls is None:
            raise ValueError(
                f"Unsupported file type '{suffix}'. "
                f"Supported: {list(_EXTRACTOR_MAP)}"
            )
        return extractor_cls().extract(path)

    @classmethod
    def supported_extensions(cls) -> tuple[str, ...]:
        """Return file extensions currently supported by the installed extractors."""
        return tuple(sorted(_EXTRACTOR_MAP))

    @classmethod
    def _iter_supported_files(cls, root: pathlib.Path, recursive: bool) -> Iterable[pathlib.Path]:
        paths = root.rglob("*") if recursive else root.glob("*")
        for path in sorted(paths):
            if path.is_file() and path.suffix.lower() in _EXTRACTOR_MAP:
                yield path

    def _build_store(self) -> VectorStore:
        backend = self._config.vector_store
        if backend == "memory":
            persist = self._config.persist_dir or ".docintel"
            return MemoryVectorStore(persist_dir=persist)
        if backend == "pgvector":
            from docintel.storage.pgvector import PgVectorStore
            return PgVectorStore(
                db_url=self._config.db_url,
                embedding_dim=self._config.embedding_dim,
                pool_min=self._config.pg_pool_min,
                pool_max=self._config.pg_pool_max,
            )
        if backend == "qdrant":
            from docintel.storage.qdrant import QdrantStore  # optional dep
            return QdrantStore(self._config.qdrant_url)
        raise ValueError(f"Unknown vector_store backend: '{backend}'")

    @staticmethod
    def _build_context(results: List[SearchResult]) -> str:
        parts = []
        for i, r in enumerate(results, 1):
            bc = r.chunk.metadata.get("breadcrumb", r.document_path)
            page = r.chunk.metadata.get("page")
            source = f"{bc} | page {page}" if page is not None else bc
            parts.append(f"[Source {i} | {source}]\n{r.chunk.text}")
        return "\n\n---\n\n".join(parts)


def _build_llm_client(config: Config) -> BaseLLMClient:
    """Factory: select LLM client based on config.provider.
    GeminiClient is referenced by name so tests can monkeypatch docintel._pipeline.GeminiClient.
    """
    provider = config.provider
    if provider == "gemini":
        return GeminiClient(config)
    if provider == "openai":
        from docintel.llm.openai_client import OpenAIClient
        return OpenAIClient(config)
    if provider == "anthropic":
        from docintel.llm.anthropic_client import AnthropicClient
        return AnthropicClient(config)
    if provider == "ollama":
        from docintel.llm.ollama_client import OllamaClient
        return OllamaClient(config)
    raise ValueError(f"Unknown provider: '{provider}'")


def _build_lightrag(config: Config, llm_client: BaseLLMClient):
    from docintel.lightrag_index import LightRAGIndex
    return LightRAGIndex(config, llm_client)


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
