"""Pharmacy module API routes — prescriptions, interactions, formulary, routing, refills, adherence."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/pharmacy", tags=["pharmacy"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Prescription ──────────────────────────────────────────────────────────


@router.post("/prescriptions/create")
async def create_prescription(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a new e-prescription."""
    from modules.pharmacy.agents.prescription import PrescriptionAgent

    agent = PrescriptionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.prescription.create",
        context={"action": "create_prescription", **body},
    ))
    return output.result


@router.post("/prescriptions/transmit")
async def transmit_prescription(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Sign and transmit a prescription to the pharmacy."""
    from modules.pharmacy.agents.prescription import PrescriptionAgent

    agent = PrescriptionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.prescription.transmit",
        context={"action": "sign_and_transmit", **body},
    ))
    return output.result


@router.get("/prescriptions/history/{patient_id}")
async def prescription_history(
    patient_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get prescription history for a patient."""
    from modules.pharmacy.agents.prescription import PrescriptionAgent

    agent = PrescriptionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id),
        trigger="pharmacy.prescription.history",
        context={"action": "prescription_history"},
    ))
    return output.result


# ── Drug Interaction ──────────────────────────────────────────────────────


@router.post("/interactions/check")
async def check_interactions(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check drug-drug interactions."""
    from modules.pharmacy.agents.drug_interaction import DrugInteractionAgent

    agent = DrugInteractionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.interactions.check",
        context={"action": "check_interactions", **body},
    ))
    return output.result


@router.post("/interactions/safety-check")
async def full_safety_check(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Full medication safety check (interactions, allergies, contraindications)."""
    from modules.pharmacy.agents.drug_interaction import DrugInteractionAgent

    agent = DrugInteractionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.interactions.safety_check",
        context={"action": "full_safety_check", **body},
    ))
    return output.result


# ── Formulary ─────────────────────────────────────────────────────────────


@router.post("/formulary/check")
async def check_coverage(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check formulary coverage for a medication."""
    from modules.pharmacy.agents.formulary import FormularyAgent

    agent = FormularyAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="pharmacy.formulary.check",
        context={"action": "check_coverage", **body},
    ))
    return output.result


@router.post("/formulary/alternatives")
async def suggest_alternatives(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Suggest formulary-preferred alternatives."""
    from modules.pharmacy.agents.formulary import FormularyAgent

    agent = FormularyAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="pharmacy.formulary.alternatives",
        context={"action": "suggest_alternatives", **body},
    ))
    return output.result


@router.post("/formulary/cost-estimate")
async def estimate_cost(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Estimate patient cost for a medication."""
    from modules.pharmacy.agents.formulary import FormularyAgent

    agent = FormularyAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="pharmacy.formulary.cost",
        context={"action": "estimate_cost", **body},
    ))
    return output.result


# ── Pharmacy Routing ──────────────────────────────────────────────────────


@router.post("/routing/find-pharmacy")
async def find_pharmacy(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Find nearby pharmacies in network."""
    from modules.pharmacy.agents.pharmacy_routing import PharmacyRoutingAgent

    agent = PharmacyRoutingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="pharmacy.routing.find",
        context={"action": "find_pharmacy", **body},
    ))
    return output.result


@router.post("/routing/transmit")
async def transmit_to_pharmacy(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Transmit prescription to selected pharmacy."""
    from modules.pharmacy.agents.pharmacy_routing import PharmacyRoutingAgent

    agent = PharmacyRoutingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="pharmacy.routing.transmit",
        context={"action": "transmit_prescription", **body},
    ))
    return output.result


# ── Refill Automation ─────────────────────────────────────────────────────


@router.post("/refills/check")
async def check_refills(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check refill eligibility for a patient's medications."""
    from modules.pharmacy.agents.refill_automation import RefillAutomationAgent

    agent = RefillAutomationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.refills.check",
        context={"action": "check_refills", **body},
    ))
    return output.result


@router.post("/refills/initiate")
async def initiate_refill(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Initiate a prescription refill."""
    from modules.pharmacy.agents.refill_automation import RefillAutomationAgent

    agent = RefillAutomationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.refills.initiate",
        context={"action": "initiate_refill", **body},
    ))
    return output.result


# ── Medication Adherence ──────────────────────────────────────────────────


@router.post("/adherence/calculate")
async def calculate_adherence(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Calculate medication adherence metrics (PDC/MPR)."""
    from modules.pharmacy.agents.medication_adherence import MedicationAdherenceAgent

    agent = MedicationAdherenceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.adherence.calculate",
        context={"action": "calculate_adherence", **body},
    ))
    return output.result


@router.post("/adherence/report")
async def adherence_report(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate medication adherence report."""
    from modules.pharmacy.agents.medication_adherence import MedicationAdherenceAgent

    agent = MedicationAdherenceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="pharmacy.adherence.report",
        context={"action": "adherence_report", **body},
    ))
    return output.result


@router.post("/adherence/interventions")
async def intervention_triggers(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Identify patients needing adherence interventions."""
    from modules.pharmacy.agents.medication_adherence import MedicationAdherenceAgent

    agent = MedicationAdherenceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="pharmacy.adherence.interventions",
        context={"action": "intervention_triggers", **body},
    ))
    return output.result
