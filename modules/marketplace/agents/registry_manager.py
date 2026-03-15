"""
Eminence HealthOS — Marketplace Registry Manager Agent
Layer 3 (Decisioning): Manages the AI Agent Marketplace registry — listing,
publishing, versioning, and validating third-party agents that run on HealthOS.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)

logger = logging.getLogger(__name__)

# ── Required metadata fields for agent publication ────────────────────────────

REQUIRED_AGENT_METADATA = {"name", "version", "tier", "description", "author", "license"}

# ── Platform compatibility matrix ─────────────────────────────────────────────

PLATFORM_VERSION = "5.0.0"

SUPPORTED_TIERS = {"sensing", "interpretation", "decisioning", "action", "measurement"}

SUPPORTED_LICENSES = {
    "MIT", "Apache-2.0", "BSD-3-Clause", "AGPL-3.0", "HealthOS-Commercial",
}

# ── In-memory registry (replaced by DB in production) ─────────────────────────

_REGISTRY: dict[str, dict[str, Any]] = {
    "sepsis-early-warning": {
        "id": "sepsis-early-warning",
        "name": "Sepsis Early Warning Agent",
        "version": "2.1.0",
        "tier": "interpretation",
        "description": "Detects early signs of sepsis using SOFA scoring and vital trend analysis.",
        "author": "ClinicalAI Corp",
        "license": "HealthOS-Commercial",
        "category": "Clinical",
        "status": "published",
        "platform_version": "5.0.0",
        "installs": 342,
        "rating": 4.8,
        "created_at": "2025-08-15T10:00:00Z",
    },
    "revenue-leakage-detector": {
        "id": "revenue-leakage-detector",
        "name": "Revenue Leakage Detector",
        "version": "1.3.0",
        "tier": "measurement",
        "description": "Identifies missed charges, under-coding, and revenue cycle inefficiencies.",
        "author": "FinHealth Analytics",
        "license": "Apache-2.0",
        "category": "Operations",
        "status": "published",
        "platform_version": "5.0.0",
        "installs": 189,
        "rating": 4.5,
        "created_at": "2025-09-01T14:30:00Z",
    },
}


class RegistryManagerAgent(BaseAgent):
    """Manages the marketplace registry for third-party HealthOS agents."""

    name = "marketplace_registry_manager"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = "Manages listing, publishing, versioning, and validation of marketplace agents."

    async def process(self, input_data: AgentInput) -> AgentOutput:
        action = input_data.context.get("action", "list_agents")
        ctx = input_data.context

        handler = {
            "list_agents": self._list_agents,
            "publish_agent": self._publish_agent,
            "validate_agent": self._validate_agent,
            "deprecate_agent": self._deprecate_agent,
        }.get(action)

        if handler is None:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Action '{action}' is not supported by the registry manager.",
                status=AgentStatus.FAILED,
            )

        return await handler(input_data, ctx)

    # ── Action Handlers ───────────────────────────────────────────────────────

    async def _list_agents(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """List all published agents, optionally filtered by category or tier."""
        category = ctx.get("category")
        tier_filter = ctx.get("tier")
        search = ctx.get("search", "").lower()

        agents = list(_REGISTRY.values())

        if category:
            agents = [a for a in agents if a.get("category", "").lower() == category.lower()]
        if tier_filter:
            agents = [a for a in agents if a.get("tier") == tier_filter]
        if search:
            agents = [
                a for a in agents
                if search in a.get("name", "").lower() or search in a.get("description", "").lower()
            ]

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "agents": agents,
                "total": len(agents),
                "platform_version": PLATFORM_VERSION,
            },
            confidence=1.0,
            rationale=f"Listed {len(agents)} marketplace agents.",
        )

    async def _publish_agent(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Publish a new agent to the marketplace after validation."""
        agent_meta = ctx.get("agent_metadata", {})

        # Validate required fields
        validation = self._validate_metadata(agent_meta)
        if not validation["valid"]:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"published": False, "validation_errors": validation["errors"]},
                confidence=0.5,
                rationale="Agent metadata failed validation.",
                status=AgentStatus.COMPLETED,
            )

        # Check platform compatibility
        compat = self._check_compatibility(agent_meta)
        if not compat["compatible"]:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"published": False, "compatibility_errors": compat["errors"]},
                confidence=0.5,
                rationale="Agent is not compatible with the current platform version.",
            )

        # Register the agent
        agent_id = agent_meta.get("id") or agent_meta["name"].lower().replace(" ", "-")
        entry = {
            "id": agent_id,
            "name": agent_meta["name"],
            "version": agent_meta["version"],
            "tier": agent_meta["tier"],
            "description": agent_meta["description"],
            "author": agent_meta["author"],
            "license": agent_meta["license"],
            "category": agent_meta.get("category", "General"),
            "status": "pending_review",
            "platform_version": PLATFORM_VERSION,
            "installs": 0,
            "rating": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _REGISTRY[agent_id] = entry

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"published": True, "agent_id": agent_id, "status": "pending_review", "agent": entry},
            confidence=0.95,
            rationale=f"Agent '{agent_meta['name']}' published successfully and is pending security review.",
        )

    async def _validate_agent(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Validate agent metadata without publishing."""
        agent_meta = ctx.get("agent_metadata", {})
        validation = self._validate_metadata(agent_meta)
        compat = self._check_compatibility(agent_meta)

        all_errors = validation["errors"] + compat["errors"]
        is_valid = len(all_errors) == 0

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "valid": is_valid,
                "errors": all_errors,
                "metadata_valid": validation["valid"],
                "platform_compatible": compat["compatible"],
            },
            confidence=1.0 if is_valid else 0.6,
            rationale="Agent validation " + ("passed" if is_valid else f"failed with {len(all_errors)} error(s)") + ".",
        )

    async def _deprecate_agent(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Deprecate an agent in the marketplace."""
        agent_id = ctx.get("agent_id", "")
        reason = ctx.get("reason", "No reason provided")

        if agent_id not in _REGISTRY:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"deprecated": False, "error": f"Agent '{agent_id}' not found in registry."},
                confidence=0.0,
                rationale=f"Cannot deprecate unknown agent '{agent_id}'.",
                status=AgentStatus.FAILED,
            )

        _REGISTRY[agent_id]["status"] = "deprecated"
        _REGISTRY[agent_id]["deprecated_at"] = datetime.now(timezone.utc).isoformat()
        _REGISTRY[agent_id]["deprecation_reason"] = reason

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"deprecated": True, "agent_id": agent_id, "reason": reason},
            confidence=1.0,
            rationale=f"Agent '{agent_id}' has been deprecated: {reason}",
        )

    # ── Validation Helpers ────────────────────────────────────────────────────

    def _validate_metadata(self, meta: dict[str, Any]) -> dict[str, Any]:
        """Check that agent metadata has all required fields."""
        errors: list[str] = []
        missing = REQUIRED_AGENT_METADATA - set(meta.keys())
        if missing:
            errors.append(f"Missing required fields: {', '.join(sorted(missing))}")

        if meta.get("tier") and meta["tier"] not in SUPPORTED_TIERS:
            errors.append(f"Unsupported tier '{meta['tier']}'. Must be one of: {', '.join(sorted(SUPPORTED_TIERS))}")

        if meta.get("license") and meta["license"] not in SUPPORTED_LICENSES:
            errors.append(f"Unsupported license '{meta['license']}'. Supported: {', '.join(sorted(SUPPORTED_LICENSES))}")

        if meta.get("version"):
            parts = meta["version"].split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append(f"Invalid version format '{meta['version']}'. Must be semver (e.g., 1.0.0).")

        return {"valid": len(errors) == 0, "errors": errors}

    def _check_compatibility(self, meta: dict[str, Any]) -> dict[str, Any]:
        """Check agent compatibility with the current platform version."""
        errors: list[str] = []

        min_platform = meta.get("min_platform_version")
        if min_platform:
            if self._compare_versions(min_platform, PLATFORM_VERSION) > 0:
                errors.append(
                    f"Agent requires platform >= {min_platform}, current is {PLATFORM_VERSION}."
                )

        max_platform = meta.get("max_platform_version")
        if max_platform:
            if self._compare_versions(PLATFORM_VERSION, max_platform) > 0:
                errors.append(
                    f"Agent supports platform <= {max_platform}, current is {PLATFORM_VERSION}."
                )

        return {"compatible": len(errors) == 0, "errors": errors}

    @staticmethod
    def _compare_versions(a: str, b: str) -> int:
        """Compare two semver strings. Returns -1, 0, or 1."""
        pa = [int(x) for x in a.split(".")]
        pb = [int(x) for x in b.split(".")]
        for x, y in zip(pa, pb):
            if x < y:
                return -1
            if x > y:
                return 1
        return 0
