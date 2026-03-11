"""Health check endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request

logger = logging.getLogger("healthos.routes.health")
router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Basic health check — always returns 200 if the API is running."""
    return {
        "status": "healthy",
        "service": "eminence-healthos",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(request: Request):
    """Readiness probe — checks database and Redis connectivity."""
    checks = {}

    # Database
    try:
        from healthos_platform.config.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis:
            await redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not configured"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values() if v != "not configured")
    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
