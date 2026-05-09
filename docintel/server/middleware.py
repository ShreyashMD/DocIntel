from __future__ import annotations
import collections
import hmac
import threading
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from docintel.logging import set_correlation_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        set_correlation_id(correlation_id)
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        response.headers["X-Correlation-Id"] = correlation_id
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        return response


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """`X-API-Key` authentication. /health is exempt so load-balancers can probe freely."""

    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key.encode()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        provided = request.headers.get("X-API-Key", "").encode()
        if not hmac.compare_digest(provided, self._api_key):
            return Response(
                content='{"detail":"Invalid or missing API key"}',
                status_code=401,
                media_type="application/json",
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window per-IP rate limiter. /health is exempt."""

    def __init__(self, app, rpm: int) -> None:
        super().__init__(app)
        self._rpm = rpm
        self._windows: dict[str, collections.deque] = {}
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._rpm <= 0 or request.url.path == "/health":
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            dq = self._windows.setdefault(ip, collections.deque())
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self._rpm:
                return Response(
                    content='{"detail":"Rate limit exceeded. Try again in 60 seconds."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"},
                )
            dq.append(now)
        return await call_next(request)
