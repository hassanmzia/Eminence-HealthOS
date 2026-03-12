"""Tests for the Pharmacy module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"pharmacy.{action}",
        context={"action": action, **extra},
    )


# ── Prescription Agent ───────────────────────────────────────────


class TestPrescriptionAgent:
    @pytest.fixture
    def agent(self):
        from modules.pharmacy.agents.prescription import PrescriptionAgent
        return PrescriptionAgent()

    @pytest.mark.asyncio
    async def test_create_prescription(self, agent):
        out = await agent.run(_input("create_prescription",
            medication="metformin", strength="1000mg", sig="1 tab PO BID",
            quantity=60, refills=3))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "pending_review"
        assert out.result["medication"] == "metformin"

    @pytest.mark.asyncio
    async def test_sign_and_transmit(self, agent):
        out = await agent.run(_input("sign_and_transmit",
            prescription_id="RX-001", provider_id="DR-123"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "transmitted"

    @pytest.mark.asyncio
    async def test_prescription_history(self, agent):
        out = await agent.run(_input("prescription_history"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["prescriptions"]) > 0

    @pytest.mark.asyncio
    async def test_cancel_prescription(self, agent):
        out = await agent.run(_input("cancel_prescription",
            prescription_id="RX-001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Drug Interaction Agent ───────────────────────────────────────


class TestDrugInteractionAgent:
    @pytest.fixture
    def agent(self):
        from modules.pharmacy.agents.drug_interaction import DrugInteractionAgent
        return DrugInteractionAgent()

    @pytest.mark.asyncio
    async def test_check_interactions(self, agent):
        out = await agent.run(_input("check_interactions",
            medications=["warfarin", "aspirin"]))
        assert out.status == AgentStatus.COMPLETED
        assert "interactions" in out.result

    @pytest.mark.asyncio
    async def test_check_allergies(self, agent):
        out = await agent.run(_input("check_allergies",
            medication="amoxicillin",
            allergies=["penicillin"]))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_check_contraindications(self, agent):
        out = await agent.run(_input("check_contraindications",
            medication="metformin", conditions=["ckd_stage_4"]))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_full_safety_check(self, agent):
        out = await agent.run(_input("full_safety_check",
            medications=["warfarin", "aspirin"],
            allergies=["penicillin"],
            conditions=["atrial_fibrillation"]))
        assert out.status == AgentStatus.COMPLETED
        assert "overall_risk" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Formulary Agent ──────────────────────────────────────────────


class TestFormularyAgent:
    @pytest.fixture
    def agent(self):
        from modules.pharmacy.agents.formulary import FormularyAgent
        return FormularyAgent()

    @pytest.mark.asyncio
    async def test_check_coverage(self, agent):
        out = await agent.run(_input("check_coverage",
            medication="metformin"))
        assert out.status == AgentStatus.COMPLETED
        assert "tier" in out.result

    @pytest.mark.asyncio
    async def test_suggest_alternatives(self, agent):
        out = await agent.run(_input("suggest_alternatives",
            medication="jardiance"))
        assert out.status == AgentStatus.COMPLETED
        assert "alternatives" in out.result

    @pytest.mark.asyncio
    async def test_estimate_cost(self, agent):
        out = await agent.run(_input("estimate_cost",
            medication="metformin"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_check_step_therapy(self, agent):
        out = await agent.run(_input("check_step_therapy",
            medication="jardiance"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Pharmacy Routing Agent ───────────────────────────────────────


class TestPharmacyRoutingAgent:
    @pytest.fixture
    def agent(self):
        from modules.pharmacy.agents.pharmacy_routing import PharmacyRoutingAgent
        return PharmacyRoutingAgent()

    @pytest.mark.asyncio
    async def test_find_pharmacy(self, agent):
        out = await agent.run(_input("find_pharmacy",
            zip_code="10001"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["pharmacies"]) > 0

    @pytest.mark.asyncio
    async def test_transmit_prescription(self, agent):
        out = await agent.run(_input("transmit_prescription",
            prescription_id="RX-001", pharmacy_id="PH-001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "transmitted"

    @pytest.mark.asyncio
    async def test_check_availability(self, agent):
        out = await agent.run(_input("check_availability",
            medication="metformin", pharmacy_id="PH-001"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Refill Automation Agent ──────────────────────────────────────


class TestRefillAutomationAgent:
    @pytest.fixture
    def agent(self):
        from modules.pharmacy.agents.refill_automation import RefillAutomationAgent
        return RefillAutomationAgent()

    @pytest.mark.asyncio
    async def test_check_refills(self, agent):
        out = await agent.run(_input("check_refills"))
        assert out.status == AgentStatus.COMPLETED
        assert "medications" in out.result

    @pytest.mark.asyncio
    async def test_initiate_refill(self, agent):
        out = await agent.run(_input("initiate_refill",
            prescription_id="RX-001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] in ("submitted", "pending_approval")

    @pytest.mark.asyncio
    async def test_send_reminder(self, agent):
        out = await agent.run(_input("send_reminder",
            prescription_id="RX-001"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_refill_history(self, agent):
        out = await agent.run(_input("refill_history"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Medication Adherence Agent ───────────────────────────────────


class TestMedicationAdherenceAgent:
    @pytest.fixture
    def agent(self):
        from modules.pharmacy.agents.medication_adherence import MedicationAdherenceAgent
        return MedicationAdherenceAgent()

    @pytest.mark.asyncio
    async def test_calculate_adherence(self, agent):
        out = await agent.run(_input("calculate_adherence"))
        assert out.status == AgentStatus.COMPLETED
        assert "pdc" in out.result or "adherence_metrics" in out.result

    @pytest.mark.asyncio
    async def test_identify_gaps(self, agent):
        out = await agent.run(_input("identify_gaps"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_adherence_report(self, agent):
        out = await agent.run(_input("adherence_report"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_intervention_triggers(self, agent):
        out = await agent.run(_input("intervention_triggers"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Registration & Routing ───────────────────────────────────────


class TestPharmacyRegistration:
    def test_register_pharmacy_agents(self):
        from modules.pharmacy.agents import register_pharmacy_agents
        from healthos_platform.orchestrator.registry import registry
        register_pharmacy_agents()
        for name in ["prescription", "drug_interaction", "formulary",
                      "pharmacy_routing", "refill_automation", "medication_adherence"]:
            assert registry.get(name) is not None, f"Agent '{name}' not registered"

    def test_pharmacy_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        pharmacy_events = [k for k in ROUTING_TABLE if k.startswith("pharmacy.")]
        assert len(pharmacy_events) >= 6, f"Expected >=6 pharmacy routes, got {len(pharmacy_events)}"
