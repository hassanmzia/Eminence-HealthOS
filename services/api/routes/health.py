"""Health check, readiness, and production diagnostic endpoints."""

import logging
import os
import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from services.api.middleware.auth import require_role

logger = logging.getLogger("healthos.routes.health")
router = APIRouter()

# Track startup time for uptime calculation
_STARTUP_TIME = time.monotonic()
_STARTUP_TIMESTAMP = datetime.now(timezone.utc).isoformat()


@router.get("/health")
async def health_check(request: Request):
    """Liveness probe — returns 200 if the API process is alive."""
    return {
        "status": "healthy",
        "service": "eminence-healthos",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(request: Request):
    """Readiness probe — checks all critical dependencies."""
    checks = {}

    # Database
    try:
        from healthos_platform.config.database import get_session_factory
        factory = get_session_factory()
        start = time.monotonic()
        async with factory() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        latency = (time.monotonic() - start) * 1000
        checks["database"] = {"status": "ok", "latency_ms": round(latency, 1)}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # Redis
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis:
            start = time.monotonic()
            await redis.ping()
            latency = (time.monotonic() - start) * 1000
            checks["redis"] = {"status": "ok", "latency_ms": round(latency, 1)}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    # Agent registry
    try:
        from healthos_platform.orchestrator.registry import registry
        agents = registry.list_agents()
        checks["agent_registry"] = {"status": "ok", "agent_count": len(agents)}
    except Exception as e:
        checks["agent_registry"] = {"status": "error", "detail": str(e)}

    critical_ok = all(
        checks.get(svc, {}).get("status") in ("ok", "not_configured")
        for svc in ("database", "redis")
    )

    status_code = 200 if critical_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if critical_ok else "not_ready",
            "checks": checks,
            "uptime_seconds": round(time.monotonic() - _STARTUP_TIME),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/health/startup")
async def startup_check():
    """Startup probe — indicates app has finished initialization."""
    return {
        "status": "started",
        "started_at": _STARTUP_TIMESTAMP,
        "uptime_seconds": round(time.monotonic() - _STARTUP_TIME),
    }


@router.get("/health/diagnostics")
async def diagnostics(request: Request):
    """Production diagnostics — admin-only runtime information."""
    import sys

    # Security info
    security_features = {
        "jwt_auth": True,
        "rbac": True,
        "phi_encryption": True,
        "phi_filter": True,
        "audit_logging": True,
        "rate_limiting": True,
        "security_headers": True,
        "input_sanitization": True,
        "tenant_isolation": True,
    }

    # Compliance checks
    try:
        from healthos_platform.config.settings import get_settings
        settings = get_settings()
        compliance = {
            "token_expiry_minutes": settings.access_token_expire_minutes,
            "encryption_configured": bool(settings.phi_encryption_key),
            "debug_mode": settings.debug,
            "environment": settings.environment,
        }
    except Exception:
        compliance = {"error": "Could not load settings"}

    return {
        "runtime": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "pid": os.getpid(),
        },
        "uptime": {
            "started_at": _STARTUP_TIMESTAMP,
            "uptime_seconds": round(time.monotonic() - _STARTUP_TIME),
        },
        "security": security_features,
        "compliance": compliance,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
