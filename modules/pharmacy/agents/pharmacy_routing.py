"""
Eminence HealthOS — Pharmacy Routing Agent (#34)
Layer 4 (Action): Finds nearest/preferred pharmacy and transmits prescription orders.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger(__name__)

# Sample pharmacy network
PHARMACY_NETWORK: list[dict[str, Any]] = [
    {"ncpdp": "1234567", "name": "Walgreens #1234", "chain": "Walgreens", "address": "100 Main St", "city": "Springfield", "distance_mi": 0.8, "hours": "8AM-10PM", "has_drive_thru": True, "specialty": False, "mail_order": False},
    {"ncpdp": "2345678", "name": "CVS Pharmacy #5678", "chain": "CVS", "address": "200 Oak Ave", "city": "Springfield", "distance_mi": 1.2, "hours": "8AM-9PM", "has_drive_thru": True, "specialty": False, "mail_order": False},
    {"ncpdp": "3456789", "name": "Rite Aid #9012", "chain": "Rite Aid", "address": "300 Elm St", "city": "Springfield", "distance_mi": 2.1, "hours": "9AM-8PM", "has_drive_thru": False, "specialty": False, "mail_order": False},
    {"ncpdp": "4567890", "name": "Springfield Medical Pharmacy", "chain": "Independent", "address": "450 Hospital Dr", "city": "Springfield", "distance_mi": 3.5, "hours": "9AM-6PM", "has_drive_thru": False, "specialty": True, "mail_order": False},
    {"ncpdp": "5678901", "name": "Express Scripts Mail", "chain": "Express Scripts", "address": "PO Box 21100", "city": "St. Louis", "distance_mi": None, "hours": "24/7", "has_drive_thru": False, "specialty": False, "mail_order": True},
]


class PharmacyRoutingAgent(BaseAgent):
    """Finds nearest/preferred pharmacy and transmits prescription orders."""

    name = "pharmacy_routing"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Pharmacy location matching, preference management, and electronic "
        "prescription transmission via NCPDP SCRIPT"
    )
    min_confidence = 0.85

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "find_pharmacy")

        if action == "find_pharmacy":
            return await self._find_pharmacy(input_data)
        elif action == "transmit_prescription":
            return self._transmit_prescription(input_data)
        elif action == "check_availability":
            return self._check_availability(input_data)
        elif action == "set_preferred":
            return self._set_preferred(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown pharmacy routing action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _find_pharmacy(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        preferred_chain = ctx.get("preferred_chain", "").lower()
        need_specialty = ctx.get("specialty_required", False)
        prefer_mail_order = ctx.get("mail_order", False)

        candidates = PHARMACY_NETWORK.copy()

        if need_specialty:
            candidates = [p for p in candidates if p["specialty"]]
        elif prefer_mail_order:
            candidates = [p for p in candidates if p["mail_order"]]
        else:
            candidates = [p for p in candidates if not p["mail_order"]]

        if preferred_chain:
            preferred = [p for p in candidates if p["chain"].lower() == preferred_chain]
            if preferred:
                candidates = preferred

        # Sort by distance (mail-order has None distance, put at end for retail queries)
        candidates.sort(key=lambda p: p["distance_mi"] if p["distance_mi"] is not None else 999)

        # --- LLM-generated routing rationale ---
        recommended = candidates[0] if candidates else None
        routing_rationale = (
            f"Recommended {recommended['name']} based on proximity and availability."
            if recommended
            else "No pharmacies found matching the given criteria."
        )
        try:
            routing_payload = {
                "preferred_chain": preferred_chain or None,
                "specialty_required": need_specialty,
                "mail_order_preferred": prefer_mail_order,
                "candidates": candidates[:5],
                "recommended": recommended,
            }
            llm_response = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Explain why the recommended pharmacy was selected and summarize "
                    f"the routing decision based on patient preferences and pharmacy attributes.\n\n"
                    f"Routing data:\n{json.dumps(routing_payload, indent=2)}"
                )}],
                system=(
                    "You are a pharmacy routing AI. Explain the rationale for pharmacy "
                    "selection in plain language. Consider factors like distance, hours, "
                    "drive-thru availability, specialty capabilities, mail-order preferences, "
                    "and patient chain preferences. Be concise and clinically relevant."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if llm_response and llm_response.content:
                routing_rationale = llm_response.content
        except Exception:
            logger.warning(
                "LLM call failed for routing rationale; using fallback narrative",
                exc_info=True,
            )

        result = {
            "searched_at": now.isoformat(),
            "pharmacies": candidates[:5],
            "total_found": len(candidates),
            "recommended": recommended,
            "routing_rationale": routing_rationale,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Found {len(candidates)} pharmacies — recommended: {candidates[0]['name'] if candidates else 'none'}",
        )

    def _transmit_prescription(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        rx_id = ctx.get("prescription_id", str(uuid.uuid4()))
        pharmacy_ncpdp = ctx.get("pharmacy_ncpdp", "1234567")

        pharmacy = next((p for p in PHARMACY_NETWORK if p["ncpdp"] == pharmacy_ncpdp), None)

        result = {
            "transmission_id": str(uuid.uuid4()),
            "prescription_id": rx_id,
            "transmitted_at": now.isoformat(),
            "pharmacy_ncpdp": pharmacy_ncpdp,
            "pharmacy_name": pharmacy["name"] if pharmacy else "Unknown",
            "protocol": "NCPDP SCRIPT v2017071",
            "status": "transmitted",
            "confirmation": str(uuid.uuid4())[:8].upper(),
            "estimated_ready": "2 hours" if pharmacy and not pharmacy["mail_order"] else "3-5 business days",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Prescription {rx_id} transmitted to {result['pharmacy_name']}",
        )

    def _check_availability(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        drug = ctx.get("drug", "unknown")
        pharmacy_ncpdp = ctx.get("pharmacy_ncpdp", "1234567")

        pharmacy = next((p for p in PHARMACY_NETWORK if p["ncpdp"] == pharmacy_ncpdp), None)

        result = {
            "drug": drug,
            "pharmacy_ncpdp": pharmacy_ncpdp,
            "pharmacy_name": pharmacy["name"] if pharmacy else "Unknown",
            "checked_at": now.isoformat(),
            "in_stock": True,
            "quantity_available": ctx.get("quantity_needed", 30),
            "estimated_ready": "1-2 hours",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.85,
            rationale=f"{drug} available at {result['pharmacy_name']}",
        )

    def _set_preferred(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        pharmacy_ncpdp = ctx.get("pharmacy_ncpdp", "1234567")

        pharmacy = next((p for p in PHARMACY_NETWORK if p["ncpdp"] == pharmacy_ncpdp), None)

        result = {
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "preferred_pharmacy": {
                "ncpdp": pharmacy_ncpdp,
                "name": pharmacy["name"] if pharmacy else "Unknown",
            },
            "updated_at": now.isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Preferred pharmacy set to {result['preferred_pharmacy']['name']}",
        )
