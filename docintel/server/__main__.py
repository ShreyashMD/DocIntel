from __future__ import annotations
import argparse
import os
import secrets

from docintel._config import Config
from docintel.logging import configure_logging
from docintel.server.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="DocIntel Platform Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)

    # Auth
    parser.add_argument("--secret-key", default=None,
                        help="JWT + encryption secret (env: SECRET_KEY). Auto-generated if omitted — not stable across restarts.")

    # LLM provider defaults (overridden per-org via /admin/settings)
    parser.add_argument("--provider", default="gemini",
                        choices=["gemini", "openai", "anthropic", "ollama", "nvidia"])
    parser.add_argument("--embedding-provider", default=None)
    parser.add_argument("--gemini-api-key", default=None)
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--anthropic-api-key", default=None)
    parser.add_argument("--nvidia-api-key", default=None)
    parser.add_argument("--ollama-base-url", default="http://localhost:11434")

    # Storage (db-url required for auth tables)
    parser.add_argument("--backend", default="memory", choices=["memory", "pgvector"],
                        dest="vector_store")
    parser.add_argument("--db-url", default=None,
                        help="PostgreSQL DSN — REQUIRED for auth. env: DATABASE_URL")
    parser.add_argument("--persist-dir", default=".docintel")

    # RAG
    parser.add_argument("--rag-mode", default="vector",
                        choices=["vector", "graph", "hybrid"])
    parser.add_argument("--lightrag-dir", default=".docintel_graph")

    # Security
    parser.add_argument("--allowed-ingest-dirs", nargs="*", default=[])
    parser.add_argument("--rate-limit-rpm", type=int, default=0)
    parser.add_argument("--cors-origins", nargs="*", default=None,
                        help="Allowed CORS origins (default: localhost:3000)")

    # Logging
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-json", action="store_true", default=True)

    args = parser.parse_args()

    configure_logging(level=args.log_level, json_format=args.log_json)

    # Resolve secrets from env or CLI
    db_url     = args.db_url or os.environ.get("DATABASE_URL")
    secret_key = args.secret_key or os.environ.get("SECRET_KEY")
    if not secret_key:
        secret_key = secrets.token_urlsafe(32)
        import logging
        logging.getLogger(__name__).warning(
            "No --secret-key provided — generated a random one. "
            "JWT tokens will be invalidated on restart. "
            "Set SECRET_KEY env var for a stable key."
        )

    if not db_url:
        raise SystemExit(
            "ERROR: --db-url (or DATABASE_URL env var) is required. "
            "Auth tables need PostgreSQL."
        )

    # Resolve API keys from env
    gemini_key    = args.gemini_api_key    or os.environ.get("GEMINI_API_KEY")
    openai_key    = args.openai_api_key    or os.environ.get("OPENAI_API_KEY")
    anthropic_key = args.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    nvidia_key    = args.nvidia_api_key    or os.environ.get("NVIDIA_API_KEY")

    config = Config(
        provider=args.provider,
        embedding_provider=args.embedding_provider,
        gemini_api_key=gemini_key,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
        nvidia_api_key=nvidia_key,
        ollama_base_url=args.ollama_base_url,
        vector_store=args.vector_store,
        db_url=db_url,
        persist_dir=args.persist_dir,
        rag_mode=args.rag_mode,
        lightrag_dir=args.lightrag_dir,
        allowed_ingest_dirs=args.allowed_ingest_dirs or [],
        rate_limit_rpm=args.rate_limit_rpm,
    )

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is required: pip install 'docintel[server]'"
        ) from exc

    app = create_app(config, secret_key=secret_key, cors_origins=args.cors_origins)
    uvicorn.run(app, host=args.host, port=args.port,
                log_level=args.log_level.lower())


if __name__ == "__main__":
    main()
