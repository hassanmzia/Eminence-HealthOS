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
    try:
        if settings.is_development:
            await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("Database init failed (service may be unavailable): %s", e)
        app.state.db_available = False

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

    # Security hardening middleware
    from healthos_platform.security.headers import SecurityHeadersMiddleware
    from healthos_platform.security.rate_limiter import RateLimitMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, enabled=settings.is_production)

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
    from modules.rpm.api.routes import router as rpm_router
    from modules.telehealth.routes import router as telehealth_router
    from modules.operations.routes import router as operations_router
    from modules.analytics.routes import router as analytics_router

    app.include_router(rpm_router, prefix="/api/v1", tags=["RPM"])
    app.include_router(telehealth_router, prefix="/api/v1", tags=["Telehealth"])
    app.include_router(operations_router, prefix="/api/v1", tags=["Operations"])
    app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])

    from modules.research_genomics.routes import router as research_genomics_router
    from modules.compliance.routes import router as compliance_router
    from modules.digital_twin.routes import router as digital_twin_router
    from modules.imaging.routes import router as imaging_router
    from modules.labs.routes import router as labs_router
    from modules.pharmacy.routes import router as pharmacy_router
    from modules.rcm.routes import router as rcm_router
    from modules.mental_health.routes import router as mental_health_router
    from modules.patient_engagement.routes import router as patient_engagement_router
    from modules.ambient_ai.routes import router as ambient_ai_router
    from modules.ms_risk_screening.routes import router as ms_risk_screening_router

    app.include_router(research_genomics_router, prefix="/api/v1", tags=["Research & Genomics"])
    app.include_router(compliance_router, prefix="/api/v1", tags=["Compliance & Governance"])
    app.include_router(digital_twin_router, prefix="/api/v1", tags=["Digital Twin"])
    app.include_router(imaging_router, prefix="/api/v1", tags=["Imaging"])
    app.include_router(labs_router, prefix="/api/v1", tags=["Labs"])
    app.include_router(pharmacy_router, prefix="/api/v1", tags=["Pharmacy"])
    app.include_router(rcm_router, prefix="/api/v1", tags=["Revenue Cycle"])
    app.include_router(mental_health_router, prefix="/api/v1", tags=["Mental Health"])
    app.include_router(patient_engagement_router, prefix="/api/v1", tags=["Patient Engagement"])
    app.include_router(ambient_ai_router, prefix="/api/v1", tags=["Ambient AI"])
    app.include_router(ms_risk_screening_router, prefix="/api/v1", tags=["MS Risk Screening"])

    from modules.marketplace.routes import router as marketplace_router
    app.include_router(marketplace_router, prefix="/api/v1", tags=["AI Marketplace"])

    from modules.ms_risk_screening.routes import router as ms_risk_router
    app.include_router(ms_risk_router, prefix="/api/v1", tags=["MS Risk Screening"])

    # ── Protocol Bridge Routes ────────────────────────────────────
    from healthos_platform.interop.mcp_bridge.routes import router as mcp_bridge_router
    from healthos_platform.interop.a2a_bridge.routes import router as a2a_bridge_router

    app.include_router(mcp_bridge_router, prefix="/api/v1", tags=["MCP Bridge"])
    app.include_router(a2a_bridge_router, prefix="/api/v1", tags=["A2A Bridge"])

    return app


app = create_app()
