"""
Eminence HealthOS — FastAPI Application Entry Point
The AI Operating System for Digital Healthcare Platforms.
"""

from __future__ import annotations

import importlib
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from healthos_platform.api.middleware.audit import AuditMiddleware
from healthos_platform.api.routes import (
    agents,
    alerts,
    auth,
    billing,
    clinical,
    clinical_assessment,
    dashboard,
    devices,
    ehr_sync,
    enterprise_auth,
    fhir,
    hospitals,
    knowledge_graph,
    messaging,
    ml,
    patient_portal,
    patients,
    profile,
    providers,
    rag,
    vitals,
)
from healthos_platform.config import get_settings
from healthos_platform.database import close_db, get_db_context, init_db

logger = structlog.get_logger()


async def _seed_if_empty() -> None:
    """Seed default data when the database is freshly created."""
    from sqlalchemy import select, func
    from healthos_platform.models import Organization, Patient, User
    from healthos_platform.security.auth import hash_password

    async with get_db_context() as db:
        result = await db.execute(select(func.count()).select_from(User))
        count = result.scalar()
        if count and count > 0:
            return

        logger.info("healthos.seeding_database")

        org = Organization(
            name="Eminence Health Demo",
            slug="eminence-demo",
            tier="enterprise",
            hipaa_baa_signed=True,
            settings={
                "features": ["rpm", "telehealth", "analytics"],
                "max_patients": 10000,
                "ai_enabled": True,
            },
        )
        db.add(org)
        await db.flush()

        users = [
            User(
                org_id=org.id,
                email="admin@eminence.health",
                hashed_password=hash_password("admin123"),
                role="admin",
                full_name="System Administrator",
            ),
            User(
                org_id=org.id,
                email="dr.smith@eminence.health",
                hashed_password=hash_password("doctor123"),
                role="clinician",
                full_name="Dr. Sarah Smith",
                profile={"specialty": "cardiology", "npi": "1234567890"},
            ),
        ]
        for u in users:
            db.add(u)
        await db.flush()

        patients = [
            Patient(
                org_id=org.id,
                mrn="MRN001",
                demographics={"name": "John Williams", "dob": "1955-03-15", "gender": "male"},
                conditions=[{"code": "I10", "display": "Essential hypertension", "onset": "2018-06-01"}],
                medications=[{"name": "Lisinopril", "dose": "20mg", "frequency": "daily"}],
                risk_level="high",
                care_team=[{"user_id": str(users[1].id), "role": "primary_physician"}],
            ),
        ]
        for p in patients:
            db.add(p)

        logger.info("healthos.seed_complete", users=len(users), patients=len(patients))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info(
        "healthos.startup",
        env=settings.environment,
        debug=settings.debug,
    )

    # Import models so Base.metadata knows about all tables
    import healthos_platform.models  # noqa: F401
    import shared.models  # noqa: F401

    # Create tables if they don't exist yet (retry for DB readiness race)
    import asyncio
    from healthos_platform.config.database import init_db as init_shared_db

    for attempt in range(1, 4):
        try:
            await init_db()
            await init_shared_db()
            logger.info("healthos.db_initialized")
            break
        except Exception:
            if attempt == 3:
                logger.exception("healthos.db_init_failed_after_retries")
                raise
            logger.warning("healthos.db_init_retry", attempt=attempt)
            await asyncio.sleep(2 * attempt)

    # Seed default data if the users table is empty
    try:
        await _seed_if_empty()
    except Exception:
        logger.exception("healthos.seed_failed")

    # Register all agents on startup
    try:
        _register_agents()
    except Exception:
        logger.exception("healthos.agent_registration_failed")

    # Initialize optional services (non-blocking)
    try:
        from healthos_platform.services.cache import get_redis
        await get_redis()
        logger.info("healthos.redis_connected")
    except Exception:
        logger.warning("healthos.redis_unavailable")

    try:
        from healthos_platform.services.vector_store import vector_store
        await vector_store.ensure_collections()
        logger.info("healthos.qdrant_connected")
    except Exception:
        logger.warning("healthos.qdrant_unavailable")

    try:
        from healthos_platform.services.knowledge_graph import get_driver
        await get_driver()
        logger.info("healthos.neo4j_connected")
    except Exception:
        logger.warning("healthos.neo4j_unavailable")

    yield

    # Cleanup
    await close_db()

    try:
        from healthos_platform.services.kafka import close_producer
        await close_producer()
    except Exception:
        pass

    try:
        from healthos_platform.services.cache import close_redis
        await close_redis()
    except Exception:
        pass

    try:
        from healthos_platform.services.vector_store import close_qdrant
        await close_qdrant()
    except Exception:
        pass

    try:
        from healthos_platform.services.knowledge_graph import close_driver
        await close_driver()
    except Exception:
        pass

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

    # Register research & genomics agents
    try:
        from modules.research_genomics.agents import register_research_genomics_agents
        register_research_genomics_agents()
        logger.info("agents.research_genomics.registered")
    except ImportError:
        logger.warning("agents.research_genomics.not_available")

    # Register clinical decision support agents
    try:
        from clinical_decision_support.orchestrator.agents.registration import register_clinical_agents
        register_clinical_agents()
        logger.info("agents.clinical_decision_support.registered")
    except ImportError:
        logger.warning("agents.clinical_decision_support.not_available")

    # Register remaining module agents dynamically
    _optional_agent_modules = [
        ("modules.analytics.agents", "register_analytics_agents"),
        ("modules.ambient_ai.agents", "register_ambient_ai_agents"),
        ("modules.compliance.agents", "register_compliance_agents"),
        ("modules.digital_twin.agents", "register_digital_twin_agents"),
        ("modules.imaging.agents", "register_imaging_agents"),
        ("modules.labs.agents", "register_labs_agents"),
        ("modules.mental_health.agents", "register_mental_health_agents"),
        ("modules.operations.agents", "register_operations_agents"),
        ("modules.patient_engagement.agents", "register_patient_engagement_agents"),
        ("modules.pharmacy.agents", "register_pharmacy_agents"),
        ("modules.rcm.agents", "register_rcm_agents"),
    ]
    for module_path, func_name in _optional_agent_modules:
        try:
            mod = importlib.import_module(module_path)
            getattr(mod, func_name)()
            logger.info(f"agents.{module_path.split('.')[1]}.registered")
        except (ImportError, AttributeError):
            logger.warning(f"agents.{module_path.split('.')[1]}.not_available")


_metrics_initialized = False


def _ensure_prometheus_metrics(registry):  # noqa: ANN001
    """Register custom HealthOS Prometheus metrics (idempotent)."""
    global _metrics_initialized  # noqa: PLW0603
    if _metrics_initialized:
        return
    _metrics_initialized = True

    from prometheus_client import Counter, Gauge, Histogram

    # Platform health
    Gauge("healthos_up", "HealthOS API status").set(1)

    # HTTP metrics
    Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    Gauge("http_connections_active", "Active HTTP connections")

    # Agent pipeline metrics
    Counter(
        "healthos_pipeline_executions_total",
        "Total pipeline executions",
        ["pipeline_name", "status"],
    )
    Histogram(
        "healthos_pipeline_duration_ms",
        "Pipeline execution duration in milliseconds",
        ["pipeline_name"],
    )
    Counter(
        "healthos_agent_executions_total",
        "Total agent executions",
        ["agent_name", "tier", "status"],
    )
    Histogram(
        "healthos_agent_duration_ms",
        "Agent execution duration in milliseconds",
        ["agent_name"],
    )
    Gauge("healthos_agent_confidence", "Agent confidence score", ["agent_name"])
    Counter("healthos_hitl_reviews_total", "Total HITL reviews", ["reason"])

    # RPM & patient metrics
    Counter(
        "healthos_vitals_ingested_total",
        "Total vitals ingested",
        ["vital_type"],
    )
    Counter(
        "healthos_anomalies_detected_total",
        "Total anomalies detected",
        ["severity"],
    )
    Gauge("healthos_alerts_open", "Currently open alerts", ["priority"])
    Gauge("healthos_active_patients", "Active monitored patients")


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
    app.include_router(dashboard.router, prefix=api_prefix)
    app.include_router(patients.router, prefix=api_prefix)
    app.include_router(vitals.router, prefix=api_prefix)
    app.include_router(alerts.router, prefix=api_prefix)
    app.include_router(agents.router, prefix=api_prefix)
    app.include_router(fhir.router, prefix=api_prefix)
    app.include_router(ehr_sync.router, prefix=api_prefix)
    app.include_router(patient_portal.router, prefix=api_prefix)
    app.include_router(profile.router, prefix=api_prefix)
    app.include_router(clinical_assessment.router, prefix=api_prefix)
    app.include_router(rag.router, prefix=api_prefix)
    app.include_router(knowledge_graph.router, prefix=api_prefix)
    app.include_router(ml.router, prefix=api_prefix)

    # Phase 1: RBAC — Hospital, Department, Provider/Nurse/OfficeAdmin profiles
    app.include_router(hospitals.router, prefix=api_prefix)
    app.include_router(providers.router, prefix=api_prefix)

    # Phase 2: EHR Clinical — Diagnosis, Prescription, Allergy, History, Labs
    app.include_router(clinical.router, prefix=api_prefix)

    # Phase 3: IoT Device API — Device auth, vitals ingestion, management
    app.include_router(devices.router, prefix=api_prefix)

    # Phase 4: Messaging & Notifications
    app.include_router(messaging.router, prefix=api_prefix)

    # Phase 5: Billing & Insurance
    app.include_router(billing.router, prefix=api_prefix)

    # Phase 6: Enterprise Auth — MFA, email verification, sessions
    app.include_router(enterprise_auth.router, prefix=api_prefix)

    # MCP Bridge routes
    try:
        from healthos_platform.interop.mcp_bridge.routes import router as mcp_bridge_router
        app.include_router(mcp_bridge_router, prefix=api_prefix)
        logger.info("routes.mcp_bridge.registered")
    except Exception as exc:
        logger.warning(f"routes.mcp_bridge.not_available: {exc}")

    # Serve uploaded files (avatars)
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    uploads_dir = Path("/app/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    # Module routes
    try:
        from modules.telehealth.routes import router as telehealth_router
        app.include_router(telehealth_router, prefix=api_prefix)
        logger.info("routes.telehealth.registered")
    except ImportError:
        logger.warning("routes.telehealth.not_available")

    try:
        from modules.research_genomics.routes import router as research_genomics_router
        app.include_router(research_genomics_router, prefix=api_prefix)
        logger.info("routes.research_genomics.registered")
    except ImportError:
        logger.warning("routes.research_genomics.not_available")

    # Register RPM module routes (different path structure)
    try:
        from modules.rpm.api.routes import router as rpm_router
        app.include_router(rpm_router, prefix=api_prefix)
        logger.info("routes.rpm.registered")
    except ImportError:
        logger.warning("routes.rpm.not_available")

    # Register remaining module routes dynamically
    _optional_route_modules = [
        "modules.analytics.routes",
        "modules.ambient_ai.routes",
        "modules.compliance.routes",
        "modules.digital_twin.routes",
        "modules.imaging.routes",
        "modules.labs.routes",
        "modules.marketplace.routes",
        "modules.mental_health.routes",
        "modules.ms_risk_screening.routes",
        "modules.operations.routes",
        "modules.patient_engagement.routes",
        "modules.pharmacy.routes",
        "modules.rcm.routes",
    ]
    for route_module in _optional_route_modules:
        try:
            mod = importlib.import_module(route_module)
            app.include_router(mod.router, prefix=api_prefix)
            logger.info(f"routes.{route_module.split('.')[1]}.registered")
        except Exception as exc:
            logger.warning(f"routes.{route_module.split('.')[1]}.not_available: {exc}")

    # Metrics endpoint (Prometheus scrape target)
    @app.get("/metrics")
    async def metrics():
        from fastapi.responses import PlainTextResponse
        from prometheus_client import generate_latest, REGISTRY

        # Ensure our custom metrics are registered (idempotent)
        _ensure_prometheus_metrics(REGISTRY)

        output = generate_latest(REGISTRY)
        return PlainTextResponse(
            output.decode("utf-8"),
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
