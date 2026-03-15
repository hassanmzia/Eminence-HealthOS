"""AI Marketplace module schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class AgentPublish(BaseModel):
    name: str
    version: str
    tier: str = Field(..., description="sensing, interpretation, decisioning, action, measurement")
    description: str
    author: str
    license: str = "proprietary"
    category: str = Field("Clinical", description="Clinical, Operations, Analytics, Integration")
    source_url: Optional[str] = None
    documentation_url: Optional[str] = None
    min_platform_version: str = "1.0.0"


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    version: str
    tier: str
    description: str
    author: str
    category: str
    rating: float
    installs: int
    status: str


class AgentInstall(BaseModel):
    agent_id: str
    tenant_id: Optional[str] = None
    configuration: Optional[dict] = None


class SecurityScanResult(BaseModel):
    agent_id: str
    score: int = Field(..., ge=0, le=100)
    passed: bool
    findings: list[dict]
    scanned_at: str


class MarketplaceAnalytics(BaseModel):
    total_agents: int
    total_installs: int
    categories: dict[str, int]
    top_agents: list[dict]
