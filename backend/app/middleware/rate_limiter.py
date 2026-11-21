"""Simple in-memory rate limiter middleware.

Production: use Redis-backed rate limiting for multi-instance deployments.
"""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter — per IP + user.

    Limits:
    - Auth endpoints (login/register): 10 requests per minute per IP (brute-force protection)
    - AI generation: 5 requests per minute per user
    - General API: 120 requests per minute per user
    """

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _get_limit(self, path: str) -> tuple[int, int]:
        """Return (max_requests, window_seconds) for a path."""
        if "/auth/login" in path or "/auth/register" in path:
            return 10, 60
        if "/generate-all" in path:
            return 5, 60
        if "/policy/upload" in path:
            return 10, 60
        return 120, 60

    async def dispatch(self, request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Skip rate limiting for health checks and docs
        if path in ("/", "/api/docs", "/api/redoc", "/api/openapi.json", "/api/v1/health"):
            return await call_next(request)

        max_requests, window = self._get_limit(path)

        # Use Authorization header to distinguish users (for per-user limits)
        auth = request.headers.get("authorization", "")
        # For auth endpoints, key by IP only (no token yet)
        if "/auth/" in path:
            key = f"ip:{client_ip}:auth"
        else:
            # For authenticated endpoints, use token hash to scope per-user
            user_key = auth[-16:] if auth else "anon"
            category = "generate" if "/generate-all" in path else "general"
            key = f"{client_ip}:{user_key}:{category}"

        now = time.time()

        # Clean old entries
        self._buckets[key] = [t for t in self._buckets[key] if now - t < window]

        if len(self._buckets[key]) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT",
                        "message": f"Too many requests. Limit: {max_requests}/{window}s",
                        "details": [],
                    },
                },
            )

        self._buckets[key].append(now)
        return await call_next(request)
