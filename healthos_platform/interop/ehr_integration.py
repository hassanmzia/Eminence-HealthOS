"""
EHR Integration Agent — Tier 5 (Action / Measurement).

Generates FHIR R4 resources for clinical documentation: DiagnosticReport,
CarePlan, DocumentReference (SOAP note). Builds FHIR Bundle for export.
Writes resources to a FHIR server endpoint.

Adapted from InHealth ehr_integration_agent (Tier 5 Action).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.ehr_integration")


class EHRIntegrationAgent(HealthOSAgent):
    """FHIR write-back and clinical documentation generation."""

    def __init__(self) -> None:
        super().__init__(
            name="ehr_integration",
            tier=AgentTier.ACTION,
            description=(
                "Generates FHIR R4 resources (DiagnosticReport, CarePlan, DocumentReference), "
                "SOAP notes, and FHIR Bundles for EHR integration"
            ),
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CLINICAL_SUMMARY, AgentCapability.COMPLIANCE_CHECK]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data

        patient_id = str(agent_input.patient_id or data.get("patient_id", ""))
        fhir_base = os.getenv("FHIR_SERVER_URL", "http://fhir-server:8080/fhir")
        timestamp = datetime.now(timezone.utc).isoformat()

        monitoring: dict[str, Any] = data.get("monitoring_results", {})
        diagnostics: dict[str, Any] = data.get("diagnostic_results", {})
        interventions: list[dict[str, Any]] = data.get("interventions", [])
        risk_scores: dict[str, Any] = data.get("risk_scores", {})

        # 1. Generate SOAP note
        soap_note = await self._generate_soap_note(
            patient_id, monitoring, diagnostics, interventions, risk_scores, timestamp,
        )

        # 2. FHIR DiagnosticReport
        diagnostic_report = self._build_fhir_diagnostic_report(
            patient_id, monitoring, diagnostics, risk_scores, timestamp,
        )

        # 3. FHIR CarePlan
        care_plan = self._build_fhir_care_plan_update(patient_id, interventions, timestamp)

        # 4. FHIR DocumentReference (SOAP note)
        doc_reference = self._build_fhir_document_reference(patient_id, soap_note, timestamp)

        # 5. Write resources to FHIR server
        written_resources: list[dict[str, Any]] = []
        for resource_type, resource_data in [
            ("DiagnosticReport", diagnostic_report),
            ("CarePlan", care_plan),
            ("DocumentReference", doc_reference),
        ]:
            result = await self._write_fhir_resource(fhir_base, resource_type, resource_data)
            written_resources.append({
                "resource_type": resource_type,
                "status": result.get("status", "error"),
                "resource_id": result.get("id", ""),
            })

        # 6. FHIR Bundle for export
        fhir_bundle = self._build_fhir_bundle(
            patient_id, [diagnostic_report, care_plan, doc_reference],
        )

        alerts: list[dict[str, Any]] = []
        write_errors = [r for r in written_resources if r.get("status") == "error"]
        if write_errors:
            alerts.append({
                "severity": "MEDIUM",
                "message": (
                    f"EHR write-back errors: {len(write_errors)} resource(s) failed to write. "
                    "Manual documentation may be required."
                ),
            })

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="ehr_documentation",
            rationale=(
                f"SOAP note generated; {len(written_resources) - len(write_errors)} FHIR resources written; "
                f"{len(write_errors)} errors"
            ),
            confidence=0.90 if not write_errors else 0.70,
            data={
                "soap_note": soap_note,
                "resources_written": len(written_resources) - len(write_errors),
                "write_errors": len(write_errors),
                "written_resources": written_resources,
                "fhir_bundle_size": len(fhir_bundle.get("entry", [])),
                "fhir_bundle": fhir_bundle,
                "timestamp": timestamp,
                "alerts": alerts,
                "recommendations": [
                    "EHR documentation complete. Review clinical note for accuracy before co-signing."
                ],
            },
            requires_hitl=False,
        )

    # -- SOAP note generation -----------------------------------------------------

    async def _generate_soap_note(
        self,
        patient_id: str,
        monitoring: dict,
        diagnostics: dict,
        interventions: list,
        risk_scores: dict,
        timestamp: str,
    ) -> str:
        monitoring_summary = json.dumps(
            {k: v.get("findings", {}) if isinstance(v, dict) else v for k, v in monitoring.items()},
            default=str,
        )[:500]
        diagnostic_summary = json.dumps(
            {k: v.get("findings", {}) if isinstance(v, dict) else v for k, v in diagnostics.items()},
            default=str,
        )[:500]
        risk_summary = json.dumps(risk_scores, default=str)[:300]

        try:
            prompt = (
                f"Generate a SOAP clinical note for patient {patient_id}:\n\n"
                f"Date/Time: {timestamp}\n"
                f"Generated by: HealthOS AI Agent System v1.0\n\n"
                f"Monitoring data: {monitoring_summary}\n"
                f"Diagnostic data: {diagnostic_summary}\n"
                f"Risk assessment: {risk_summary}\n"
                f"Interventions planned: {len(interventions)}\n\n"
                "Create a complete SOAP note:\n"
                "SUBJECTIVE: Patient-reported symptoms\n"
                "OBJECTIVE: Vital signs, lab values, objective measurements\n"
                "ASSESSMENT: Clinical assessment with differential diagnoses\n"
                "PLAN: Specific interventions, medication changes, follow-up\n\n"
                "Format as proper clinical documentation."
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a clinical documentation narrator. Write precise, clinically accurate "
                    "SOAP notes following JCAHO, CMS, and HL7 FHIR R4 standards."
                ),
                temperature=0.3,
                max_tokens=1536,
            ))
            return resp.content
        except Exception as exc:
            logger.warning("SOAP note generation failed: %s", exc)
            return f"[AI-GENERATED NOTE - {timestamp}]\nClinical note generation incomplete. Manual documentation required."

    # -- FHIR resource builders (preserved from source) ----------------------------

    def _build_fhir_diagnostic_report(
        self, patient_id: str, monitoring: dict, diagnostics: dict,
        risk_scores: dict, timestamp: str,
    ) -> dict[str, Any]:
        return {
            "resourceType": "DiagnosticReport",
            "id": str(uuid.uuid4()),
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "AI", "display": "AI Analysis"}]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "81248-8", "display": "Clinical decision support report"}],
                "text": "HealthOS AI Agent Analysis",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": timestamp,
            "issued": timestamp,
            "performer": [{"display": "HealthOS AI Agent System v1.0"}],
            "conclusion": (
                f"AI agent analysis completed. Risk level: "
                f"{risk_scores.get('ml_ensemble_agent', {}).get('findings', {}).get('risk_level', 'UNKNOWN')}."
            ),
            "presentedForm": [{
                "contentType": "application/json",
                "data": json.dumps({
                    "monitoring_summary": {k: v.get("findings", {}) if isinstance(v, dict) else v for k, v in monitoring.items()},
                    "diagnostic_summary": {k: v.get("findings", {}) if isinstance(v, dict) else v for k, v in diagnostics.items()},
                    "risk_assessment": risk_scores,
                }, default=str)[:4096],
            }],
        }

    def _build_fhir_care_plan_update(
        self, patient_id: str, interventions: list[dict[str, Any]], timestamp: str,
    ) -> dict[str, Any]:
        activities = []
        for intervention in interventions[:10]:
            activities.append({
                "detail": {
                    "kind": "ServiceRequest",
                    "status": "scheduled" if not intervention.get("requires_hitl") else "on-hold",
                    "intent": "proposal",
                    "description": str(intervention.get("recommendation_text", intervention))[:200],
                    "doNotPerform": intervention.get("requires_hitl", False),
                },
            })
        return {
            "resourceType": "CarePlan",
            "id": str(uuid.uuid4()),
            "status": "active",
            "intent": "proposal",
            "category": [{"coding": [{"system": "http://loinc.org", "code": "38717-5", "display": "Chronic disease management care plan"}]}],
            "title": "HealthOS AI Care Plan Update",
            "subject": {"reference": f"Patient/{patient_id}"},
            "period": {"start": timestamp},
            "created": timestamp,
            "author": {"display": "HealthOS AI Agent System"},
            "activity": activities,
        }

    def _build_fhir_document_reference(
        self, patient_id: str, soap_note: str, timestamp: str,
    ) -> dict[str, Any]:
        encoded_note = base64.b64encode(soap_note.encode()).decode()
        return {
            "resourceType": "DocumentReference",
            "id": str(uuid.uuid4()),
            "status": "current",
            "type": {
                "coding": [{"system": "http://loinc.org", "code": "34109-9", "display": "Note"}],
                "text": "AI-Generated Clinical Note",
            },
            "category": [{"coding": [{"system": "http://loinc.org", "code": "11488-4", "display": "Consultation note"}]}],
            "subject": {"reference": f"Patient/{patient_id}"},
            "date": timestamp,
            "author": [{"display": "HealthOS AI Agent System v1.0"}],
            "description": "AI-generated clinical summary - requires physician review and co-signature",
            "content": [{"attachment": {"contentType": "text/plain", "data": encoded_note, "creation": timestamp}}],
            "context": {"period": {"start": timestamp}},
        }

    def _build_fhir_bundle(
        self, patient_id: str, resources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "document",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": [
                {"resource": r, "fullUrl": f"urn:uuid:{r.get('id', str(uuid.uuid4()))}"}
                for r in resources
            ],
        }

    async def _write_fhir_resource(
        self, fhir_base: str, resource_type: str, resource_data: dict[str, Any],
    ) -> dict[str, Any]:
        resource_id = resource_data.get("id", str(uuid.uuid4()))
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.put(
                    f"{fhir_base}/{resource_type}/{resource_id}",
                    json=resource_data,
                    headers={
                        "Content-Type": "application/fhir+json",
                        "Accept": "application/fhir+json",
                    },
                )
                if resp.status_code in (200, 201):
                    response_data = resp.json()
                    return {"status": "success", "id": response_data.get("id", resource_id)}
                else:
                    logger.warning("FHIR write failed: %s %s", resp.status_code, resp.text[:200])
                    return {"status": "error", "http_status": resp.status_code}
        except Exception as exc:
            logger.error("FHIR resource write failed for %s: %s", resource_type, exc)
            return {"status": "error", "error": str(exc)}
