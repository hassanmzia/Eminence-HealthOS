"""
Eminence HealthOS — Analytics Cache Service

Redis-based caching layer for analytics results.  Stores pre-computed
analytics outputs (executive summaries, risk distributions, etc.) so
dashboard reads are served from cache rather than re-running agents.

Uses ``redis.asyncio`` with JSON serialization.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from healthos_platform.config import get_settings

logger = logging.getLogger(__name__)

# ── Key Namespace ─────────────────────────────────────────────────────────────

_PREFIX = "healthos:analytics"


def _key(parts: str | list[str]) -> str:
    """Build a namespaced Redis key."""
    if isinstance(parts, str):
        return f"{_PREFIX}:{parts}"
    return f"{_PREFIX}:{':'.join(parts)}"


# ── Redis Connection ──────────────────────────────────────────────────────────

_pool: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    """Return a shared ``redis.asyncio`` connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = aioredis.from_url(
            settings.redis_cache_url,
            decode_responses=True,
            max_connections=20,
        )
    return _pool


async def close_redis() -> None:
    """Shut down the Redis connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# ── Generic Cache Primitives ─────────────────────────────────────────────────


async def get_cached(key: str) -> Any | None:
    """Retrieve a JSON-serialized value from cache.

    Returns ``None`` on cache miss or deserialization failure.
    """
    try:
        r = await _get_redis()
        raw = await r.get(_key(key))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("analytics.cache.get_failed", extra={"key": key, "error": str(exc)})
        return None


async def set_cached(key: str, value: Any, ttl: int = 3600) -> None:
    """Store a JSON-serializable value in cache with a TTL (seconds)."""
    try:
        r = await _get_redis()
        await r.set(_key(key), json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        logger.warning("analytics.cache.set_failed", extra={"key": key, "error": str(exc)})


# ── Executive Summary ─────────────────────────────────────────────────────────


async def cache_executive_summary(org_id: str, data: dict[str, Any], ttl: int = 3600) -> None:
    """Cache an executive summary for an organization."""
    await set_cached(f"executive_summary:{org_id}", data, ttl=ttl)


async def get_cached_executive_summary(org_id: str) -> dict[str, Any] | None:
    """Retrieve a cached executive summary."""
    return await get_cached(f"executive_summary:{org_id}")


# ── Risk Distribution ────────────────────────────────────────────────────────


async def cache_risk_distribution(org_id: str, data: dict[str, Any], ttl: int = 1800) -> None:
    """Cache a risk-score distribution for an organization."""
    await set_cached(f"risk_distribution:{org_id}", data, ttl=ttl)


async def get_cached_risk_distribution(org_id: str) -> dict[str, Any] | None:
    """Retrieve a cached risk distribution."""
    return await get_cached(f"risk_distribution:{org_id}")


# ── Cache Invalidation ───────────────────────────────────────────────────────


async def invalidate_org_cache(org_id: str) -> int:
    """Delete all analytics cache entries for a given organization.

    Returns the number of keys deleted.
    """
    try:
        r = await _get_redis()
        pattern = _key(f"*:{org_id}")
        cursor: int | bytes = 0
        deleted = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                deleted += await r.delete(*keys)
            if cursor == 0:
                break
        logger.info(
            "analytics.cache.invalidated",
            extra={"org_id": org_id, "keys_deleted": deleted},
        )
        return deleted
    except Exception as exc:
        logger.warning(
            "analytics.cache.invalidate_failed",
            extra={"org_id": org_id, "error": str(exc)},
        )
        return 0
