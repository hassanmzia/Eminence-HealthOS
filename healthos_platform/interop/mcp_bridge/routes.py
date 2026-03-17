"""
Eminence HealthOS — MCP Bridge REST Endpoints
Provides FastAPI routes for the MCP server to fetch patient context
and execute tools against the Django backend.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from healthos_platform.interop.mcp_bridge.context_builder import MCPContextBuilder
from healthos_platform.interop.mcp_bridge.tool_executor import MCPToolExecutor

router = APIRouter(prefix="/mcp", tags=["MCP Bridge"])

# Singletons
_context_builder = MCPContextBuilder()
_tool_executor = MCPToolExecutor()


class ToolExecuteRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}
    callId: str = ""


@router.get("/servers")
async def list_mcp_servers() -> dict[str, Any]:
    """List configured MCP servers and their status."""
    import os
    import httpx

    servers_config = [
        {"id": "mcp-fhir", "name": "FHIR Server", "url": os.getenv("MCP_FHIR_SERVER_URL", "http://localhost:8005"), "tools": ["read_patient", "search_patient", "read_observation"]},
        {"id": "mcp-labs", "name": "Labs Server", "url": os.getenv("MCP_LABS_SERVER_URL", "http://localhost:8006"), "tools": ["query_lab_results", "order_lab_test"]},
        {"id": "mcp-rag", "name": "RAG Server", "url": os.getenv("MCP_RAG_SERVER_URL", "http://localhost:8007"), "tools": ["search_documents", "retrieve_context"]},
        {"id": "mcp-adapter", "name": "FHIR Adapter", "url": os.getenv("MCP_FHIR_ADAPTER_URL", "http://localhost:8002"), "tools": ["write_observation", "write_condition"]},
    ]

    results = []
    for srv in servers_config:
        entry = {"id": srv["id"], "name": srv["name"], "url": srv["url"], "tools": srv["tools"], "status": "disconnected", "last_heartbeat": None}
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{srv['url']}/health")
                if r.status_code == 200:
                    entry["status"] = "connected"
                    from datetime import datetime, timezone
                    entry["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                else:
                    entry["status"] = "error"
        except Exception:
            entry["status"] = "disconnected"
        results.append(entry)

    return {"servers": results}


@router.get("/context/{patient_id}")
async def get_mcp_context(patient_id: str, request: Request) -> dict[str, Any]:
    """Build and return the full MCP context for a patient."""
    org_id = getattr(request.state, "tenant_id", "default")
    context = await _context_builder.build_context(patient_id, org_id)
    return context


@router.get("/tools")
async def list_mcp_tools() -> dict[str, Any]:
    """List available MCP tools."""
    return {"tools": _tool_executor.list_tools()}


@router.post("/tools/execute")
async def execute_mcp_tool(
    body: ToolExecuteRequest, request: Request
) -> dict[str, Any]:
    """Execute an MCP tool call."""
    org_id = getattr(request.state, "tenant_id", "default")
    result = await _tool_executor.execute(body.tool, body.arguments, org_id)
    return result
