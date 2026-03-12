"""
Integration test fixtures — builds on shared conftest with auth helpers.
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from healthos_platform.config.settings import Settings, get_settings
from healthos_platform.database import Base, get_db
from healthos_platform.models import Organization, Patient, User
from healthos_platform.security.auth import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Override settings for integration tests
# ---------------------------------------------------------------------------

_test_settings = Settings(
    environment="test",
    database_url="sqlite+aiosqlite:///:memory:",
    database_sync_url="sqlite:///:memory:",
    jwt_secret_key="integration-test-secret",
    jwt_algorithm="HS256",
    jwt_access_token_expire_minutes=60,
    default_tenant_id="test-tenant",
    debug=False,
)


def _override_settings() -> Settings:
    return _test_settings


# ---------------------------------------------------------------------------
# Database engine + session (per-session scope so tables persist across tests)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def _engine():
    engine = create_async_engine(_test_settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Seed data helpers
# ---------------------------------------------------------------------------

_org_id = uuid.uuid4()
_admin_id = uuid.uuid4()
_clinician_id = uuid.uuid4()
_nurse_id = uuid.uuid4()
_patient_user_id = uuid.uuid4()


@pytest_asyncio.fixture
async def seed_org(db_session: AsyncSession) -> Organization:
    org = Organization(
        id=_org_id,
        name="Test Hospital",
        slug="test-hospital",
        tier="enterprise",
        hipaa_baa_signed=True,
        settings={"features": ["rpm", "telehealth"]},
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def seed_users(db_session: AsyncSession, seed_org: Organization) -> dict[str, User]:
    users = {
        "admin": User(
            id=_admin_id,
            org_id=seed_org.id,
            email="admin@test.health",
            hashed_password=hash_password("admin123"),
            role="admin",
            full_name="Test Admin",
        ),
        "clinician": User(
            id=_clinician_id,
            org_id=seed_org.id,
            email="dr.test@test.health",
            hashed_password=hash_password("doctor123"),
            role="clinician",
            full_name="Dr. Test",
        ),
        "nurse": User(
            id=_nurse_id,
            org_id=seed_org.id,
            email="nurse@test.health",
            hashed_password=hash_password("nurse123"),
            role="nurse",
            full_name="Nurse Test",
        ),
    }
    for u in users.values():
        db_session.add(u)
    await db_session.flush()
    return users


@pytest_asyncio.fixture
async def seed_patient(db_session: AsyncSession, seed_org: Organization) -> Patient:
    patient = Patient(
        org_id=seed_org.id,
        mrn="TEST-001",
        demographics={"name": "Jane Doe", "dob": "1980-01-15", "gender": "female"},
        conditions=[{"code": "E11", "display": "Type 2 diabetes"}],
        medications=[{"name": "Metformin", "dose": "500mg", "frequency": "twice daily"}],
        risk_level="moderate",
    )
    db_session.add(patient)
    await db_session.flush()
    await db_session.refresh(patient)
    return patient


# ---------------------------------------------------------------------------
# Auth tokens
# ---------------------------------------------------------------------------


def _make_token(user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> str:
    # Temporarily override get_settings for token creation
    import healthos_platform.config.settings as settings_mod
    original = settings_mod.get_settings
    settings_mod.get_settings = _override_settings
    settings_mod.get_settings.cache_clear = lambda: None  # type: ignore[attr-defined]
    try:
        # Clear lru_cache so our overridden settings take effect
        import healthos_platform.config as config_mod
        if hasattr(config_mod, "get_settings"):
            try:
                config_mod.get_settings.cache_clear()
            except Exception:
                pass
        return create_access_token(user_id, org_id, role)
    finally:
        settings_mod.get_settings = original


@pytest_asyncio.fixture
def admin_token(seed_users) -> str:
    return _make_token(_admin_id, _org_id, "admin")


@pytest_asyncio.fixture
def clinician_token(seed_users) -> str:
    return _make_token(_clinician_id, _org_id, "clinician")


@pytest_asyncio.fixture
def nurse_token(seed_users) -> str:
    return _make_token(_nurse_id, _org_id, "nurse")


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the real FastAPI app with DB overridden."""
    from healthos_platform.api.main import create_app
    import healthos_platform.config.settings as settings_mod

    # Patch settings for the app
    original_get_settings = settings_mod.get_settings
    settings_mod.get_settings = _override_settings
    try:
        settings_mod.get_settings.cache_clear()
    except Exception:
        pass

    import healthos_platform.config as config_mod
    original_config_get = getattr(config_mod, "get_settings", None)
    config_mod.get_settings = _override_settings

    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    # Also override the database.get_db import used in routes
    from healthos_platform import database as db_mod
    app.dependency_overrides[db_mod.get_db] = _override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    settings_mod.get_settings = original_get_settings
    if original_config_get:
        config_mod.get_settings = original_config_get


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
