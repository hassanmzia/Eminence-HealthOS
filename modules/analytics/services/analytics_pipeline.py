"""
Eminence HealthOS — Analytics Pipeline Orchestrator

Provides high-level functions that invoke one or more analytics agents for a
given organization.  Used by the scheduler and by ad-hoc API endpoints.

Each function:
1. Resolves the required agent(s) from the registry.
2. Builds an ``AgentInput`` for the organization.
3. Invokes the agent via its ``run()`` lifecycle wrapper.
4. Returns the ``AgentOutput`` (or a dict of outputs for the full pipeline).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.types import AgentInput, AgentOutput, AgentStatus
from healthos_platform.orchestrator.registry import registry

logger = logging.getLogger(__name__)

# Ordered list of agents executed during a full analytics refresh.
_FULL_PIPELINE_AGENTS: list[str] = [
    "population_health",
    "readmission_risk",
    "cohort_segmentation",
    "cost_analyzer",
    "outcome_tracker",
    "cost_risk_insight",
    "executive_insight",
]


def _build_input(
    org_id: uuid.UUID,
    *,
    action: str = "overview",
    trigger: str = "scheduled_pipeline",
    extra_context: dict[str, Any] | None = None,
) -> AgentInput:
    """Create an ``AgentInput`` pre-filled for a scheduled analytics run."""
    context: dict[str, Any] = {"action": action}
    if extra_context:
        context.update(extra_context)
    return AgentInput(
        org_id=org_id,
        trigger=trigger,
        context=context,
    )


# ── Full Pipeline ─────────────────────────────────────────────────────────────


async def run_full_analytics(org_id: uuid.UUID) -> dict[str, AgentOutput]:
    """Run every registered analytics agent in sequence for *org_id*.

    Returns a mapping of ``{agent_name: AgentOutput}``.
    """
    results: dict[str, AgentOutput] = {}
    trace_id = uuid.uuid4()

    logger.info(
        "analytics.pipeline.full.start",
        extra={"org_id": str(org_id), "trace_id": str(trace_id)},
    )

    for agent_name in _FULL_PIPELINE_AGENTS:
        agent = registry.get(agent_name)
        if agent is None:
            logger.warning(
                "analytics.pipeline.agent_not_found",
                extra={"agent": agent_name},
            )
            continue

        try:
            agent_input = _build_input(org_id, trigger="full_pipeline")
            agent_input.trace_id = trace_id
            output = await agent.run(agent_input)
            results[agent_name] = output
        except Exception as exc:
            logger.error(
                "analytics.pipeline.agent_error",
                extra={"agent": agent_name, "org_id": str(org_id), "error": str(exc)},
            )
            results[agent_name] = AgentOutput(
                trace_id=trace_id,
                agent_name=agent_name,
                status=AgentStatus.FAILED,
                rationale=f"Pipeline error: {exc}",
                errors=[str(exc)],
            )

    logger.info(
        "analytics.pipeline.full.complete",
        extra={
            "org_id": str(org_id),
            "trace_id": str(trace_id),
            "agents_run": len(results),
        },
    )
    return results


# ── Risk Refresh ──────────────────────────────────────────────────────────────


async def run_risk_refresh(org_id: uuid.UUID) -> AgentOutput:
    """Run only the readmission-risk scoring agent for *org_id*."""
    agent = registry.get("readmission_risk")
    if agent is None:
        raise RuntimeError("readmission_risk agent is not registered")

    logger.info("analytics.pipeline.risk_refresh.start", extra={"org_id": str(org_id)})
    agent_input = _build_input(org_id, action="score", trigger="risk_refresh")
    output = await agent.run(agent_input)
    logger.info(
        "analytics.pipeline.risk_refresh.complete",
        extra={"org_id": str(org_id), "status": output.status.value},
    )
    return output


# ── Cohort Refresh ────────────────────────────────────────────────────────────


async def run_cohort_refresh(org_id: uuid.UUID) -> AgentOutput:
    """Run the cohort segmentation agent for *org_id*."""
    agent = registry.get("cohort_segmentation")
    if agent is None:
        raise RuntimeError("cohort_segmentation agent is not registered")

    logger.info("analytics.pipeline.cohort_refresh.start", extra={"org_id": str(org_id)})
    agent_input = _build_input(org_id, action="segment", trigger="cohort_refresh")
    output = await agent.run(agent_input)
    logger.info(
        "analytics.pipeline.cohort_refresh.complete",
        extra={"org_id": str(org_id), "status": output.status.value},
    )
    return output
