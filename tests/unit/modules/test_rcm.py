"""Tests for the Revenue Cycle Management module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"rcm.{action}",
        context={"action": action, **extra},
    )


# ── Charge Capture Agent ──────────────────────────────────────────


class TestChargeCaptureAgent:
    @pytest.fixture
    def agent(self):
        from modules.rcm.agents.charge_capture import ChargeCaptureAgent
        return ChargeCaptureAgent()

    @pytest.mark.asyncio
    async def test_capture_charges(self, agent):
        em_code = {"code": "99214", "level": 4}
        cpt_codes = [{"cpt": "80048", "description": "BMP"}]
        icd10_codes = [{"code": "I10", "name": "Hypertension"}]
        out = await agent.run(_input("capture_charges",
            encounter_id="ENC-001", em_code=em_code, cpt_codes=cpt_codes, icd10_codes=icd10_codes))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_charges"] >= 2
        assert out.result["status"] == "ready_for_claim"

    @pytest.mark.asyncio
    async def test_estimate_reimbursement(self, agent):
        out = await agent.run(_input("estimate_reimbursement",
            codes=[{"code": "99213"}, {"code": "80048"}], payer_type="commercial"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_estimated"] > 0
        assert out.result["payer_type"] == "commercial"

    @pytest.mark.asyncio
    async def test_missed_charge_scan(self, agent):
        encounters = [
            {"encounter_id": "E1", "has_em_code": False, "labs_ordered": True, "lab_charge_captured": False},
        ]
        out = await agent.run(_input("missed_charge_scan", encounters=encounters))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["findings"]) >= 1

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Claims Optimization Agent ─────────────────────────────────────


class TestClaimsOptimizationAgent:
    @pytest.fixture
    def agent(self):
        from modules.rcm.agents.claims_optimization import ClaimsOptimizationAgent
        return ClaimsOptimizationAgent()

    @pytest.mark.asyncio
    async def test_optimize_clean_claim(self, agent):
        out = await agent.run(_input("optimize_claim",
            claim_id="CLM-001",
            patient_dob="1960-05-15",
            provider_npi="1234567890",
            primary_icd10="I10",
            icd10_codes=[{"code": "I10"}],
            cpt_codes=[{"code": "99213"}],
            eligibility_status="verified"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["is_clean"] is True

    @pytest.mark.asyncio
    async def test_optimize_claim_with_errors(self, agent):
        out = await agent.run(_input("optimize_claim", claim_id="CLM-002"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_batch_scrub(self, agent):
        claims = [
            {"claim_id": "C1", "provider_npi": "123", "primary_icd10": "I10", "eligibility_status": "verified"},
            {"claim_id": "C2"},  # missing fields
        ]
        out = await agent.run(_input("batch_scrub", claims=claims))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_claims"] == 2

    @pytest.mark.asyncio
    async def test_check_bundling(self, agent):
        out = await agent.run(_input("check_bundling",
            cpt_codes=[{"code": "80048"}, {"code": "80053"}]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["has_bundling_issues"] is True

    @pytest.mark.asyncio
    async def test_clean_claim_rate(self, agent):
        out = await agent.run(_input("clean_claim_rate"))
        assert out.status == AgentStatus.COMPLETED
        assert "clean_claim_rate" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Denial Management Agent ───────────────────────────────────────


class TestDenialManagementAgent:
    @pytest.fixture
    def agent(self):
        from modules.rcm.agents.denial_management import DenialManagementAgent
        return DenialManagementAgent()

    @pytest.mark.asyncio
    async def test_analyze_denial(self, agent):
        out = await agent.run(_input("analyze_denial",
            claim_id="CLM-001", denial_code="CO-197", denied_amount=850.00))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["is_appealable"] is True
        assert out.result["denial_code"] == "CO-197"

    @pytest.mark.asyncio
    async def test_analyze_non_appealable(self, agent):
        out = await agent.run(_input("analyze_denial",
            claim_id="CLM-002", denial_code="CO-18", denied_amount=200.00))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["is_appealable"] is False

    @pytest.mark.asyncio
    async def test_generate_appeal(self, agent):
        out = await agent.run(_input("generate_appeal",
            claim_id="CLM-001", denial_code="CO-197", denied_amount=850.00,
            patient_name="John Doe", provider_name="Dr. Smith"))
        assert out.status == AgentStatus.COMPLETED
        assert "appeal_letter" in out.result
        assert out.result["status"] == "ready_to_send"

    @pytest.mark.asyncio
    async def test_denial_trends(self, agent):
        out = await agent.run(_input("denial_trends"))
        assert out.status == AgentStatus.COMPLETED
        assert "top_categories" in out.result
        assert out.result["total_denials"] > 0

    @pytest.mark.asyncio
    async def test_batch_appeal(self, agent):
        denials = [
            {"denial_code": "CO-197", "amount": 500},
            {"denial_code": "CO-18", "amount": 200},  # non-appealable
        ]
        out = await agent.run(_input("batch_appeal", denials=denials))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["appeals_generated"] == 1
        assert out.result["skipped_non_appealable"] == 1

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Revenue Integrity Agent ───────────────────────────────────────


class TestRevenueIntegrityAgent:
    @pytest.fixture
    def agent(self):
        from modules.rcm.agents.revenue_integrity import RevenueIntegrityAgent
        return RevenueIntegrityAgent()

    @pytest.mark.asyncio
    async def test_scan_chart(self, agent):
        out = await agent.run(_input("scan_chart", encounter_id="ENC-001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_findings"] > 0
        assert out.result["total_revenue_opportunity"] > 0

    @pytest.mark.asyncio
    async def test_hcc_gap_analysis(self, agent):
        out = await agent.run(_input("hcc_gap_analysis"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["hcc_gaps"]) > 0
        assert out.result["total_raf_impact"] > 0

    @pytest.mark.asyncio
    async def test_em_level_review(self, agent):
        out = await agent.run(_input("em_level_review"))
        assert out.status == AgentStatus.COMPLETED
        assert "accuracy_rate" in out.result

    @pytest.mark.asyncio
    async def test_revenue_leakage_report(self, agent):
        out = await agent.run(_input("revenue_leakage_report"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_leakage"] > 0
        assert len(out.result["leakage_categories"]) > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Payment Posting Agent ─────────────────────────────────────────


class TestPaymentPostingAgent:
    @pytest.fixture
    def agent(self):
        from modules.rcm.agents.payment_posting import PaymentPostingAgent
        return PaymentPostingAgent()

    @pytest.mark.asyncio
    async def test_post_payment_full(self, agent):
        out = await agent.run(_input("post_payment",
            claim_id="CLM-001", billed_amount=500.00, paid_amount=450.00,
            adjustment_amount=50.00, patient_responsibility=0.00))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["is_paid_in_full"] is True

    @pytest.mark.asyncio
    async def test_post_payment_underpaid(self, agent):
        out = await agent.run(_input("post_payment",
            claim_id="CLM-002", billed_amount=500.00, paid_amount=200.00,
            adjustment_amount=0.00, patient_responsibility=0.00))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["is_underpaid"] is True

    @pytest.mark.asyncio
    async def test_reconcile_era(self, agent):
        out = await agent.run(_input("reconcile_era", era_id="ERA-001"))
        assert out.status == AgentStatus.COMPLETED
        assert "matched" in out.result

    @pytest.mark.asyncio
    async def test_underpayment_check(self, agent):
        out = await agent.run(_input("underpayment_check"))
        assert out.status == AgentStatus.COMPLETED
        assert "payer_summary" in out.result

    @pytest.mark.asyncio
    async def test_ar_aging_report(self, agent):
        out = await agent.run(_input("ar_aging_report"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_ar"] > 0
        assert "aging_buckets" in out.result

    @pytest.mark.asyncio
    async def test_collections_summary(self, agent):
        out = await agent.run(_input("collections_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["collection_rate"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Registration & Routing ─────────────────────────────────────────


class TestRCMRegistration:
    def test_register_agents(self):
        from modules.rcm.agents import register_rcm_agents
        register_rcm_agents()
        from healthos_platform.orchestrator.registry import registry
        assert registry.get("charge_capture") is not None
        assert registry.get("claims_optimization") is not None
        assert registry.get("denial_management") is not None
        assert registry.get("revenue_integrity") is not None
        assert registry.get("payment_posting") is not None

    def test_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        assert "rcm.charges.capture" in ROUTING_TABLE
        assert "rcm.claim.scrub" in ROUTING_TABLE
        assert "rcm.denial.received" in ROUTING_TABLE
        assert "rcm.payment.received" in ROUTING_TABLE
        assert "rcm.integrity.scan" in ROUTING_TABLE
