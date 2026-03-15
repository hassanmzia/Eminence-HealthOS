"""
Eminence HealthOS — Analytics Scheduler

Periodic analytics pipeline powered by APScheduler (``AsyncIOScheduler``).

Scheduled jobs:
    run_population_health_refresh — every 6 hours
    run_risk_score_update         — every 4 hours
    run_cohort_refresh            — every 12 hours
    run_daily_metrics_snapshot    — daily at 02:00 UTC
    run_executive_digest          — daily at 06:00 UTC

Start from the CLI:
    python -m modules.analytics.scheduler
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from healthos_platform.agents.types import AgentInput, AgentOutput, AgentStatus
from healthos_platform.database import get_db_context
from healthos_platform.models import Organization
from healthos_platform.orchestrator.registry import registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("healthos.analytics.scheduler")


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_active_org_ids() -> list[uuid.UUID]:
    """Return the IDs of all organizations in the database."""
    async with get_db_context() as session:
        result = await session.execute(select(Organization.id))
        return list(result.scalars().all())


def _build_input(
    org_id: uuid.UUID,
    *,
    action: str = "overview",
    trigger: str = "scheduler",
) -> AgentInput:
    return AgentInput(
        org_id=org_id,
        trigger=trigger,
        context={"action": action},
    )


async def _run_agent_for_all_orgs(
    agent_name: str,
    *,
    action: str = "overview",
    trigger: str = "scheduler",
) -> None:
    """Invoke *agent_name* once per active organization, logging errors."""
    agent = registry.get(agent_name)
    if agent is None:
        logger.error("scheduler.agent_not_registered", extra={"agent": agent_name})
        return

    try:
        org_ids = await _get_active_org_ids()
    except Exception as exc:
        logger.error(
            "scheduler.org_query_failed",
            extra={"agent": agent_name, "error": str(exc)},
        )
        return

    logger.info(
        "scheduler.job.start",
        extra={"agent": agent_name, "org_count": len(org_ids)},
    )

    for org_id in org_ids:
        try:
            agent_input = _build_input(org_id, action=action, trigger=trigger)
            output: AgentOutput = await agent.run(agent_input)
            logger.info(
                "scheduler.job.org_complete",
                extra={
                    "agent": agent_name,
                    "org_id": str(org_id),
                    "status": output.status.value,
                    "confidence": output.confidence,
                    "duration_ms": output.duration_ms,
                },
            )
        except Exception as exc:
            logger.error(
                "scheduler.job.org_error",
                extra={
                    "agent": agent_name,
                    "org_id": str(org_id),
                    "error": str(exc),
                },
            )

    logger.info("scheduler.job.end", extra={"agent": agent_name})


# ── Scheduled Jobs ────────────────────────────────────────────────────────────


async def run_population_health_refresh() -> None:
    """Every 6 hours — run population health analysis for all active orgs."""
    await _run_agent_for_all_orgs(
        "population_health",
        action="overview",
        trigger="scheduled_population_health_refresh",
    )


async def run_risk_score_update() -> None:
    """Every 4 hours — refresh readmission risk scores for all active orgs."""
    await _run_agent_for_all_orgs(
        "readmission_risk",
        action="score",
        trigger="scheduled_risk_score_update",
    )


async def run_cohort_refresh() -> None:
    """Every 12 hours — update cohort patient counts and risk distributions."""
    await _run_agent_for_all_orgs(
        "cohort_segmentation",
        action="segment",
        trigger="scheduled_cohort_refresh",
    )


async def run_daily_metrics_snapshot() -> None:
    """Daily at 02:00 UTC — snapshot population metrics for all active orgs."""
    await _run_agent_for_all_orgs(
        "population_health",
        action="quality_metrics",
        trigger="scheduled_daily_metrics_snapshot",
    )


async def run_executive_digest() -> None:
    """Daily at 06:00 UTC — generate executive summary for all active orgs."""
    from modules.analytics.services.cache_service import cache_executive_summary

    agent = registry.get("executive_insight")
    if agent is None:
        logger.error("scheduler.agent_not_registered", extra={"agent": "executive_insight"})
        return

    try:
        org_ids = await _get_active_org_ids()
    except Exception as exc:
        logger.error(
            "scheduler.org_query_failed",
            extra={"agent": "executive_insight", "error": str(exc)},
        )
        return

    logger.info(
        "scheduler.job.start",
        extra={"agent": "executive_insight", "org_count": len(org_ids)},
    )

    for org_id in org_ids:
        try:
            agent_input = _build_input(
                org_id,
                action="executive_summary",
                trigger="scheduled_executive_digest",
            )
            output: AgentOutput = await agent.run(agent_input)

            # Cache the result so dashboards can serve it instantly
            if output.status == AgentStatus.COMPLETED:
                await cache_executive_summary(
                    str(org_id),
                    output.result,
                    ttl=7200,  # 2 hours — next digest will overwrite
                )

            logger.info(
                "scheduler.job.org_complete",
                extra={
                    "agent": "executive_insight",
                    "org_id": str(org_id),
                    "status": output.status.value,
                    "duration_ms": output.duration_ms,
                },
            )
        except Exception as exc:
            logger.error(
                "scheduler.job.org_error",
                extra={
                    "agent": "executive_insight",
                    "org_id": str(org_id),
                    "error": str(exc),
                },
            )

    logger.info("scheduler.job.end", extra={"agent": "executive_insight"})


# ── Scheduler Setup ──────────────────────────────────────────────────────────


def create_scheduler() -> AsyncIOScheduler:
    """Build and configure the ``AsyncIOScheduler`` with all analytics jobs."""
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        run_population_health_refresh,
        trigger=IntervalTrigger(hours=6),
        id="population_health_refresh",
        name="Population health refresh (every 6h)",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        run_risk_score_update,
        trigger=IntervalTrigger(hours=4),
        id="risk_score_update",
        name="Readmission risk score update (every 4h)",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        run_cohort_refresh,
        trigger=IntervalTrigger(hours=12),
        id="cohort_refresh",
        name="Cohort segmentation refresh (every 12h)",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        run_daily_metrics_snapshot,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_metrics_snapshot",
        name="Daily metrics snapshot (02:00 UTC)",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        run_executive_digest,
        trigger=CronTrigger(hour=6, minute=0),
        id="executive_digest",
        name="Executive digest (06:00 UTC)",
        max_instances=1,
        replace_existing=True,
    )

    return scheduler


# ── CLI Entrypoint ────────────────────────────────────────────────────────────


async def _run() -> None:
    """Start the scheduler and block until a shutdown signal is received."""

    # Register all analytics agents so the registry is populated.
    from modules.analytics.agents import register_analytics_agents

    register_analytics_agents()

    scheduler = create_scheduler()
    scheduler.start()

    logger.info(
        "Analytics scheduler started — %d jobs registered",
        len(scheduler.get_jobs()),
    )
    for job in scheduler.get_jobs():
        logger.info("  • %s  [next run: %s]", job.name, job.next_run_time)

    # Graceful shutdown on SIGINT / SIGTERM
    shutdown_event = asyncio.Event()

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info("Received %s — shutting down scheduler …", sig.name)
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    await shutdown_event.wait()

    scheduler.shutdown(wait=True)
    logger.info("Analytics scheduler shut down cleanly")


def main() -> None:
    """Entrypoint for ``python -m modules.analytics.scheduler``."""
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted — exiting")


if __name__ == "__main__":
    main()
