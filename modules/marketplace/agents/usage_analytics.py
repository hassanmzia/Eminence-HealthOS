"""
Eminence HealthOS — Marketplace Usage Analytics Agent
Layer 5 (Measurement): Tracks marketplace analytics — installs, usage patterns,
ratings, and popularity rankings for third-party agents.
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

# ── In-memory analytics store (replaced by time-series DB in production) ──────

_INSTALL_LOG: list[dict[str, Any]] = [
    {"agent_id": "sepsis-early-warning", "tenant_id": "tenant-001", "installed_at": "2025-11-01T08:00:00Z"},
    {"agent_id": "sepsis-early-warning", "tenant_id": "tenant-002", "installed_at": "2025-11-05T14:30:00Z"},
    {"agent_id": "revenue-leakage-detector", "tenant_id": "tenant-001", "installed_at": "2025-11-10T09:15:00Z"},
]

_USAGE_STATS: dict[str, dict[str, Any]] = {
    "sepsis-early-warning": {
        "total_installs": 342,
        "active_installs": 298,
        "total_invocations": 128_450,
        "avg_daily_invocations": 1_540,
        "avg_latency_ms": 245,
        "error_rate": 0.002,
        "ratings": [5, 5, 4, 5, 5, 4, 5, 5, 4, 5],
        "last_30d_installs": 28,
    },
    "revenue-leakage-detector": {
        "total_installs": 189,
        "active_installs": 156,
        "total_invocations": 45_230,
        "avg_daily_invocations": 720,
        "avg_latency_ms": 380,
        "error_rate": 0.005,
        "ratings": [4, 5, 4, 5, 4, 4, 5, 4, 5, 4],
        "last_30d_installs": 15,
    },
    "smart-scheduling-optimizer": {
        "total_installs": 567,
        "active_installs": 489,
        "total_invocations": 234_100,
        "avg_daily_invocations": 2_100,
        "avg_latency_ms": 190,
        "error_rate": 0.001,
        "ratings": [5, 5, 5, 4, 5, 5, 5, 5, 4, 5],
        "last_30d_installs": 45,
    },
    "clinical-note-enhancer": {
        "total_installs": 412,
        "active_installs": 378,
        "total_invocations": 89_320,
        "avg_daily_invocations": 1_200,
        "avg_latency_ms": 520,
        "error_rate": 0.003,
        "ratings": [5, 4, 5, 5, 4, 5, 4, 5, 5, 4],
        "last_30d_installs": 32,
    },
}


class UsageAnalyticsAgent(BaseAgent):
    """Tracks marketplace analytics — installs, usage, ratings, and popularity."""

    name = "marketplace_usage_analytics"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Tracks and reports on marketplace agent usage, installs, and ratings."

    async def process(self, input_data: AgentInput) -> AgentOutput:
        action = input_data.context.get("action", "get_analytics")
        ctx = input_data.context

        handler = {
            "track_install": self._track_install,
            "get_analytics": self._get_analytics,
            "get_popular_agents": self._get_popular_agents,
            "calculate_ratings": self._calculate_ratings,
        }.get(action)

        if handler is None:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Action '{action}' is not supported by the analytics agent.",
                status=AgentStatus.FAILED,
            )

        return await handler(input_data, ctx)

    # ── Action Handlers ───────────────────────────────────────────────────────

    async def _track_install(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Track a new agent installation."""
        agent_id = ctx.get("agent_id", "")
        tenant_id = ctx.get("tenant_id", str(input_data.org_id))

        entry = {
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        _INSTALL_LOG.append(entry)

        # Update stats
        if agent_id in _USAGE_STATS:
            _USAGE_STATS[agent_id]["total_installs"] += 1
            _USAGE_STATS[agent_id]["active_installs"] += 1
            _USAGE_STATS[agent_id]["last_30d_installs"] += 1
        else:
            _USAGE_STATS[agent_id] = {
                "total_installs": 1,
                "active_installs": 1,
                "total_invocations": 0,
                "avg_daily_invocations": 0,
                "avg_latency_ms": 0,
                "error_rate": 0.0,
                "ratings": [],
                "last_30d_installs": 1,
            }

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "tracked": True,
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "total_installs": _USAGE_STATS[agent_id]["total_installs"],
            },
            confidence=1.0,
            rationale=f"Tracked install of '{agent_id}' for tenant '{tenant_id}'.",
        )

    async def _get_analytics(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Get usage analytics for a specific agent or all agents."""
        agent_id = ctx.get("agent_id")

        if agent_id:
            stats = _USAGE_STATS.get(agent_id)
            if not stats:
                return self.build_output(
                    trace_id=input_data.trace_id,
                    result={"error": f"No analytics found for agent '{agent_id}'."},
                    confidence=0.0,
                    rationale=f"Agent '{agent_id}' has no recorded analytics.",
                    status=AgentStatus.FAILED,
                )

            ratings = stats.get("ratings", [])
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "agent_id": agent_id,
                    "total_installs": stats["total_installs"],
                    "active_installs": stats["active_installs"],
                    "total_invocations": stats["total_invocations"],
                    "avg_daily_invocations": stats["avg_daily_invocations"],
                    "avg_latency_ms": stats["avg_latency_ms"],
                    "error_rate": stats["error_rate"],
                    "avg_rating": round(avg_rating, 1),
                    "rating_count": len(ratings),
                    "last_30d_installs": stats["last_30d_installs"],
                },
                confidence=0.95,
                rationale=f"Analytics retrieved for agent '{agent_id}'.",
            )

        # Aggregate analytics
        total_agents = len(_USAGE_STATS)
        total_installs = sum(s["total_installs"] for s in _USAGE_STATS.values())
        total_invocations = sum(s["total_invocations"] for s in _USAGE_STATS.values())

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "total_agents": total_agents,
                "total_installs": total_installs,
                "total_invocations": total_invocations,
                "agents": {
                    aid: {
                        "total_installs": s["total_installs"],
                        "active_installs": s["active_installs"],
                        "avg_rating": round(sum(s["ratings"]) / len(s["ratings"]), 1) if s["ratings"] else 0.0,
                    }
                    for aid, s in _USAGE_STATS.items()
                },
            },
            confidence=0.95,
            rationale=f"Aggregate analytics for {total_agents} marketplace agents.",
        )

    async def _get_popular_agents(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Get the most popular agents ranked by installs."""
        limit = ctx.get("limit", 10)
        sort_by = ctx.get("sort_by", "total_installs")

        ranked = []
        for agent_id, stats in _USAGE_STATS.items():
            ratings = stats.get("ratings", [])
            avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
            ranked.append({
                "agent_id": agent_id,
                "total_installs": stats["total_installs"],
                "active_installs": stats["active_installs"],
                "avg_rating": avg_rating,
                "total_invocations": stats["total_invocations"],
                "last_30d_installs": stats["last_30d_installs"],
            })

        if sort_by == "rating":
            ranked.sort(key=lambda x: x["avg_rating"], reverse=True)
        elif sort_by == "recent":
            ranked.sort(key=lambda x: x["last_30d_installs"], reverse=True)
        else:
            ranked.sort(key=lambda x: x["total_installs"], reverse=True)

        ranked = ranked[:limit]

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "popular_agents": ranked,
                "sort_by": sort_by,
                "total": len(ranked),
            },
            confidence=1.0,
            rationale=f"Top {len(ranked)} agents by {sort_by}.",
        )

    async def _calculate_ratings(self, input_data: AgentInput, ctx: dict[str, Any]) -> AgentOutput:
        """Calculate rating statistics for agents."""
        agent_id = ctx.get("agent_id")

        if agent_id:
            stats = _USAGE_STATS.get(agent_id, {})
            ratings = stats.get("ratings", [])
            if not ratings:
                return self.build_output(
                    trace_id=input_data.trace_id,
                    result={"agent_id": agent_id, "avg_rating": 0.0, "rating_count": 0, "distribution": {}},
                    confidence=1.0,
                    rationale=f"No ratings found for agent '{agent_id}'.",
                )

            distribution = {str(i): ratings.count(i) for i in range(1, 6)}
            return self.build_output(
                trace_id=input_data.trace_id,
                result={
                    "agent_id": agent_id,
                    "avg_rating": round(sum(ratings) / len(ratings), 1),
                    "rating_count": len(ratings),
                    "distribution": distribution,
                },
                confidence=1.0,
                rationale=f"Rating statistics for '{agent_id}'.",
            )

        # All agents
        all_ratings: dict[str, Any] = {}
        for aid, stats in _USAGE_STATS.items():
            ratings = stats.get("ratings", [])
            all_ratings[aid] = {
                "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
                "rating_count": len(ratings),
            }

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"ratings": all_ratings},
            confidence=1.0,
            rationale=f"Rating statistics for {len(all_ratings)} agents.",
        )
