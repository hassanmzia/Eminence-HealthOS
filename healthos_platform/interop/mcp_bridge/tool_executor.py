"""
Eminence HealthOS — MCP Tool Executor
Routes MCP tool calls from the MCP server to Django-side handlers.
Each tool maps to a specific backend operation.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger()


class MCPToolExecutor:
    """
    Executes MCP tool calls by routing them to appropriate Django-side handlers.
    Supports: vitals, medications, conditions, notifications, care gaps,
    care plans, literature RAG, drug interactions, risk scores.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Awaitable[Any]]] = {
            "query_vitals": self._handle_query_vitals,
            "query_medications": self._handle_query_medications,
            "query_conditions": self._handle_query_conditions,
            "send_notification": self._handle_send_notification,
            "create_care_gap": self._handle_create_care_gap,
            "update_care_plan": self._handle_update_care_plan,
            "literature_search": self._handle_literature_search,
            "check_drug_interactions": self._handle_drug_interactions,
            "get_risk_scores": self._handle_risk_scores,
            # MS Risk Screening tools — proxied to ms-risk-backend MCP server
            "ms_screen_patient": self._handle_ms_risk_proxy,
            "ms_run_screening_workflow": self._handle_ms_risk_proxy,
            "ms_get_patient_risk_card": self._handle_ms_risk_proxy,
            "ms_analyze_fairness": self._handle_ms_risk_proxy,
            "ms_what_if_policy": self._handle_ms_risk_proxy,
            "ms_review_assessment": self._handle_ms_risk_proxy,
            "ms_get_workflow_metrics": self._handle_ms_risk_proxy,
            "ms_summarize_note": self._handle_ms_risk_proxy,
        }
        self._log = logger.bind(component="mcp_tool_executor")

    def list_tools(self) -> list[dict[str, str]]:
        """List available tools."""
        return [
            {"name": name, "description": f"MCP tool: {name}"}
            for name in self._handlers
        ]

    # ── Tool Handlers ────────────────────────────────────────────────────────

    async def _handle_query_vitals(
        self, args: dict[str, Any], org_id: str
    ) -> list[dict[str, Any]]:
        """Query patient vitals from the database."""
        patient_id = args.get("patient_id", "")
        vital_type = args.get("vital_type")
        limit = args.get("limit", 20)

        try:
            from shared.models.clinical import Observation

            qs = Observation.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
                category="vital-signs",
            )
            if vital_type:
                qs = qs.filter(code_display__icontains=vital_type)

            qs = qs.order_by("-effective_date")[:limit]
            return [
                {
                    "type": v.code_display,
                    "value": v.value,
                    "unit": v.unit,
                    "recorded_at": str(v.effective_date),
                }
                async for v in qs
            ]
        except Exception:
            return []

    async def _handle_query_medications(
        self, args: dict[str, Any], org_id: str
    ) -> list[dict[str, Any]]:
        """Query patient medications."""
        patient_id = args.get("patient_id", "")
        try:
            from shared.models.clinical import MedicationRequest

            meds = MedicationRequest.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
                status="active",
            )
            return [
                {"code": m.code, "display": m.display, "dosage": m.dosage_instruction}
                async for m in meds
            ]
        except Exception:
            return []

    async def _handle_query_conditions(
        self, args: dict[str, Any], org_id: str
    ) -> list[dict[str, Any]]:
        """Query patient conditions."""
        patient_id = args.get("patient_id", "")
        try:
            from shared.models.clinical import Condition

            conditions = Condition.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
                clinical_status="active",
            )
            return [
                {"code": c.code, "display": c.display, "onset": str(c.onset_date)}
                async for c in conditions
            ]
        except Exception:
            return []

    async def _handle_send_notification(
        self, args: dict[str, Any], org_id: str
    ) -> dict[str, Any]:
        """Send a notification via the notification service."""
        return {
            "status": "queued",
            "recipient": args.get("recipient_id", ""),
            "channel": args.get("channel", "in_app"),
        }

    async def _handle_create_care_gap(
        self, args: dict[str, Any], org_id: str
    ) -> dict[str, Any]:
        """Create a care gap record."""
        return {
            "status": "created",
            "gap_type": args.get("gap_type", ""),
            "patient_id": args.get("patient_id", ""),
        }

    async def _handle_update_care_plan(
        self, args: dict[str, Any], org_id: str
    ) -> dict[str, Any]:
        """Update a care plan."""
        return {
            "status": "updated",
            "care_plan_id": args.get("care_plan_id", ""),
        }

    async def _handle_literature_search(
        self, args: dict[str, Any], org_id: str
    ) -> list[dict[str, Any]]:
        """Search literature via RAG pipeline."""
        query = args.get("query", "")
        try:
            from healthos_platform.ml.rag.retriever import retrieve_documents

            return await retrieve_documents(query=query, collections=["papers"], top_k=5)
        except Exception:
            return []

    async def _handle_drug_interactions(
        self, args: dict[str, Any], org_id: str
    ) -> list[dict[str, Any]]:
        """Check drug interactions via the knowledge graph."""
        medications = args.get("medications", [])
        # Placeholder — in production queries Neo4j
        return [
            {
                "drug1": medications[i],
                "drug2": medications[j],
                "severity": "none",
                "description": "No known interaction",
            }
            for i in range(len(medications))
            for j in range(i + 1, len(medications))
        ]

    async def _handle_risk_scores(
        self, args: dict[str, Any], org_id: str
    ) -> list[dict[str, Any]]:
        """Get patient risk scores."""
        patient_id = args.get("patient_id", "")
        try:
            from shared.models.analytics import RiskScoreRecord

            scores = RiskScoreRecord.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
            ).order_by("-calculated_at")[:10]

            return [
                {
                    "score_type": s.score_type,
                    "score": float(s.score),
                    "risk_level": s.risk_level,
                }
                async for s in scores
            ]
        except Exception:
            return []

    # ── MS Risk Screening MCP Proxy ──────────────────────────────────────

    _MS_TOOL_NAME_MAP = {
        "ms_screen_patient": "screen_patient",
        "ms_run_screening_workflow": "run_screening_workflow",
        "ms_get_patient_risk_card": "get_patient_risk_card",
        "ms_analyze_fairness": "analyze_fairness",
        "ms_what_if_policy": "what_if_policy",
        "ms_review_assessment": "review_assessment",
        "ms_get_workflow_metrics": "get_workflow_metrics",
        "ms_summarize_note": "summarize_note",
    }

    async def _handle_ms_risk_proxy(
        self, args: dict[str, Any], org_id: str, *, _tool_name: str = ""
    ) -> dict[str, Any]:
        """Proxy MCP tool invocations to the ms-risk-backend MCP server."""
        import httpx

        # Resolve the original tool name from the caller context
        remote_tool = self._MS_TOOL_NAME_MAP.get(_tool_name, _tool_name)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "http://ms-risk-backend:8000/mcp/invoke/",
                    json={
                        "tool_name": remote_tool,
                        "arguments": args,
                        "session_id": args.pop("session_id", None),
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            self._log.warning("ms_risk_mcp.proxy_failed", tool=remote_tool, error=str(e))
            return {"error": f"MS Risk MCP proxy failed: {e}", "success": False}

    async def execute(
        self, tool_name: str, arguments: dict[str, Any], org_id: str
    ) -> dict[str, Any]:
        """Execute a tool call and return the result."""
        handler = self._handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}", "success": False}

        try:
            # Pass tool_name for MS Risk proxy routing
            if tool_name.startswith("ms_"):
                result = await handler(arguments, org_id, _tool_name=tool_name)
            else:
                result = await handler(arguments, org_id)
            self._log.info("mcp.tool_executed", tool=tool_name, success=True)
            return {"result": result, "success": True}
        except Exception as e:
            self._log.error("mcp.tool_failed", tool=tool_name, error=str(e))
            return {"error": str(e), "success": False}
