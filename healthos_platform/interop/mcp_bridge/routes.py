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
