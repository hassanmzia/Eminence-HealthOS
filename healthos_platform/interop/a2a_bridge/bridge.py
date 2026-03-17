"""
Eminence HealthOS — A2A Protocol Bridge
Bridges the internal HealthOS agent system with the A2A gateway,
handling agent registration, task delegation, and message routing.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

A2A_GATEWAY_URL = "http://localhost:3200"


class A2ABridge:
    """
    Bridges between HealthOS internal agents and the A2A gateway.
    Handles registration, task submission, and result collection.
    """

    def __init__(self, gateway_url: str = A2A_GATEWAY_URL) -> None:
        self.gateway_url = gateway_url
        self._registered_agents: set[str] = set()
        self._log = logger.bind(component="a2a_bridge")

    async def register_agent(self, agent_card: dict[str, Any]) -> bool:
        """Register an internal agent with the A2A gateway."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.gateway_url}/a2a/agents/register",
                    json=agent_card,
                )
                resp.raise_for_status()

            self._registered_agents.add(agent_card["id"])
            self._log.info("a2a.agent_registered", agent_id=agent_card["id"])
            return True
        except Exception as e:
            self._log.warning("a2a.registration_failed", error=str(e))
            return False

    async def submit_task(self, task: dict[str, Any]) -> dict[str, Any] | None:
        """Submit a task to the A2A gateway for delegation."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.gateway_url}/a2a/tasks",
                    json=task,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            self._log.warning("a2a.task_submission_failed", error=str(e))
            return None

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get the status of a task from the A2A gateway."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.gateway_url}/a2a/tasks/{task_id}")
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            self._log.warning("a2a.task_status_failed", error=str(e))
            return None

    async def discover_agents(
        self, agent_type: str | None = None, tier: int | None = None
    ) -> list[dict[str, Any]]:
        """Discover agents registered with the A2A gateway."""
        try:
            import httpx

            url = f"{self.gateway_url}/a2a/agents"
            if agent_type:
                url = f"{self.gateway_url}/a2a/agents/type/{agent_type}"
            elif tier is not None:
                url = f"{self.gateway_url}/a2a/agents/tier/{tier}"

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json().get("agents", [])
        except Exception as e:
            self._log.warning("a2a.discovery_failed", error=str(e))
            return []

    async def heartbeat(self, agent_id: str) -> bool:
        """Send heartbeat for a registered agent."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{self.gateway_url}/a2a/agents/{agent_id}/heartbeat"
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def register_all_agents(self) -> int:
        """Register all internal HealthOS agents with the A2A gateway."""
        from healthos_platform.orchestrator.registry import registry

        registered = 0
        for agent_info in registry.list_agents():
            card = {
                "id": f"healthos-{agent_info['name']}",
                "name": agent_info["name"],
                "type": agent_info["name"],
                "tier": self._tier_to_int(agent_info.get("tier", "sensing")),
                "capabilities": [agent_info["name"]],
                "endpoint": f"http://localhost:8000/api/v1/agents/{agent_info['name']}",
                "status": "online",
            }
            if await self.register_agent(card):
                registered += 1

        # Register MS Risk Screening agents (proxied to ms-risk-backend)
        ms_risk_registered = await self._register_ms_risk_agents()
        registered += ms_risk_registered

        self._log.info("a2a.bulk_registration", registered=registered)
        return registered

    async def _register_ms_risk_agents(self) -> int:
        """Register the 5 MS Risk Screening pipeline agents."""
        ms_risk_agents = [
            {
                "id": "ms-risk-retrieval",
                "name": "MS Risk Retrieval Agent",
                "type": "retrieval",
                "tier": 1,
                "capabilities": ["ms_patient_retrieval", "ehr_data_fetch"],
                "endpoint": "http://ms-risk-backend:8000/a2a/agents/retrieval/",
                "status": "online",
                "metadata": {
                    "module": "ms_risk_screening",
                    "description": "Fetches patient records, labs, and imaging data from the EHR",
                },
            },
            {
                "id": "ms-risk-phenotyping",
                "name": "MS Risk Phenotyping Agent",
                "type": "phenotyping",
                "tier": 2,
                "capabilities": ["ms_risk_scoring", "phenotype_analysis"],
                "endpoint": "http://ms-risk-backend:8000/a2a/agents/phenotyping/",
                "status": "online",
                "metadata": {
                    "module": "ms_risk_screening",
                    "description": "Computes MS risk score from clinical features and symptom patterns",
                },
            },
            {
                "id": "ms-risk-notes-imaging",
                "name": "MS Risk Notes & Imaging Agent",
                "type": "notes_imaging",
                "tier": 2,
                "capabilities": ["nlp_note_analysis", "mri_lesion_detection"],
                "endpoint": "http://ms-risk-backend:8000/a2a/agents/notes_imaging/",
                "status": "online",
                "metadata": {
                    "module": "ms_risk_screening",
                    "description": "NLP analysis of clinical notes and MRI lesion detection",
                },
            },
            {
                "id": "ms-risk-safety-governance",
                "name": "MS Risk Safety & Governance Agent",
                "type": "safety_governance",
                "tier": 3,
                "capabilities": ["safety_guardrails", "demographic_checks", "rate_limiting"],
                "endpoint": "http://ms-risk-backend:8000/a2a/agents/safety_governance/",
                "status": "online",
                "metadata": {
                    "module": "ms_risk_screening",
                    "description": "Applies guardrails, demographic checks, and rate limits",
                },
            },
            {
                "id": "ms-risk-coordinator",
                "name": "MS Risk Coordinator Agent",
                "type": "coordinator",
                "tier": 4,
                "capabilities": ["ms_screening_orchestration", "action_determination"],
                "endpoint": "http://ms-risk-backend:8000/a2a/agents/coordinator/",
                "status": "online",
                "metadata": {
                    "module": "ms_risk_screening",
                    "description": "Orchestrates the pipeline, determines action, and generates rationale",
                },
            },
        ]

        registered = 0
        for card in ms_risk_agents:
            if await self.register_agent(card):
                registered += 1

        self._log.info("a2a.ms_risk_registration", registered=registered)
        return registered

    @staticmethod
    def _tier_to_int(tier_value: str) -> int:
        """Convert tier string to integer."""
        tier_map = {
            "sensing": 1,
            "interpretation": 2,
            "decisioning": 3,
            "action": 4,
            "measurement": 5,
        }
        return tier_map.get(tier_value, 1)
