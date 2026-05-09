from __future__ import annotations
import argparse

from docintel._config import Config
from docintel.logging import configure_logging
from docintel.server.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="DocIntel HTTP server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)

    # LLM provider
    parser.add_argument("--provider", default="gemini",
                        choices=["gemini", "openai", "anthropic", "ollama"])
    parser.add_argument("--embedding-provider", default=None,
                        help="Embedding provider override (required when --provider=anthropic)")
    parser.add_argument("--gemini-api-key", default=None)
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--anthropic-api-key", default=None)
    parser.add_argument("--ollama-base-url", default="http://localhost:11434")

    # Vector store
    parser.add_argument("--backend", default="memory", choices=["memory", "pgvector"])
    parser.add_argument("--backend-url", default=None, help="PostgreSQL DSN (required for pgvector)")
    parser.add_argument("--persist-dir", default=".docintel")

    # RAG mode
    parser.add_argument("--rag-mode", default="vector", choices=["vector", "graph", "hybrid"],
                        help="Retrieval mode: vector (default), graph (LightRAG), hybrid (both)")
    parser.add_argument("--lightrag-dir", default=".docintel_graph",
                        help="Working directory for LightRAG knowledge graph storage")

    # HTTP security
    parser.add_argument("--api-key", default=None,
                        help="Require X-API-Key header on all routes except /health")
    parser.add_argument("--allowed-ingest-dirs", nargs="*", default=[],
                        help="Restrict /ingest to these directory paths (empty = allow all)")
    parser.add_argument("--rate-limit-rpm", type=int, default=0,
                        help="Per-IP rate limit (requests/min, 0=off)")

    # Logging
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-json", action="store_true", default=True)
    args = parser.parse_args()

    configure_logging(level=args.log_level, json_format=args.log_json)

    config = Config(
        provider=args.provider,
        embedding_provider=args.embedding_provider,
        gemini_api_key=args.gemini_api_key,
        openai_api_key=args.openai_api_key,
        anthropic_api_key=args.anthropic_api_key,
        ollama_base_url=args.ollama_base_url,
        vector_store=args.backend,
        db_url=args.backend_url,
        persist_dir=args.persist_dir,
        rag_mode=args.rag_mode,
        lightrag_dir=args.lightrag_dir,
        api_key=args.api_key,
        allowed_ingest_dirs=args.allowed_ingest_dirs or [],
        rate_limit_rpm=args.rate_limit_rpm,
    )

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is required. Install with: pip install 'docintel[server]'"
        ) from exc

    app = create_app(config)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower())


if __name__ == "__main__":
    main()
