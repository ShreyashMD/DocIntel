from __future__ import annotations
import pathlib
from typing import List, Optional

from docintel._config import Config
from docintel.core.entities import Document, QueryResult, SearchResult
from docintel.extractors.pdf import PdfExtractor
from docintel.extractors.text import TextExtractor
from docintel.llm.gemini import GeminiClient
from docintel.processing.chunker import HierarchicalChunker
from docintel.processing.embedder import Embedder
from docintel.storage.memory import MemoryVectorStore
from docintel.storage.base import VectorStore


_EXTRACTOR_MAP = {
    ".pdf": PdfExtractor,
    ".txt": TextExtractor,
    ".md": TextExtractor,
    ".rst": TextExtractor,
    ".log": TextExtractor,
}


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

        self._llm = GeminiClient(config)
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
        path = str(pathlib.Path(path).resolve())
        doc = Document.create(path, tenant_id=tenant_id)

        # 1. Extract
        if verbose:
            print(f"[docintel] Extracting  {path}")
        pages = self._extract(path)

        # 2. Summarize (Contextual Retrieval)
        doc_summary = ""
        if summarize:
            full_text = "\n\n".join(t for _, t in pages)
            if verbose:
                print("[docintel] Summarizing …")
            doc_summary = self._llm.summarize(full_text)
            doc.summary = doc_summary

        # 3. Hierarchical chunk
        if verbose:
            print("[docintel] Chunking …")
        chunks = self._chunker.chunk_pages(pages, doc_path=path, doc_summary=doc_summary)
        doc.chunks = chunks

        # 4. Embed
        if verbose:
            print(f"[docintel] Embedding {len(chunks)} chunks …")
        embedded = self._embedder.embed_chunks(chunks)

        # 5. Store
        self._store.upsert(embedded, tenant_id=tenant_id, doc_path=path)
        self._store.save()

        if verbose:
            print(f"[docintel] Done. {len(embedded)} chunks indexed for tenant '{tenant_id}'.")
        return doc

    def search(
        self,
        query: str,
        tenant_id: str = "default",
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """Semantic similarity search. Returns ranked SearchResult objects."""
        k = top_k or self._config.top_k
        vector = self._embedder.embed_query(query)
        return self._store.search(vector, tenant_id=tenant_id, top_k=k)

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
        results = self.search(question, tenant_id=tenant_id, top_k=top_k)
        if not results:
            return QueryResult(
                question=question,
                answer="No relevant documents found. Please ingest documents first.",
                sources=[],
                model=self._config.generation_model,
            )

        context = self._build_context(results)
        answer = self._llm.answer(question, context)
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
        if isinstance(store, MemoryVectorStore):
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

    def _build_store(self) -> VectorStore:
        backend = self._config.vector_store
        if backend == "memory":
            persist = self._config.persist_dir or ".docintel"
            return MemoryVectorStore(persist_dir=persist)
        if backend == "pgvector":
            from docintel.storage.pgvector import PgVectorStore  # optional dep
            return PgVectorStore(self._config.db_url)
        if backend == "qdrant":
            from docintel.storage.qdrant import QdrantStore  # optional dep
            return QdrantStore(self._config.qdrant_url)
        raise ValueError(f"Unknown vector_store backend: '{backend}'")

    @staticmethod
    def _build_context(results: List[SearchResult]) -> str:
        parts = []
        for i, r in enumerate(results, 1):
            bc = r.chunk.metadata.get("breadcrumb", r.document_path)
            parts.append(f"[Source {i} | {bc}]\n{r.chunk.text}")
        return "\n\n---\n\n".join(parts)
