"""
Eminence HealthOS — Rate Limiter
Token-bucket rate limiting per tenant and per-IP to prevent abuse.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

import structlog

logger = structlog.get_logger()


@dataclass
class TokenBucket:
    """Token-bucket rate limiter for a single key."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()

    def consume(self, count: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= count:
                self.tokens -= count
                return True
            return False

    @property
    def retry_after(self) -> float:
        """Seconds until a token becomes available."""
        if self.tokens >= 1:
            return 0.0
        return (1.0 - self.tokens) / self.refill_rate


# Default rate limit tiers
RATE_LIMITS = {
    "default": {"capacity": 100, "refill_rate": 10.0},  # 100 burst, 10/sec sustained
    "admin": {"capacity": 200, "refill_rate": 20.0},     # Admin gets higher limits
    "auth": {"capacity": 10, "refill_rate": 1.0},        # Auth endpoints: 10 burst, 1/sec
    "export": {"capacity": 5, "refill_rate": 0.1},       # Export: 5 burst, 1 per 10 sec
}

# Paths that get special rate limit tiers
PATH_TIERS: dict[str, str] = {
    "/api/v1/auth/": "auth",
    "/api/v1/login": "auth",
    "/api/v1/register": "auth",
    "/api/v1/analytics/executive/": "export",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-tenant and per-IP rate limiting."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = Lock()

    def _get_bucket(self, key: str, tier: str) -> TokenBucket:
        with self._lock:
            if key not in self._buckets:
                config = RATE_LIMITS.get(tier, RATE_LIMITS["default"])
                self._buckets[key] = TokenBucket(**config)
            return self._buckets[key]

    def _get_tier(self, path: str) -> str:
        for prefix, tier in PATH_TIERS.items():
            if path.startswith(prefix):
                return tier
        return "default"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip health checks
        if request.url.path in ("/health", "/health/ready", "/metrics"):
            return await call_next(request)

        # Identify the client
        tenant_id = request.headers.get("X-Tenant-ID", "anonymous")
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"{tenant_id}:{client_ip}"

        tier = self._get_tier(request.url.path)
        bucket = self._get_bucket(rate_key, tier)

        if not bucket.consume():
            retry_after = int(bucket.retry_after) + 1
            logger.warning(
                "rate_limit.exceeded",
                tenant_id=tenant_id,
                client_ip=client_ip,
                path=request.url.path,
                tier=tier,
                retry_after=retry_after,
            )
            return Response(
                content='{"detail": "Rate limit exceeded. Try again later."}',
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(bucket.capacity),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        return response
