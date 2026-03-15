"""AI Agent Marketplace module API routes — registry, security scanning, analytics."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Registry ──────────────────────────────────────────────────────────────────


@router.get("/agents")
async def list_marketplace_agents(
    category: str | None = None,
    tier: str | None = None,
    search: str | None = None,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """List all available agents in the marketplace."""
    from modules.marketplace.agents.registry_manager import RegistryManagerAgent

    agent = RegistryManagerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="marketplace.agents.list",
        context={
            "action": "list_agents",
            "category": category,
            "tier": tier,
            "search": search,
        },
    ))
    return output.result


@router.get("/agents/{agent_id}")
async def get_marketplace_agent(
    agent_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get details for a specific marketplace agent."""
    from modules.marketplace.agents.registry_manager import RegistryManagerAgent

    agent = RegistryManagerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="marketplace.agents.get",
        context={"action": "list_agents", "search": agent_id},
    ))
    agents = output.result.get("agents", [])
    matched = next((a for a in agents if a.get("id") == agent_id), None)
    if matched:
        return matched
    return {"error": f"Agent '{agent_id}' not found."}


@router.post("/agents/publish")
async def publish_marketplace_agent(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Publish a new agent to the marketplace."""
    from modules.marketplace.agents.registry_manager import RegistryManagerAgent

    agent = RegistryManagerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="marketplace.agents.publish",
        context={"action": "publish_agent", "agent_metadata": body},
    ))
    return output.result


@router.post("/agents/{agent_id}/install")
async def install_marketplace_agent(
    agent_id: str,
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Install a marketplace agent to the current tenant."""
    from modules.marketplace.agents.usage_analytics import UsageAnalyticsAgent

    agent = UsageAnalyticsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="marketplace.agents.install",
        context={
            "action": "track_install",
            "agent_id": agent_id,
            "tenant_id": tenant_id,
        },
    ))
    return output.result


@router.post("/agents/{agent_id}/scan")
async def scan_marketplace_agent(
    agent_id: str,
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run a security scan on a marketplace agent."""
    from modules.marketplace.agents.security_scanner import SecurityScannerAgent

    agent = SecurityScannerAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="marketplace.agents.scan",
        context={
            "action": "scan_agent",
            "agent_id": agent_id,
            "source_code": body.get("source_code", ""),
        },
    ))
    return output.result


# ── Analytics ─────────────────────────────────────────────────────────────────


@router.get("/analytics")
async def get_marketplace_analytics(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get aggregate marketplace analytics."""
    from modules.marketplace.agents.usage_analytics import UsageAnalyticsAgent

    agent = UsageAnalyticsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="marketplace.analytics.overview",
        context={"action": "get_analytics"},
    ))
    return output.result


@router.get("/analytics/{agent_id}")
async def get_agent_analytics(
    agent_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get usage analytics for a specific marketplace agent."""
    from modules.marketplace.agents.usage_analytics import UsageAnalyticsAgent

    agent = UsageAnalyticsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=None,
        trigger="marketplace.analytics.agent",
        context={"action": "get_analytics", "agent_id": agent_id},
    ))
    return output.result
