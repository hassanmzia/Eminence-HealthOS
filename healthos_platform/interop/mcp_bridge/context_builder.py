"""
Eminence HealthOS — MCP Context Builder
Aggregates patient data from the Django ORM into MCP-formatted context
for consumption by the MCP server and AI agents.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


class MCPContextBuilder:
    """
    Builds MCP-formatted patient context by querying Django ORM models.
    Aggregates conditions, medications, vitals, allergies, risk scores,
    care gaps, and encounter history.
    """

    async def build_context(
        self, patient_id: str, org_id: str
    ) -> dict[str, Any]:
        """Build the full MCP context for a patient."""
        context = {
            "version": "1.0",
            "patient_id": patient_id,
            "org_id": org_id,
            "demographics": await self._get_demographics(patient_id, org_id),
            "conditions": await self._get_conditions(patient_id, org_id),
            "medications": await self._get_medications(patient_id, org_id),
            "vitals": await self._get_vitals(patient_id, org_id),
            "allergies": await self._get_allergies(patient_id, org_id),
            "risk_scores": await self._get_risk_scores(patient_id, org_id),
            "care_gaps": await self._get_care_gaps(patient_id, org_id),
            "encounters": await self._get_encounters(patient_id, org_id),
        }

        logger.info(
            "mcp.context_built",
            patient_id=patient_id,
            conditions=len(context["conditions"]),
            medications=len(context["medications"]),
        )

        return context

    async def _get_demographics(self, patient_id: str, org_id: str) -> dict[str, Any]:
        """Fetch patient demographics from ORM."""
        try:
            from shared.models.patient import Patient

            patient = await Patient.objects.filter(
                id=patient_id, organization_id=org_id
            ).afirst()

            if not patient:
                return {}

            return {
                "id": str(patient.id),
                "mrn": patient.mrn,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "date_of_birth": str(patient.date_of_birth),
                "gender": patient.gender,
            }
        except Exception as e:
            logger.warning("mcp.demographics_fetch_failed", error=str(e))
            return {}

    async def _get_conditions(self, patient_id: str, org_id: str) -> list[dict[str, Any]]:
        """Fetch active conditions."""
        try:
            from shared.models.clinical import Condition

            conditions = Condition.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
                clinical_status="active",
            )
            return [
                {
                    "id": str(c.id),
                    "code": c.code,
                    "code_system": c.code_system,
                    "display": c.display,
                    "clinical_status": c.clinical_status,
                    "onset_date": str(c.onset_date) if c.onset_date else None,
                }
                async for c in conditions
            ]
        except Exception as e:
            logger.warning("mcp.conditions_fetch_failed", error=str(e))
            return []

    async def _get_medications(self, patient_id: str, org_id: str) -> list[dict[str, Any]]:
        """Fetch active medications."""
        try:
            from shared.models.clinical import MedicationRequest

            meds = MedicationRequest.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
                status="active",
            )
            return [
                {
                    "id": str(m.id),
                    "code": m.code,
                    "display": m.display,
                    "dosage": m.dosage_instruction,
                    "status": m.status,
                }
                async for m in meds
            ]
        except Exception as e:
            logger.warning("mcp.medications_fetch_failed", error=str(e))
            return []

    async def _get_vitals(self, patient_id: str, org_id: str) -> list[dict[str, Any]]:
        """Fetch recent vital signs."""
        try:
            from shared.models.clinical import Observation

            vitals = Observation.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
                category="vital-signs",
            ).order_by("-effective_date")[:50]

            return [
                {
                    "type": v.code_display,
                    "value": v.value,
                    "unit": v.unit,
                    "recorded_at": str(v.effective_date),
                }
                async for v in vitals
            ]
        except Exception as e:
            logger.warning("mcp.vitals_fetch_failed", error=str(e))
            return []

    async def _get_allergies(self, patient_id: str, org_id: str) -> list[dict[str, Any]]:
        """Fetch allergies."""
        try:
            from shared.models.clinical import AllergyIntolerance

            allergies = AllergyIntolerance.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
            )
            return [
                {
                    "substance": a.substance,
                    "reaction": a.reaction,
                    "severity": a.severity,
                }
                async for a in allergies
            ]
        except Exception as e:
            logger.warning("mcp.allergies_fetch_failed", error=str(e))
            return []

    async def _get_risk_scores(self, patient_id: str, org_id: str) -> list[dict[str, Any]]:
        """Fetch latest risk scores."""
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
                    "calculated_at": str(s.calculated_at),
                }
                async for s in scores
            ]
        except Exception as e:
            logger.warning("mcp.risk_scores_fetch_failed", error=str(e))
            return []

    async def _get_care_gaps(self, patient_id: str, org_id: str) -> list[dict[str, Any]]:
        """Fetch open care gaps."""
        try:
            from shared.models.clinical import CareGap

            gaps = CareGap.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
                status="open",
            )
            return [
                {
                    "gap_type": g.gap_type,
                    "description": g.description,
                    "priority": g.priority,
                    "due_date": str(g.due_date) if g.due_date else None,
                }
                async for g in gaps
            ]
        except Exception as e:
            logger.warning("mcp.care_gaps_fetch_failed", error=str(e))
            return []

    async def _get_encounters(self, patient_id: str, org_id: str) -> list[dict[str, Any]]:
        """Fetch recent encounters."""
        try:
            from shared.models.clinical import Encounter

            encounters = Encounter.objects.filter(
                patient_id=patient_id,
                organization_id=org_id,
            ).order_by("-period_start")[:10]

            return [
                {
                    "id": str(e.id),
                    "type": e.encounter_type,
                    "date": str(e.period_start),
                    "provider": str(e.provider_id) if e.provider_id else None,
                }
                async for e in encounters
            ]
        except Exception as e:
            logger.warning("mcp.encounters_fetch_failed", error=str(e))
            return []
