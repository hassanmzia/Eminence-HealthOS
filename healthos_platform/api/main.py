"""
Eminence HealthOS — FastAPI Application Entry Point
The AI Operating System for Digital Healthcare Platforms.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from healthos_platform.api.middleware.audit import AuditMiddleware
from healthos_platform.api.routes import agents, alerts, auth, fhir, patients, vitals
from healthos_platform.config import get_settings
from healthos_platform.database import close_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info(
        "healthos.startup",
        env=settings.environment,
        debug=settings.debug,
    )

    # Register all agents on startup
    _register_agents()

    yield

    # Cleanup
    await close_db()
    logger.info("healthos.shutdown")


def _register_agents() -> None:
    """Register all platform and module agents."""
    from healthos_platform.orchestrator.registry import registry

    # Register core platform agents (context assembly, policy rules)
    try:
        from healthos_platform.agents import register_core_agents
        register_core_agents()
        logger.info("agents.core.registered")
    except ImportError:
        logger.warning("agents.core.not_available")

    # Import RPM agents to trigger registration
    try:
        from modules.rpm.agents import register_rpm_agents
        register_rpm_agents()
        logger.info("agents.rpm.registered")
    except ImportError:
        logger.warning("agents.rpm.not_available")

    # Register telehealth agents
    try:
        from modules.telehealth.agents import register_telehealth_agents
        register_telehealth_agents()
        logger.info("agents.telehealth.registered")
    except ImportError:
        logger.warning("agents.telehealth.not_available")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Eminence HealthOS",
        description="The AI Operating System for Digital Healthcare Platforms",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)

    # API Routes
    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(patients.router, prefix=api_prefix)
    app.include_router(vitals.router, prefix=api_prefix)
    app.include_router(alerts.router, prefix=api_prefix)
    app.include_router(agents.router, prefix=api_prefix)
    app.include_router(fhir.router, prefix=api_prefix)

    # Module routes
    try:
        from modules.telehealth.routes import router as telehealth_router
        app.include_router(telehealth_router, prefix=api_prefix)
        logger.info("routes.telehealth.registered")
    except ImportError:
        logger.warning("routes.telehealth.not_available")

    # Metrics endpoint (Prometheus scrape target)
    @app.get("/metrics")
    async def metrics():
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            "# HELP healthos_up HealthOS API status\n"
            "# TYPE healthos_up gauge\n"
            "healthos_up 1\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.environment,
            "platform": "Eminence HealthOS",
        }

    @app.get("/")
    async def root():
        return {
            "name": "Eminence HealthOS",
            "version": "0.1.0",
            "description": "The AI Operating System for Digital Healthcare Platforms",
            "docs": "/docs" if settings.is_development else None,
        }

    return app


app = create_app()
