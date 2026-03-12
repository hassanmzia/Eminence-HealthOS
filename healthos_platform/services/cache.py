"""
Eminence HealthOS — Redis Cache Layer
Provides async caching for patient context, risk scores, dashboard aggregations,
and session data. Supports TTL, namespaced keys, and batch operations.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from healthos_platform.config import get_settings

logger = structlog.get_logger()

_redis = None


async def get_redis():
    """Get or create the singleton Redis connection."""
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis

        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("redis.connected", url=settings.redis_url.split("@")[-1])
    return _redis


async def close_redis():
    """Close the Redis connection."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("redis.closed")


# ═══════════════════════════════════════════════════════════════════════════════
# Core Cache Operations
# ═══════════════════════════════════════════════════════════════════════════════


class CacheNamespace:
    """Namespaced cache keys to prevent collisions."""

    PATIENT_CONTEXT = "healthos:patient:{patient_id}:context"
    PATIENT_RISK = "healthos:patient:{patient_id}:risk"
    PATIENT_VITALS_LATEST = "healthos:patient:{patient_id}:vitals:latest"
    DASHBOARD_SUMMARY = "healthos:org:{org_id}:dashboard:summary"
    AGENT_STATE = "healthos:agent:{agent_name}:state"
    SESSION = "healthos:session:{session_id}"
    FHIR_BUNDLE = "healthos:fhir:{resource_type}:{resource_id}"
    RATE_LIMIT = "healthos:ratelimit:{client_id}:{endpoint}"


class HealthOSCache:
    """High-level cache operations for HealthOS."""

    def __init__(self, default_ttl: int | None = None):
        self._default_ttl = default_ttl

    @property
    def _ttl(self) -> int:
        if self._default_ttl is not None:
            return self._default_ttl
        settings = get_settings()
        return settings.redis_cache_ttl

    async def get(self, key: str) -> Any | None:
        """Get a cached value."""
        r = await get_redis()
        val = await r.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a cached value with optional TTL."""
        r = await get_redis()
        serialized = json.dumps(value, default=str) if not isinstance(value, str) else value
        await r.set(key, serialized, ex=ttl or self._ttl)

    async def delete(self, key: str) -> None:
        """Delete a cached key."""
        r = await get_redis()
        await r.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        r = await get_redis()
        return bool(await r.exists(key))

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple keys at once."""
        r = await get_redis()
        values = await r.mget(keys)
        result = {}
        for key, val in zip(keys, values):
            if val is not None:
                try:
                    result[key] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    result[key] = val
        return result

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        r = await get_redis()
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await r.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        return deleted

    # ── Domain-Specific Operations ────────────────────────────────────────

    async def get_patient_context(self, patient_id: str) -> dict[str, Any] | None:
        """Get cached patient context for agent pipelines."""
        key = CacheNamespace.PATIENT_CONTEXT.format(patient_id=patient_id)
        return await self.get(key)

    async def set_patient_context(self, patient_id: str, context: dict[str, Any], ttl: int = 300) -> None:
        """Cache patient context (5-minute default TTL)."""
        key = CacheNamespace.PATIENT_CONTEXT.format(patient_id=patient_id)
        await self.set(key, context, ttl=ttl)

    async def get_patient_risk(self, patient_id: str) -> dict[str, Any] | None:
        """Get cached risk score for a patient."""
        key = CacheNamespace.PATIENT_RISK.format(patient_id=patient_id)
        return await self.get(key)

    async def set_patient_risk(self, patient_id: str, risk_data: dict[str, Any], ttl: int = 600) -> None:
        """Cache patient risk score (10-minute default TTL)."""
        key = CacheNamespace.PATIENT_RISK.format(patient_id=patient_id)
        await self.set(key, risk_data, ttl=ttl)

    async def get_dashboard_summary(self, org_id: str) -> dict[str, Any] | None:
        """Get cached dashboard summary for an organization."""
        key = CacheNamespace.DASHBOARD_SUMMARY.format(org_id=org_id)
        return await self.get(key)

    async def set_dashboard_summary(self, org_id: str, summary: dict[str, Any], ttl: int = 60) -> None:
        """Cache dashboard summary (1-minute default TTL)."""
        key = CacheNamespace.DASHBOARD_SUMMARY.format(org_id=org_id)
        await self.set(key, summary, ttl=ttl)

    async def invalidate_patient(self, patient_id: str) -> int:
        """Invalidate all cached data for a patient."""
        pattern = f"healthos:patient:{patient_id}:*"
        deleted = await self.invalidate_pattern(pattern)
        logger.info("cache.patient.invalidated", patient_id=patient_id, keys_deleted=deleted)
        return deleted

    async def invalidate_org_dashboard(self, org_id: str) -> int:
        """Invalidate dashboard cache for an organization."""
        pattern = f"healthos:org:{org_id}:dashboard:*"
        return await self.invalidate_pattern(pattern)

    # ── Rate Limiting ─────────────────────────────────────────────────────

    async def check_rate_limit(self, client_id: str, endpoint: str, max_requests: int = 100, window: int = 60) -> bool:
        """Check and increment rate limit. Returns True if within limit."""
        key = CacheNamespace.RATE_LIMIT.format(client_id=client_id, endpoint=endpoint)
        r = await get_redis()

        current = await r.get(key)
        if current is None:
            await r.set(key, 1, ex=window)
            return True

        if int(current) >= max_requests:
            return False

        await r.incr(key)
        return True


# Module-level cache instance
cache = HealthOSCache()
