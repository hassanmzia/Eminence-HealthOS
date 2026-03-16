"""
MCP Servers for Healthcare Platform

These servers provide standardized access to healthcare data sources
following the Model Context Protocol specification.

Servers:
- mcp_fhir_server: FHIR R4 data access (patients, vitals, conditions, medications)
- mcp_labs_server: Laboratory results with clinical interpretation
- mcp_rag_server: Clinical guidelines, ICD-10/CPT codes, drug interactions
"""

from .base import BaseMCPServer, MCPRequest, MCPResponse, MCPToolDefinition

__all__ = [
    "BaseMCPServer",
    "MCPRequest",
    "MCPResponse",
    "MCPToolDefinition",
]
