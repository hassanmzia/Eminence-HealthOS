"""
HealthOS FastAPI Application.

Main entry point for the API server. Configures middleware, routes,
lifespan events, and error handling.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from healthos_platform.config.settings import get_settings
from healthos_platform.config.database import init_db, close_db
from services.api.middleware.tenant import TenantMiddleware
from services.api.middleware.tracing import TracingMiddleware
from services.api.routes import (
    health, patients, providers, observations, agents, alerts,
    fhir, orchestrator, dashboard, websocket,
)

logger = logging.getLogger("healthos.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    settings = get_settings()
    logger.info("Starting HealthOS %s (%s)", settings.app_version, settings.environment)

    # Initialize database
    if settings.is_development:
        await init_db()

    # Initialize observability
    try:
        from observability.core.tracer import ObservabilityManager
        app.state.observability = ObservabilityManager()
        logger.info("Observability manager initialized")
    except Exception as e:
        logger.warning("Observability init skipped: %s", e)

    # Initialize Redis
    try:
        import redis.asyncio as aioredis
        app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await app.state.redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis connection failed: %s", e)
        app.state.redis = None

    yield

    # Shutdown
    if hasattr(app.state, "redis") and app.state.redis:
        await app.state.redis.close()
    await close_db()
    logger.info("HealthOS shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Eminence HealthOS",
        description="Unified Healthcare AI Platform API",
        version=settings.app_version,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── Middleware (order matters — last added runs first) ────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware)
    app.add_middleware(TracingMiddleware)

    # ── Routes ───────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
    app.include_router(providers.router, prefix="/api/v1/providers", tags=["Providers"])
    app.include_router(observations.router, prefix="/api/v1/observations", tags=["Observations"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
    app.include_router(fhir.router, prefix="/api/v1/fhir", tags=["FHIR R4"])
    app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
    app.include_router(websocket.router, tags=["WebSocket"])

    # ── Module Routes ─────────────────────────────────────────
    from modules.telehealth.routes import router as telehealth_router
    from modules.operations.routes import router as operations_router
    from modules.analytics.routes import router as analytics_router

    app.include_router(telehealth_router, prefix="/api/v1/telehealth", tags=["Telehealth"])
    app.include_router(operations_router, prefix="/api/v1/operations", tags=["Operations"])
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])

    return app


app = create_app()
