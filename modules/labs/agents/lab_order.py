"""
Eminence HealthOS — Lab Order Agent (#37)
Layer 4 (Action): Creates and routes lab orders from care plans and encounters.
"""

from __future__ import annotations

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

# Common lab order panels
LAB_PANELS: dict[str, dict[str, Any]] = {
    "bmp": {"name": "Basic Metabolic Panel", "loinc": "51990-0", "cpt": "80048", "components": ["Glucose", "BUN", "Creatinine", "Sodium", "Potassium", "Chloride", "CO2", "Calcium"], "specimen": "Serum", "turnaround_hours": 4},
    "cmp": {"name": "Comprehensive Metabolic Panel", "loinc": "24323-8", "cpt": "80053", "components": ["Glucose", "BUN", "Creatinine", "Sodium", "Potassium", "Chloride", "CO2", "Calcium", "Total Protein", "Albumin", "Bilirubin", "ALP", "ALT", "AST"], "specimen": "Serum", "turnaround_hours": 4},
    "cbc": {"name": "Complete Blood Count", "loinc": "57021-8", "cpt": "85025", "components": ["WBC", "RBC", "Hemoglobin", "Hematocrit", "Platelets", "MCV", "MCH", "MCHC", "RDW", "Neutrophils", "Lymphocytes", "Monocytes"], "specimen": "Whole Blood", "turnaround_hours": 2},
    "lipid": {"name": "Lipid Panel", "loinc": "57698-3", "cpt": "80061", "components": ["Total Cholesterol", "LDL", "HDL", "Triglycerides", "VLDL"], "specimen": "Serum", "turnaround_hours": 4},
    "hba1c": {"name": "Hemoglobin A1c", "loinc": "4548-4", "cpt": "83036", "components": ["HbA1c"], "specimen": "Whole Blood", "turnaround_hours": 6},
    "tsh": {"name": "Thyroid Stimulating Hormone", "loinc": "3016-3", "cpt": "84443", "components": ["TSH"], "specimen": "Serum", "turnaround_hours": 6},
    "renal": {"name": "Renal Function Panel", "loinc": "24362-6", "cpt": "80069", "components": ["BUN", "Creatinine", "eGFR", "Sodium", "Potassium", "Chloride", "CO2", "Calcium", "Phosphorus", "Albumin"], "specimen": "Serum", "turnaround_hours": 4},
    "hepatic": {"name": "Hepatic Function Panel", "loinc": "24325-3", "cpt": "80076", "components": ["Total Protein", "Albumin", "Total Bilirubin", "Direct Bilirubin", "ALP", "ALT", "AST"], "specimen": "Serum", "turnaround_hours": 4},
    "urinalysis": {"name": "Urinalysis", "loinc": "24357-6", "cpt": "81003", "components": ["Specific Gravity", "pH", "Protein", "Glucose", "Ketones", "Blood", "Leukocyte Esterase", "Nitrites"], "specimen": "Urine", "turnaround_hours": 2},
    "pt_inr": {"name": "PT/INR", "loinc": "5902-2", "cpt": "85610", "components": ["PT", "INR"], "specimen": "Plasma", "turnaround_hours": 2},
}


class LabOrderAgent(BaseAgent):
    """Creates and routes lab orders from care plans and encounters."""

    name = "lab_order"
    tier = AgentTier.ACTION
    version = "1.0.0"
    description = (
        "Lab order generation and routing — creates structured lab orders "
        "with LOINC codes and routes to laboratory systems"
    )
    min_confidence = 0.88

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "create_order")

        if action == "create_order":
            return self._create_order(input_data)
        elif action == "cancel_order":
            return self._cancel_order(input_data)
        elif action == "order_status":
            return self._order_status(input_data)
        elif action == "suggest_panels":
            return self._suggest_panels(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown lab order action: {action}",
                status=AgentStatus.FAILED,
            )

    def _create_order(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        panels_requested = ctx.get("panels", ["bmp"])
        encounter_id = ctx.get("encounter_id")
        priority = ctx.get("priority", "routine")
        fasting = ctx.get("fasting_required", False)
        clinical_notes = ctx.get("clinical_notes", "")

        orders: list[dict[str, Any]] = []
        for panel_key in panels_requested:
            panel = LAB_PANELS.get(panel_key.lower())
            if panel:
                orders.append({
                    "order_id": str(uuid.uuid4()),
                    "panel_key": panel_key,
                    "panel_name": panel["name"],
                    "loinc": panel["loinc"],
                    "cpt": panel["cpt"],
                    "components": panel["components"],
                    "specimen_type": panel["specimen"],
                    "estimated_turnaround_hours": panel["turnaround_hours"],
                })

        result = {
            "lab_order_id": str(uuid.uuid4()),
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "encounter_id": encounter_id,
            "provider_id": ctx.get("provider_id", "unknown"),
            "created_at": now.isoformat(),
            "status": "ordered",
            "priority": priority,
            "fasting_required": fasting,
            "clinical_notes": clinical_notes,
            "orders": orders,
            "total_panels": len(orders),
            "total_components": sum(len(o["components"]) for o in orders),
            "collection_location": ctx.get("collection_location", "in_office"),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.93,
            rationale=f"Lab order created: {len(orders)} panel(s) — {priority} priority",
        )

    def _cancel_order(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        result = {
            "lab_order_id": ctx.get("lab_order_id", "unknown"),
            "status": "cancelled",
            "cancelled_at": now.isoformat(),
            "reason": ctx.get("reason", "Provider cancelled"),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale="Lab order cancelled",
        )

    def _order_status(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        order_id = ctx.get("lab_order_id", "unknown")

        result = {
            "lab_order_id": order_id,
            "status": ctx.get("current_status", "in_progress"),
            "checked_at": now.isoformat(),
            "specimen_collected": True,
            "specimen_received_by_lab": True,
            "processing": True,
            "results_available": False,
            "estimated_completion": "2 hours",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Order {order_id}: {result['status']}",
        )

    def _suggest_panels(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        conditions = [c.lower() for c in ctx.get("conditions", [])]
        medications = [m.lower() for m in ctx.get("medications", [])]

        suggestions: list[dict[str, Any]] = []

        # Condition-based suggestions
        condition_panels = {
            "diabetes": ["hba1c", "bmp", "lipid", "renal"],
            "hypertension": ["bmp", "renal", "lipid"],
            "hypothyroidism": ["tsh"],
            "anemia": ["cbc"],
            "liver disease": ["hepatic", "cmp"],
            "ckd": ["renal", "cbc"],
        }

        for condition in conditions:
            for cond_key, panels in condition_panels.items():
                if cond_key in condition:
                    for panel_key in panels:
                        panel = LAB_PANELS.get(panel_key)
                        if panel and not any(s["panel_key"] == panel_key for s in suggestions):
                            suggestions.append({
                                "panel_key": panel_key,
                                "panel_name": panel["name"],
                                "reason": f"Monitoring for {condition}",
                                "priority": "routine",
                            })

        # Medication-based suggestions
        if any("warfarin" in m for m in medications):
            suggestions.append({"panel_key": "pt_inr", "panel_name": "PT/INR", "reason": "Warfarin monitoring", "priority": "routine"})
        if any("metformin" in m for m in medications):
            if not any(s["panel_key"] == "renal" for s in suggestions):
                suggestions.append({"panel_key": "renal", "panel_name": "Renal Function Panel", "reason": "Metformin renal monitoring", "priority": "routine"})

        result = {
            "suggested_at": now.isoformat(),
            "conditions_evaluated": conditions,
            "medications_evaluated": medications,
            "suggestions": suggestions,
            "total_suggested": len(suggestions),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.87,
            rationale=f"Suggested {len(suggestions)} lab panels based on conditions and medications",
        )
