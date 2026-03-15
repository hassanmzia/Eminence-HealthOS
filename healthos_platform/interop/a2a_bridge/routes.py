"""
Eminence HealthOS — A2A Bridge REST Endpoints
FastAPI routes for A2A bridge operations.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from healthos_platform.interop.a2a_bridge.bridge import A2ABridge

router = APIRouter(prefix="/a2a", tags=["A2A Bridge"])

_bridge = A2ABridge()


class TaskSubmitRequest(BaseModel):
    type: str
    priority: str = "NORMAL"
    sourceAgentId: str = ""
    payload: dict[str, Any] = {}


@router.post("/register-all")
async def register_all_agents() -> dict[str, Any]:
    """Register all internal agents with the A2A gateway."""
    count = await _bridge.register_all_agents()
    return {"registered": count}


@router.get("/agents")
async def discover_agents(
    agent_type: str | None = None, tier: int | None = None
) -> dict[str, Any]:
    """Discover agents from the A2A gateway."""
    agents = await _bridge.discover_agents(agent_type=agent_type, tier=tier)
    return {"agents": agents}


@router.post("/tasks")
async def submit_task(body: TaskSubmitRequest) -> dict[str, Any]:
    """Submit a task to the A2A gateway."""
    result = await _bridge.submit_task(body.model_dump())
    return result or {"error": "Task submission failed"}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get task status from the A2A gateway."""
    result = await _bridge.get_task_status(task_id)
    return result or {"error": "Task not found"}
