"""
docintel — Industrial Document Analysis Framework
==================================================

Quickstart
----------
>>> import docintel as di
>>> di.configure(gemini_api_key="YOUR_KEY")
>>> di.ingest("manual.pdf")
>>> result = di.ask("What is the maximum operating pressure?")
>>> print(result.answer)

Class-based (for multi-tenant or multi-pipeline setups):
>>> from docintel import Pipeline
>>> p = Pipeline(gemini_api_key="YOUR_KEY", tenant_id="plant_a")
>>> p.ingest("blueprint.pdf", tenant_id="plant_a")
>>> results = p.search("hydraulic pump specs")
"""

from docintel._config import Config
from docintel._pipeline import Pipeline
from docintel.core.entities import Chunk, Document, QueryResult, SearchResult

__version__ = "0.1.0"
__all__ = [
    "Pipeline",
    "Config",
    "configure",
    "ingest",
    "ask",
    "search",
    "delete",
    "stats",
    "Document",
    "Chunk",
    "SearchResult",
    "QueryResult",
]

# ---------------------------------------------------------------------------
# Module-level singleton API
# ---------------------------------------------------------------------------

_default: Pipeline | None = None


def _get() -> Pipeline:
    if _default is None:
        raise RuntimeError(
            "Call di.configure(gemini_api_key='...') before using module-level functions."
        )
    return _default


def configure(
    gemini_api_key: str,
    *,
    generation_model: str = "gemini-2.5-flash",
    embedding_model: str = "gemini-embedding-001",
    chunk_size: int = 600,
    chunk_overlap: int = 80,
    top_k: int = 5,
    vector_store: str = "memory",
    persist_dir: str | None = None,
    db_url: str | None = None,
    qdrant_url: str | None = None,
) -> Pipeline:
    """
    Initialise the default pipeline.

    Call this once at the top of your script:
        import docintel as di
        di.configure(gemini_api_key="...")
    """
    global _default
    cfg = Config(
        gemini_api_key=gemini_api_key,
        generation_model=generation_model,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        vector_store=vector_store,
        persist_dir=persist_dir,
        db_url=db_url,
        qdrant_url=qdrant_url,
    )
    _default = Pipeline(cfg)
    return _default


def ingest(path: str, tenant_id: str = "default", summarize: bool = True, verbose: bool = True) -> Document:
    """Ingest a document into the default pipeline."""
    return _get().ingest(path, tenant_id=tenant_id, summarize=summarize, verbose=verbose)


def ask(question: str, tenant_id: str = "default", top_k: int | None = None) -> QueryResult:
    """RAG query against the default pipeline."""
    return _get().ask(question, tenant_id=tenant_id, top_k=top_k)


def search(query: str, tenant_id: str = "default", top_k: int | None = None) -> list[SearchResult]:
    """Semantic similarity search against the default pipeline."""
    return _get().search(query, tenant_id=tenant_id, top_k=top_k)


def delete(path: str, tenant_id: str = "default") -> None:
    """Remove a document from the default pipeline's index."""
    _get().delete(path, tenant_id=tenant_id)


def stats() -> dict:
    """Return store statistics from the default pipeline."""
    return _get().stats()
