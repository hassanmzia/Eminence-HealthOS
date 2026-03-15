"""AI Marketplace service layer."""

import logging
from typing import Optional

logger = logging.getLogger("healthos.marketplace.marketplace_service")


class MarketplaceService:
    """Business logic for AI agent marketplace."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._agents: dict[str, dict] = {}
        self._installs: dict[str, list[str]] = {}

    async def list_agents(self, category: Optional[str] = None, status: str = "published") -> list[dict]:
        agents = list(self._agents.values())
        if category:
            agents = [a for a in agents if a.get("category") == category]
        return [a for a in agents if a.get("status") == status]

    async def get_agent(self, agent_id: str) -> Optional[dict]:
        return self._agents.get(agent_id)

    async def publish_agent(self, data: dict) -> dict:
        agent_id = data.get("agent_id", "")
        self._agents[agent_id] = {**data, "status": "published", "installs": 0, "rating": 0.0}
        logger.info("Published marketplace agent %s", agent_id)
        return self._agents[agent_id]

    async def install_agent(self, agent_id: str, tenant_id: str) -> dict:
        agent = self._agents.get(agent_id, {})
        agent["installs"] = agent.get("installs", 0) + 1
        self._installs.setdefault(tenant_id, []).append(agent_id)
        logger.info("Installed agent %s for tenant %s", agent_id, tenant_id)
        return {"agent_id": agent_id, "tenant_id": tenant_id, "status": "installed"}

    async def get_analytics(self) -> dict:
        return {
            "total_agents": len(self._agents),
            "total_installs": sum(a.get("installs", 0) for a in self._agents.values()),
            "categories": {},
            "top_agents": sorted(self._agents.values(), key=lambda a: a.get("installs", 0), reverse=True)[:5],
        }
