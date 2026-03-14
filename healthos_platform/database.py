"""
Eminence HealthOS — Database Engine & Session Management
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = structlog.get_logger()

from healthos_platform.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all HealthOS models."""

    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            echo=settings.debug,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


_MISSING_COLUMN_MIGRATIONS = [
    'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "avatar_url" VARCHAR(500)',
    'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "phone" VARCHAR(50)',
    'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "mfa_enabled" BOOLEAN DEFAULT false',
    'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "mfa_secret" VARCHAR(255)',
    'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMPTZ DEFAULT now()',
]


async def init_db() -> None:
    """Create all tables if they don't exist, and add missing columns."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _MISSING_COLUMN_MIGRATIONS:
            try:
                await conn.execute(text(stmt))
            except Exception as exc:
                logger.warning("healthos.migration_stmt_skipped", stmt=stmt, error=str(exc))


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
