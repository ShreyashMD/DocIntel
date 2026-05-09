from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI

from docintel._config import Config
from docintel._pipeline import Pipeline
from docintel.server.middleware import ApiKeyMiddleware, CorrelationIdMiddleware, RateLimitMiddleware
from docintel.server.routes import router


def create_app(config: Config) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        # Graceful shutdown: flush in-memory store and close any DB connection pool.
        pipeline = getattr(app.state, "pipeline", None)
        if pipeline is not None:
            store = getattr(pipeline, "_store", None)
            if store is not None:
                if hasattr(store, "close"):
                    store.close()
                elif hasattr(store, "save"):
                    store.save()

    app = FastAPI(
        title="DocIntel API",
        version="0.1.0",
        description="Industrial Document Analysis — ingest, search, and query documents via HTTP.",
        lifespan=lifespan,
    )

    # Middleware is applied in reverse-registration order for requests.
    # add_middleware order below = innermost-first, so the last added runs first.
    # Desired request order: CorrelationId → ApiKey → RateLimit → route.
    if config.rate_limit_rpm > 0:
        app.add_middleware(RateLimitMiddleware, rpm=config.rate_limit_rpm)
    if config.api_key:
        app.add_middleware(ApiKeyMiddleware, api_key=config.api_key)
    app.add_middleware(CorrelationIdMiddleware)

    app.state.pipeline = Pipeline(config)
    app.include_router(router)
    return app
