from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from docintel._config import Config
from docintel.server import db as _db
from docintel.server.auth_routes import router as auth_router
from docintel.server.middleware import CorrelationIdMiddleware, RateLimitMiddleware
from docintel.server.org_routes import router as org_router
from docintel.server.pipeline_registry import PipelineRegistry
from docintel.server.routes import router as doc_router
from docintel.server.superadmin_routes import router as superadmin_router


def create_app(config: Config, secret_key: str,
               cors_origins: list[str] | None = None) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        registry = getattr(app.state, "pipeline_registry", None)
        if registry:
            registry.shutdown()
        _db.close_pool()

    app = FastAPI(
        title="DocIntel Platform",
        version="1.0.0",
        description="Multi-tenant document intelligence platform — ingest, search, and query.",
        lifespan=lifespan,
    )

    # CORS — allow the web frontend to talk to the API
    origins = cors_origins or ["http://localhost:3000", "http://127.0.0.1:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if config.rate_limit_rpm > 0:
        app.add_middleware(RateLimitMiddleware, rpm=config.rate_limit_rpm)
    app.add_middleware(CorrelationIdMiddleware)

    # Initialise DB pool + run migrations (requires db_url)
    if config.db_url:
        _db.init_pool(config.db_url, config.pg_pool_min, config.pg_pool_max)

    # Per-org pipeline registry
    app.state.pipeline_registry = PipelineRegistry(config)
    app.state.secret_key        = secret_key
    app.state.config            = config

    app.include_router(auth_router)
    app.include_router(doc_router)
    app.include_router(org_router)
    app.include_router(superadmin_router)

    return app
