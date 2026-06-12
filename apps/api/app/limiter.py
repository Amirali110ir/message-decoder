"""Simple in-memory rate limiter implemented as Starlette middleware.

Runs only when AI_PROVIDER != "mock" (i.e. production). In dev / CI the
middleware is a no-op so tests are never affected.

Limits (per remote IP):
  POST /auth/request-otp  → 5 / minute   (SMS abuse prevention)
  POST /decode/free       → 20 / minute  (scraping prevention)
  POST /decode/paid       → 30 / minute  (credit-burn prevention)
"""

import os
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_LIMITS: dict[str, tuple[int, int]] = {
    "/auth/request-otp": (5, 60),
    "/decode/free": (20, 60),
    "/decode/paid": (30, 60),
}


def _is_production() -> bool:
    return os.getenv("AI_PROVIDER", "mock") != "mock"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        # (ip, path) -> list of request timestamps
        self._buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if not _is_production() or path not in _LIMITS or request.method != "POST":
            return await call_next(request)

        limit, window = _LIMITS[path]
        ip = request.client.host if request.client else "unknown"
        key = (ip, path)
        now = time.monotonic()

        self._buckets[key] = [t for t in self._buckets[key] if now - t < window]

        if len(self._buckets[key]) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": f"نرخ درخواست بیش از حد مجاز است. لطفاً کمی صبر کنید."},
            )

        self._buckets[key].append(now)
        return await call_next(request)
