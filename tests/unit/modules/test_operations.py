"""
Eminence HealthOS — Operations Module Tests
End-to-end tests for all Phase 3 operations agents and infrastructure.
"""

from __future__ import annotations

import uuid

import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.uuid4()


def _input(context: dict, patient_id: uuid.UUID | None = PATIENT_ID) -> AgentInput:
    return AgentInput(
        org_id=ORG_ID,
        patient_id=patient_id,
        trigger="test",
        context=context,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PRIOR AUTHORIZATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestPriorAuthorizationAgent:

    @pytest.fixture
    def agent(self):
        from modules.operations.agents.prior_authorization import PriorAuthorizationAgent
        return PriorAuthorizationAgent()

    @pytest.mark.asyncio
    async def test_evaluate_requires_auth(self, agent):
        output = await agent.run(_input({
            "action": "evaluate",
            "cpt_codes": ["70553"],  # MRI — requires auth
            "diagnosis_codes": ["M54.5"],
            "payer": "aetna",
            "estimated_cost": 2800,
        }))
        assert output.status == AgentStatus.COMPLETED
        assert output.result["requires_prior_auth"] is True
        assert len(output.result["auth_reasons"]) > 0
        assert output.result["matching_category"] == "advanced_imaging"

    @pytest.mark.asyncio
    async def test_evaluate_no_auth_needed(self, agent):
        output = await agent.run(_input({
            "action": "evaluate",
            "cpt_codes": ["99213"],  # Office visit — no auth
            "diagnosis_codes": ["I10"],
            "payer": "aetna",
        }))
        assert output.result["requires_prior_auth"] is False
        assert output.result["recommendation"] == "proceed_without_auth"

    @pytest.mark.asyncio
    async def test_submit_auth(self, agent):
        output = await agent.run(_input({
            "action": "submit",
            "cpt_codes": ["70553"],
            "diagnosis_codes": ["M54.5"],
            "clinical_summary": "Patient presents with chronic lower back pain.",
            "payer": "aetna",
        }))
        assert output.result["status"] == "submitted"
        assert output.result["auth_reference"].startswith("PA-")

    @pytest.mark.asyncio
    async def test_submit_incomplete(self, agent):
        output = await agent.run(_input({
            "action": "submit",
            "payer": "aetna",
        }))
        assert output.result["status"] == "incomplete"
        assert "cpt_codes" in output.result["missing_fields"]

    @pytest.mark.asyncio
    async def test_check_status(self, agent):
        output = await agent.run(_input({
            "action": "check_status",
            "auth_reference": "PA-20260312-001",
        }))
        assert output.result["status"] == "pending_review"

    @pytest.mark.asyncio
    async def test_appeal(self, agent):
        output = await agent.run(_input({
            "action": "appeal",
            "auth_reference": "PA-20260312-001",
            "denial_reason": "Insufficient documentation",
        }))
        assert output.result["appeal_status"] == "initiated"
        assert output.status == AgentStatus.WAITING_HITL


# ═══════════════════════════════════════════════════════════════════════════════
# INSURANCE VERIFICATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestInsuranceVerificationAgent:

    @pytest.fixture
    def agent(self):
        from modules.operations.agents.insurance_verification import InsuranceVerificationAgent
        return InsuranceVerificationAgent()

    @pytest.mark.asyncio
    async def test_verify_eligibility(self, agent):
        output = await agent.run(_input({
            "action": "verify_eligibility",
            "member_id": "MEM-12345",
            "group_number": "GRP-001",
            "payer": "aetna",
        }))
        assert output.result["eligible"] is True
        assert output.result["coverage_status"] == "active"

    @pytest.mark.asyncio
    async def test_verify_missing_fields(self, agent):
        output = await agent.run(_input({
            "action": "verify_eligibility",
        }))
        assert output.result["eligible"] is False
        assert output.result["status"] == "incomplete"

    @pytest.mark.asyncio
    async def test_check_benefits(self, agent):
        output = await agent.run(_input({
            "action": "check_benefits",
            "member_id": "MEM-12345",
            "payer": "aetna",
            "service_type": "specialist",
        }))
        assert output.result["benefits"]["copay"] == 50

    @pytest.mark.asyncio
    async def test_estimate_cost(self, agent):
        output = await agent.run(_input({
            "action": "estimate_cost",
            "payer": "aetna",
            "service_type": "medical",
            "estimated_charges": 500,
        }))
        assert "patient_responsibility" in output.result
        assert output.result["patient_responsibility"] >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# REFERRAL COORDINATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestReferralCoordinationAgent:

    @pytest.fixture
    def agent(self):
        from modules.operations.agents.referral_coordination import ReferralCoordinationAgent
        return ReferralCoordinationAgent()

    @pytest.mark.asyncio
    async def test_create_referral(self, agent):
        output = await agent.run(_input({
            "action": "create",
            "specialty": "cardiology",
            "urgency": "urgent",
            "reason": "Persistent elevated heart rate",
            "diagnosis_codes": ["R00.0"],
        }))
        assert output.result["referral_id"].startswith("REF-")
        assert output.result["specialty"] == "cardiology"
        assert output.result["target_days"] <= 3  # urgent cardiology

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, agent):
        output = await agent.run(_input({"action": "create"}))
        assert output.result["status"] == "incomplete"

    @pytest.mark.asyncio
    async def test_match_specialist(self, agent):
        output = await agent.run(_input({
            "action": "match_specialist",
            "specialty": "orthopedics",
            "urgency": "routine",
        }))
        assert output.result["matches_found"] > 0
        assert output.result["specialists"][0]["accepting_patients"] is True

    @pytest.mark.asyncio
    async def test_track_referral(self, agent):
        output = await agent.run(_input({
            "action": "track",
            "referral_id": "REF-20260310-001",
        }))
        assert output.result["status"] == "pending_scheduling"

    @pytest.mark.asyncio
    async def test_close_referral(self, agent):
        output = await agent.run(_input({
            "action": "close",
            "referral_id": "REF-20260310-001",
            "outcome": "completed",
        }))
        assert output.result["status"] == "closed"
        assert output.result["outcome"] == "completed"


# ═══════════════════════════════════════════════════════════════════════════════
# TASK ORCHESTRATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestTaskOrchestrationAgent:

    @pytest.fixture
    def agent(self):
        from modules.operations.agents.task_orchestration import TaskOrchestrationAgent
        return TaskOrchestrationAgent()

    @pytest.mark.asyncio
    async def test_create_task(self, agent):
        output = await agent.run(_input({
            "action": "create_task",
            "task_type": "prior_auth",
            "priority": "urgent",
            "title": "Submit prior auth for MRI",
        }))
        assert output.result["task_id"].startswith("TASK-")
        assert output.result["priority"] == "urgent"
        assert output.result["sla_hours"] == 4

    @pytest.mark.asyncio
    async def test_create_workflow(self, agent):
        output = await agent.run(_input({
            "action": "create_workflow",
            "workflow_type": "new_patient_intake",
            "priority": "normal",
        }))
        assert output.result["workflow_id"].startswith("WF-")
        assert output.result["total_steps"] == 4

    @pytest.mark.asyncio
    async def test_check_sla(self, agent):
        output = await agent.run(_input({"action": "check_sla"}))
        assert "sla_compliance_rate" in output.result
        assert output.result["total_open_tasks"] > 0

    @pytest.mark.asyncio
    async def test_get_queue(self, agent):
        output = await agent.run(_input({
            "action": "get_queue",
            "assignee": "billing_team",
        }))
        assert "tasks" in output.result
        assert output.result["total_tasks"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING READINESS AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestBillingReadinessAgent:

    @pytest.fixture
    def agent(self):
        from modules.operations.agents.billing_readiness import BillingReadinessAgent
        return BillingReadinessAgent()

    @pytest.mark.asyncio
    async def test_validate_complete_encounter(self, agent):
        output = await agent.run(_input({
            "action": "validate",
            "encounter_type": "office_visit",
            "encounter": {
                "patient_id": str(PATIENT_ID),
                "provider_id": str(uuid.uuid4()),
                "date_of_service": "2026-03-12",
                "cpt_codes": ["99214"],
                "diagnosis_codes": ["I10"],
                "place_of_service": "11",
                "modifier": "25",
                "clinical_notes": "Follow-up for hypertension management.",
                "provider_signature": True,
                "review_of_systems": True,
            },
        }))
        assert output.result["completeness_score"] == 1.0
        assert output.result["is_billing_ready"] is True

    @pytest.mark.asyncio
    async def test_validate_incomplete_encounter(self, agent):
        output = await agent.run(_input({
            "action": "validate",
            "encounter_type": "office_visit",
            "encounter": {
                "patient_id": str(PATIENT_ID),
            },
        }))
        assert output.result["completeness_score"] < 1.0
        assert len(output.result["missing_fields"]) > 0

    @pytest.mark.asyncio
    async def test_check_coding(self, agent):
        output = await agent.run(_input({
            "action": "check_coding",
            "cpt_codes": ["99214"],
            "diagnosis_codes": ["I10"],
            "em_level": "99214",
            "documentation_elements": 4,
            "visit_time_minutes": 25,
        }))
        assert output.result["is_accurate"] is True
        assert output.result["coding_accuracy_score"] > 0.8

    @pytest.mark.asyncio
    async def test_prepare_claim(self, agent):
        output = await agent.run(_input({
            "action": "prepare_claim",
            "payer": "aetna",
            "cpt_codes": ["99214"],
            "diagnosis_codes": ["I10"],
            "provider_npi": "1234567890",
            "date_of_service": "2026-03-12",
        }))
        assert output.result["claim_id"].startswith("CLM-")
        assert output.result["status"] == "prepared"

    @pytest.mark.asyncio
    async def test_billing_audit(self, agent):
        output = await agent.run(_input({"action": "audit", "period": "weekly"}))
        assert output.result["billing_rate"] > 0
        assert "top_issues" in output.result


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW ANALYTICS AGENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkflowAnalyticsAgent:

    @pytest.fixture
    def agent(self):
        from modules.operations.agents.workflow_analytics import WorkflowAnalyticsAgent
        return WorkflowAnalyticsAgent()

    @pytest.mark.asyncio
    async def test_summary(self, agent):
        output = await agent.run(_input({"action": "summary", "period": "weekly"}))
        assert "workflows" in output.result
        assert "tasks" in output.result
        assert "billing" in output.result

    @pytest.mark.asyncio
    async def test_bottleneck_analysis(self, agent):
        output = await agent.run(_input({"action": "bottleneck_analysis"}))
        assert output.result["total_identified"] > 0
        assert output.result["estimated_total_time_savings_hours"] > 0

    @pytest.mark.asyncio
    async def test_kpi_report(self, agent):
        output = await agent.run(_input({"action": "kpi_report"}))
        assert "efficiency_metrics" in output.result
        assert "quality_metrics" in output.result
        assert "financial_metrics" in output.result

    @pytest.mark.asyncio
    async def test_trend_analysis(self, agent):
        output = await agent.run(_input({"action": "trend_analysis"}))
        assert len(output.result["weekly_data"]) > 0
        assert len(output.result["insights"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkflowEngine:

    @pytest.fixture
    def engine(self):
        from modules.operations.workflow_engine import WorkflowEngine
        return WorkflowEngine()

    def test_create_workflow_from_template(self, engine):
        wf = engine.create_workflow("specialist_referral", str(ORG_ID), str(PATIENT_ID))
        assert wf.workflow_type == "specialist_referral"
        assert len(wf.steps) == 5
        assert wf.steps[0].status.value == "ready"
        assert wf.steps[1].status.value == "pending"  # depends on step 0

    def test_create_workflow_unknown_type(self, engine):
        with pytest.raises(ValueError):
            engine.create_workflow("nonexistent", str(ORG_ID))

    def test_get_ready_steps(self, engine):
        wf = engine.create_workflow("specialist_referral", str(ORG_ID))
        ready = engine.get_ready_steps(wf.workflow_id)
        assert len(ready) == 1
        assert ready[0].name == "Verify Specialist Coverage"

    def test_step_lifecycle(self, engine):
        wf = engine.create_workflow("specialist_referral", str(ORG_ID))
        ready = engine.get_ready_steps(wf.workflow_id)
        step = ready[0]

        # Start step
        started = engine.start_step(wf.workflow_id, step.step_id)
        assert started.status.value == "in_progress"

        # Complete step
        completed = engine.complete_step(wf.workflow_id, step.step_id, {"verified": True})
        assert completed.status.value == "completed"

        # Next steps should now be ready
        new_ready = engine.get_ready_steps(wf.workflow_id)
        assert len(new_ready) >= 1

    def test_workflow_summary(self, engine):
        wf = engine.create_workflow("claim_submission", str(ORG_ID))
        summary = engine.get_workflow_summary(wf.workflow_id)
        assert summary["total_steps"] == 5
        assert summary["progress"] == 0

    def test_list_templates(self, engine):
        templates = engine.available_templates
        assert len(templates) >= 5
        names = [t["type"] for t in templates]
        assert "claim_submission" in names
        assert "specialist_referral" in names


# ═══════════════════════════════════════════════════════════════════════════════
# PAYER CONNECTOR
# ═══════════════════════════════════════════════════════════════════════════════


class TestPayerConnector:

    @pytest.fixture
    def registry(self):
        from modules.operations.payer_connector import PayerConnectorRegistry
        return PayerConnectorRegistry()

    def test_list_payers(self, registry):
        payers = registry.list_payers()
        assert len(payers) >= 7
        names = [p["payer_id"] for p in payers]
        assert "aetna" in names
        assert "medicare" in names

    @pytest.mark.asyncio
    async def test_eligibility_check(self, registry):
        from modules.operations.payer_connector import EligibilityRequest

        connector = registry.get("aetna")
        assert connector is not None

        response = await connector.check_eligibility(EligibilityRequest(
            member_id="MEM-12345",
            group_number="GRP-001",
        ))
        assert response.eligible is True
        assert response.plan_type == "PPO"

    @pytest.mark.asyncio
    async def test_submit_claim(self, registry):
        from modules.operations.payer_connector import ClaimSubmission

        connector = registry.get("unitedhealth")
        response = await connector.submit_claim(ClaimSubmission(
            claim_id="CLM-TEST-001",
            patient_member_id="MEM-12345",
            provider_npi="1234567890",
            date_of_service="2026-03-12",
            diagnosis_codes=["I10"],
            total_charges=450,
        ))
        assert response.status == "accepted"
        assert response.payer_claim_number.startswith("PCN-")

    @pytest.mark.asyncio
    async def test_claim_status(self, registry):
        connector = registry.get("cigna")
        status = await connector.check_claim_status("CLM-TEST-001")
        assert status["status"] == "in_process"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestOperationsRegistration:

    def test_register_all_agents(self):
        from healthos_platform.orchestrator.registry import AgentRegistry

        registry = AgentRegistry()
        registry.reset()

        from modules.operations.agents import register_operations_agents
        register_operations_agents()

        assert registry.agent_count == 6
        assert registry.get("prior_authorization") is not None
        assert registry.get("insurance_verification") is not None
        assert registry.get("referral_coordination") is not None
        assert registry.get("task_orchestration") is not None
        assert registry.get("billing_readiness") is not None
        assert registry.get("workflow_analytics") is not None

        registry.reset()

    def test_routing_table_has_operations_events(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE

        assert "operations.prior_auth.evaluate" in ROUTING_TABLE
        assert "operations.insurance.verify" in ROUTING_TABLE
        assert "operations.referral.create" in ROUTING_TABLE
        assert "operations.workflow.create" in ROUTING_TABLE
        assert "billing.encounter.validate" in ROUTING_TABLE
        assert "billing.claim.prepare" in ROUTING_TABLE
