"""
End-to-end Operations workflow tests.

Full multi-agent workflow lifecycle tests covering:
  - New patient intake workflow
  - Claim submission workflow
  - Specialist referral workflow
  - Direct agent tests (prior auth, insurance, billing)
  - SLA violation detection
  - Step failure and retry resilience

Each test exercises the WorkflowEngine and/or operations agents via their
``process()`` method, passing realistic operational context and asserting on
both structure and semantics of every output.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from healthos_platform.agents.types import AgentInput, AgentOutput, AgentStatus
from modules.operations.workflow_engine import (
    StepStatus,
    WorkflowEngine,
    WorkflowStatus,
)

# Register operations fixtures so pytest discovers them from the companion module.
pytest_plugins = ["tests.e2e.conftest_operations"]

from tests.e2e.conftest_operations import make_ops_input  # noqa: E402

# ── Agent imports ────────────────────────────────────────────────────────────

from modules.operations.agents.prior_authorization import PriorAuthorizationAgent
from modules.operations.agents.insurance_verification import InsuranceVerificationAgent
from modules.operations.agents.billing_readiness import BillingReadinessAgent
from modules.operations.agents.referral_coordination import ReferralCoordinationAgent
from modules.operations.agents.task_orchestration import TaskOrchestrationAgent


# ── Helpers ──────────────────────────────────────────────────────────────────


def _assert_valid_output(output: AgentOutput, *, agent_name: str) -> None:
    """Common assertions that every agent output must satisfy."""
    assert isinstance(output, AgentOutput)
    assert output.agent_name == agent_name
    assert output.status in (
        AgentStatus.COMPLETED,
        AgentStatus.WAITING_HITL,
    )
    assert 0.0 <= output.confidence <= 1.0
    assert isinstance(output.result, dict)
    assert output.rationale  # must have a non-empty rationale


def _execute_ready_steps(
    engine: WorkflowEngine,
    workflow_id: str,
    step_outputs: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """
    Drive one round of workflow execution: get ready steps, start each,
    and complete each with a default (or supplied) output.

    Returns the list of step names that were executed in this round.
    """
    ready = engine.get_ready_steps(workflow_id)
    executed_names: list[str] = []

    for step in ready:
        started = engine.start_step(workflow_id, step.step_id)
        assert started is not None, f"Failed to start step {step.name}"
        assert started.status == StepStatus.IN_PROGRESS

        output = (step_outputs or {}).get(step.name, {"status": "ok"})
        completed = engine.complete_step(workflow_id, step.step_id, output)
        assert completed is not None, f"Failed to complete step {step.name}"
        assert completed.status == StepStatus.COMPLETED
        executed_names.append(step.name)

    return executed_names


def _run_workflow_to_completion(
    engine: WorkflowEngine,
    workflow_id: str,
    step_outputs: dict[str, dict[str, Any]] | None = None,
    max_rounds: int = 20,
) -> list[list[str]]:
    """
    Drive a workflow to completion by repeatedly executing ready steps.
    Returns a list-of-lists where each inner list is the step names executed
    in that round (useful for verifying dependency ordering).
    """
    rounds: list[list[str]] = []
    for _ in range(max_rounds):
        executed = _execute_ready_steps(engine, workflow_id, step_outputs)
        if not executed:
            break
        rounds.append(executed)
    return rounds


# ═════════════════════════════════════════════════════════════════════════════
# 1. test_new_patient_intake_workflow — Full intake workflow
# ═════════════════════════════════════════════════════════════════════════════


class TestNewPatientIntakeWorkflow:
    """Full new-patient intake workflow from template."""

    def test_new_patient_intake_workflow(self, workflow_engine, org_id, patient_id):
        """
        Create workflow from new_patient_intake template, execute each step,
        and verify dependency ordering and successful completion.

        Template steps:
          0. Verify Insurance                        (ready immediately)
          1. Check Benefits          (depends on 0)
          2. Collect Demographics                    (ready immediately)
          3. Schedule Initial Visit   (depends on 0, 2)
          4. Assign Care Team         (depends on 3)
        """
        wf = workflow_engine.create_workflow(
            workflow_type="new_patient_intake",
            org_id=str(org_id),
            patient_id=str(patient_id),
            priority="normal",
            context={"source": "e2e_test"},
        )

        assert wf.status == WorkflowStatus.ACTIVE
        assert len(wf.steps) == 5
        assert wf.workflow_type == "new_patient_intake"
        assert wf.patient_id == str(patient_id)

        # ── Round 1: steps with no dependencies should be ready ──────────
        round1 = _execute_ready_steps(workflow_engine, wf.workflow_id)
        assert "Verify Insurance" in round1
        assert "Collect Demographics" in round1
        # Dependent steps must NOT have executed yet
        assert "Check Benefits" not in round1
        assert "Schedule Initial Visit" not in round1
        assert "Assign Care Team" not in round1

        # ── Round 2: Check Benefits (depends on Verify Insurance) and
        #             Schedule Initial Visit (depends on Verify Insurance + Collect Demographics)
        round2 = _execute_ready_steps(workflow_engine, wf.workflow_id)
        assert "Check Benefits" in round2
        assert "Schedule Initial Visit" in round2
        assert "Assign Care Team" not in round2

        # ── Round 3: Assign Care Team (depends on Schedule Initial Visit)
        round3 = _execute_ready_steps(workflow_engine, wf.workflow_id)
        assert "Assign Care Team" in round3

        # ── Workflow should now be completed ─────────────────────────────
        final_wf = workflow_engine.get_workflow(wf.workflow_id)
        assert final_wf.status == WorkflowStatus.COMPLETED
        assert final_wf.completed_at is not None
        assert all(
            s.status == StepStatus.COMPLETED for s in final_wf.steps
        )

        # Verify summary
        summary = workflow_engine.get_workflow_summary(wf.workflow_id)
        assert summary["progress"] == 1.0
        assert summary["step_counts"]["completed"] == 5


# ═════════════════════════════════════════════════════════════════════════════
# 2. test_claim_submission_workflow — Full billing workflow
# ═════════════════════════════════════════════════════════════════════════════


class TestClaimSubmissionWorkflow:
    """Full claim submission workflow from template."""

    def test_claim_submission_workflow(self, workflow_engine, org_id, patient_id):
        """
        Template steps:
          0. Validate Encounter                     (ready immediately)
          1. Check Coding            (depends on 0)
          2. Verify Insurance                       (ready immediately)
          3. Check Prior Auth        (depends on 2)
          4. Prepare Claim           (depends on 0, 1, 2)
        """
        claim_output = {
            "Prepare Claim": {
                "claim_id": "CLM-20260314-TEST",
                "claim_type": "837P",
                "status": "prepared",
                "payer": "BlueCross",
                "total_charges": 450,
                "service_lines": [
                    {"line_number": 1, "cpt_code": "99214", "charge_amount": 250},
                    {"line_number": 2, "cpt_code": "83036", "charge_amount": 200},
                ],
            },
        }

        wf = workflow_engine.create_workflow(
            workflow_type="claim_submission",
            org_id=str(org_id),
            patient_id=str(patient_id),
        )

        assert wf.status == WorkflowStatus.ACTIVE
        assert len(wf.steps) == 5

        # ── Round 1: Validate Encounter and Verify Insurance (no deps) ───
        round1 = _execute_ready_steps(workflow_engine, wf.workflow_id)
        assert "Validate Encounter" in round1
        assert "Verify Insurance" in round1
        assert "Check Coding" not in round1
        assert "Prepare Claim" not in round1

        # ── Round 2: Check Coding (needs Validate Encounter),
        #             Check Prior Auth (needs Verify Insurance) ───────────
        round2 = _execute_ready_steps(workflow_engine, wf.workflow_id)
        assert "Check Coding" in round2
        assert "Check Prior Auth" in round2
        # Prepare Claim still blocked — needs 0, 1, and 2 completed
        assert "Prepare Claim" not in round2

        # ── Round 3: Prepare Claim (all dependencies met) ────────────────
        round3 = _execute_ready_steps(
            workflow_engine, wf.workflow_id, claim_output
        )
        assert "Prepare Claim" in round3

        # ── Verify claim output stored on the step ───────────────────────
        final_wf = workflow_engine.get_workflow(wf.workflow_id)
        assert final_wf.status == WorkflowStatus.COMPLETED

        claim_step = [s for s in final_wf.steps if s.name == "Prepare Claim"][0]
        assert claim_step.output["claim_id"] == "CLM-20260314-TEST"
        assert claim_step.output["claim_type"] == "837P"
        assert claim_step.output["status"] == "prepared"
        assert "service_lines" in claim_step.output
        assert claim_step.output["total_charges"] == 450

        # Coding validation must have run before claim preparation
        coding_step = [s for s in final_wf.steps if s.name == "Check Coding"][0]
        claim_step = [s for s in final_wf.steps if s.name == "Prepare Claim"][0]
        assert coding_step.completed_at <= claim_step.completed_at


# ═════════════════════════════════════════════════════════════════════════════
# 3. test_specialist_referral_workflow — Full referral flow
# ═════════════════════════════════════════════════════════════════════════════


class TestSpecialistReferralWorkflow:
    """Full specialist referral workflow from template."""

    def test_specialist_referral_workflow(self, workflow_engine, org_id, patient_id):
        """
        Template steps:
          0. Verify Specialist Coverage              (ready immediately)
          1. Create Referral          (depends on 0)
          2. Match Specialist         (depends on 1)
          3. Schedule Specialist Visit (depends on 2)
          4. Send Clinical Summary    (depends on 1)
        """
        specialist_output = {
            "Match Specialist": {
                "specialists": [
                    {
                        "provider_id": "PROV-CAR-001",
                        "name": "Dr. Smith (Cardiology)",
                        "specialty": "cardiology",
                        "in_network": True,
                        "accepting_patients": True,
                    },
                ],
                "matches_found": 1,
            },
        }

        wf = workflow_engine.create_workflow(
            workflow_type="specialist_referral",
            org_id=str(org_id),
            patient_id=str(patient_id),
            priority="urgent",
        )

        assert wf.status == WorkflowStatus.ACTIVE
        assert wf.priority == "urgent"
        assert len(wf.steps) == 5

        rounds = _run_workflow_to_completion(
            workflow_engine, wf.workflow_id, specialist_output
        )

        # Round 1: only Verify Specialist Coverage (no deps)
        assert rounds[0] == ["Verify Specialist Coverage"]

        # Round 2: Create Referral (depends on step 0)
        assert rounds[1] == ["Create Referral"]

        # Round 3: Match Specialist (depends on 1) + Send Clinical Summary (depends on 1)
        assert "Match Specialist" in rounds[2]
        assert "Send Clinical Summary" in rounds[2]

        # Round 4: Schedule Specialist Visit (depends on 2)
        assert "Schedule Specialist Visit" in rounds[3]

        # Verify specialist match output is stored
        final_wf = workflow_engine.get_workflow(wf.workflow_id)
        assert final_wf.status == WorkflowStatus.COMPLETED

        match_step = [s for s in final_wf.steps if s.name == "Match Specialist"][0]
        assert match_step.output["matches_found"] == 1
        assert match_step.output["specialists"][0]["provider_id"] == "PROV-CAR-001"
        assert match_step.output["specialists"][0]["in_network"] is True


# ═════════════════════════════════════════════════════════════════════════════
# 4. test_prior_auth_agent_evaluate — Direct agent test
# ═════════════════════════════════════════════════════════════════════════════


class TestPriorAuthAgent:
    """Direct tests for PriorAuthorizationAgent evaluate action."""

    @pytest.mark.asyncio
    async def test_prior_auth_agent_evaluate(
        self, org_id, patient_id, sample_prior_auth_context
    ):
        """
        Run PriorAuthorizationAgent with evaluate action and assert:
        - Clinical necessity scoring is present and reasonable
        - Documentation checklist is generated
        - Auth requirement is correctly identified for imaging CPT codes
        """
        agent = PriorAuthorizationAgent()
        agent_input = make_ops_input(
            org_id,
            patient_id,
            sample_prior_auth_context,
            trigger="prior_auth.evaluate",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="prior_authorization")

        result = output.result

        # CPT 70553 and 72148 are in advanced_imaging category
        assert result["requires_prior_auth"] is True
        assert result["matching_category"] == "advanced_imaging"
        assert len(result["auth_reasons"]) >= 1
        assert any("70553" in r or "72148" in r for r in result["auth_reasons"])

        # Clinical necessity score: with 2 dx codes + 2 cpt codes + long notes => high
        score = result["clinical_necessity_score"]
        assert 0.0 <= score <= 1.0
        assert score >= 0.8, (
            f"Expected high clinical necessity score with full context, got {score}"
        )

        # Documentation checklist should include base docs + advanced_imaging docs
        docs = result["required_documents"]
        assert len(docs) >= 4  # at least base documents
        assert any("medical necessity" in d.lower() for d in docs)
        assert any("imaging" in d.lower() for d in docs)

        # Recommendation should be to submit auth
        assert result["recommendation"] == "submit_auth"
        assert result["payer"] == "aetna"
        assert "evaluated_at" in result

    @pytest.mark.asyncio
    async def test_prior_auth_no_auth_needed(self, org_id, patient_id):
        """Simple office visit CPT should not require prior auth."""
        agent = PriorAuthorizationAgent()
        ctx = {
            "action": "evaluate",
            "cpt_codes": ["99213"],
            "diagnosis_codes": ["J06.9"],
            "payer": "default",
            "estimated_cost": 200,
        }
        agent_input = make_ops_input(org_id, patient_id, ctx)
        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="prior_authorization")
        assert output.result["requires_prior_auth"] is False
        assert output.result["recommendation"] == "proceed_without_auth"


# ═════════════════════════════════════════════════════════════════════════════
# 5. test_insurance_verification_agent — Direct agent test
# ═════════════════════════════════════════════════════════════════════════════


class TestInsuranceVerificationAgent:
    """Direct tests for InsuranceVerificationAgent."""

    @pytest.mark.asyncio
    async def test_insurance_verification_agent(
        self, org_id, patient_id, sample_insurance_context
    ):
        """
        Run InsuranceVerificationAgent with verify_eligibility action and
        assert eligibility result with coverage details.
        """
        agent = InsuranceVerificationAgent()
        agent_input = make_ops_input(
            org_id,
            patient_id,
            sample_insurance_context,
            trigger="insurance.verify",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="insurance_verification")

        result = output.result

        # Core eligibility assertions
        assert result["eligible"] is True
        assert result["coverage_status"] == "active"
        assert result["payer"] == "BlueCross"
        assert result["member_id"] == "MEM-987654321"
        assert result["group_number"] == "GRP-12345"

        # Plan details
        assert result["plan_name"]  # non-empty
        assert result["plan_type"] == "PPO"
        assert result["effective_date"]
        assert result["subscriber_relationship"] == "self"

        # Verification metadata
        assert "verified_at" in result
        assert result["date_of_service"] == "2026-03-15T09:00:00Z"

        # Confidence should be high for active coverage
        assert output.confidence >= 0.90

    @pytest.mark.asyncio
    async def test_insurance_verification_missing_fields(self, org_id, patient_id):
        """Verify agent reports missing required fields gracefully."""
        agent = InsuranceVerificationAgent()
        ctx = {
            "action": "verify_eligibility",
            # Omit member_id and payer
        }
        agent_input = make_ops_input(org_id, patient_id, ctx)
        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="insurance_verification")
        assert output.result["eligible"] is False
        assert output.result["status"] == "incomplete"
        assert "member_id" in output.result["missing_fields"]
        assert "payer" in output.result["missing_fields"]

    @pytest.mark.asyncio
    async def test_insurance_check_benefits(self, org_id, patient_id):
        """Verify benefits check returns copay, deductible, and coinsurance."""
        agent = InsuranceVerificationAgent()
        ctx = {
            "action": "check_benefits",
            "member_id": "MEM-111222333",
            "payer": "Cigna",
            "service_type": "specialist",
            "cpt_codes": ["99214"],
        }
        agent_input = make_ops_input(org_id, patient_id, ctx)
        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="insurance_verification")
        result = output.result
        benefits = result["benefits"]

        assert result["service_type"] == "specialist"
        assert "copay" in benefits
        assert "deductible_remaining" in benefits
        assert "coinsurance_pct" in benefits
        assert "out_of_pocket_max_remaining" in benefits
        assert isinstance(benefits["copay"], (int, float))
        assert benefits["copay"] == 50  # specialist copay from simulated data


# ═════════════════════════════════════════════════════════════════════════════
# 6. test_billing_readiness_agent — Direct agent test
# ═════════════════════════════════════════════════════════════════════════════


class TestBillingReadinessAgent:
    """Direct tests for BillingReadinessAgent validate and check_coding."""

    @pytest.mark.asyncio
    async def test_billing_readiness_validate(
        self, org_id, patient_id, sample_billing_context
    ):
        """
        Run BillingReadinessAgent with validate action and assert encounter
        validation results including completeness and readiness.
        """
        agent = BillingReadinessAgent()
        agent_input = make_ops_input(
            org_id,
            patient_id,
            sample_billing_context,
            trigger="billing.validate",
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="billing_readiness")

        result = output.result

        assert result["encounter_type"] == "office_visit"
        assert result["is_billing_ready"] is True
        assert result["completeness_score"] == 1.0
        assert result["recommendation"] == "ready_to_bill"
        assert len(result["missing_fields"]) == 0
        assert len(result["documentation_issues"]) == 0
        assert "validated_at" in result

    @pytest.mark.asyncio
    async def test_billing_readiness_incomplete_encounter(self, org_id, patient_id):
        """Validate that missing fields are correctly reported."""
        agent = BillingReadinessAgent()
        ctx = {
            "action": "validate",
            "encounter_type": "office_visit",
            "encounter": {
                "patient_id": "PT-001",
                # Missing provider_id, date_of_service, cpt_codes, etc.
            },
        }
        agent_input = make_ops_input(org_id, patient_id, ctx)
        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="billing_readiness")
        result = output.result

        assert result["is_billing_ready"] is False
        assert result["completeness_score"] < 1.0
        assert len(result["missing_fields"]) > 0
        assert result["recommendation"] == "needs_review"

    @pytest.mark.asyncio
    async def test_billing_check_coding(self, org_id, patient_id):
        """
        Run BillingReadinessAgent with check_coding action and assert
        CPT/ICD compatibility check produces accuracy score and issues.
        """
        agent = BillingReadinessAgent()
        ctx = {
            "action": "check_coding",
            "cpt_codes": ["99214", "83036"],
            "diagnosis_codes": ["E11.65"],
            "em_level": "99214",
            "documentation_elements": 4,
            "visit_time_minutes": 25,
        }
        agent_input = make_ops_input(
            org_id, patient_id, ctx, trigger="billing.check_coding"
        )

        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="billing_readiness")

        result = output.result

        assert "coding_accuracy_score" in result
        assert 0.0 <= result["coding_accuracy_score"] <= 1.0
        assert "is_accurate" in result
        assert result["cpt_codes"] == ["99214", "83036"]
        assert result["diagnosis_codes"] == ["E11.65"]
        assert result["em_level"] == "99214"
        assert "checked_at" in result
        # With compatible codes and sufficient documentation, should have
        # high accuracy (99214 and 83036 are compatible with E11)
        assert result["coding_accuracy_score"] >= 0.70

    @pytest.mark.asyncio
    async def test_billing_check_coding_incompatible(self, org_id, patient_id):
        """Verify coding check detects incompatible CPT/ICD combinations."""
        agent = BillingReadinessAgent()
        ctx = {
            "action": "check_coding",
            "cpt_codes": ["94010"],  # Spirometry — not compatible with E11 (diabetes)
            "diagnosis_codes": ["E11.65"],
        }
        agent_input = make_ops_input(org_id, patient_id, ctx)
        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="billing_readiness")
        result = output.result

        assert len(result["issues"]) > 0
        assert any("94010" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_billing_prepare_claim(self, org_id, patient_id):
        """Verify claim preparation produces required CMS-1500 fields."""
        agent = BillingReadinessAgent()
        ctx = {
            "action": "prepare_claim",
            "encounter_id": "ENC-20260314-001",
            "payer": "Aetna",
            "cpt_codes": ["99214", "83036"],
            "diagnosis_codes": ["E11.65", "I10"],
            "provider_npi": "1234567890",
            "date_of_service": "2026-03-14",
            "charges": [
                {"amount": 250, "cpt_code": "99214"},
                {"amount": 85, "cpt_code": "83036"},
            ],
        }
        agent_input = make_ops_input(org_id, patient_id, ctx)
        output = await agent.process(agent_input)

        _assert_valid_output(output, agent_name="billing_readiness")
        result = output.result

        assert result["status"] == "prepared"
        assert result["claim_id"].startswith("CLM-")
        assert result["claim_type"] == "837P"
        assert result["payer"] == "Aetna"
        assert result["provider_npi"] == "1234567890"
        assert len(result["service_lines"]) == 2
        assert result["total_charges"] == 335
        assert result["diagnosis_codes"] == ["E11.65", "I10"]
        assert "prepared_at" in result


# ═════════════════════════════════════════════════════════════════════════════
# 7. test_workflow_sla_violations — SLA tracking
# ═════════════════════════════════════════════════════════════════════════════


class TestWorkflowSLAViolations:
    """SLA violation detection tests."""

    def test_workflow_sla_violations(self, workflow_engine, org_id):
        """
        Create a workflow with tight SLAs, manipulate timestamps to simulate
        overdue steps, and verify SLA violations are detected.
        """
        # Create workflow with steps that have small SLA windows
        custom_steps = [
            {
                "name": "Urgent Verification",
                "agent_name": "insurance_verification",
                "action": "verify_eligibility",
                "sla_hours": 0.001,  # ~3.6 seconds — will be overdue immediately
            },
            {
                "name": "Urgent Auth Check",
                "agent_name": "prior_authorization",
                "action": "check_status",
                "sla_hours": 0.001,
            },
        ]

        wf = workflow_engine.create_workflow(
            workflow_type="custom_sla_test",
            org_id=str(org_id),
            priority="urgent",
            custom_steps=custom_steps,
        )

        assert wf.status == WorkflowStatus.ACTIVE

        # Backdate workflow creation so SLAs are already violated
        wf.created_at = datetime.now(timezone.utc) - timedelta(hours=1)

        # Steps should be READY (no dependencies)
        ready = workflow_engine.get_ready_steps(wf.workflow_id)
        assert len(ready) == 2

        # Start one step to make it IN_PROGRESS (also SLA-eligible)
        workflow_engine.start_step(wf.workflow_id, ready[0].step_id)

        # Check for SLA violations
        violations = workflow_engine.check_sla_violations(str(org_id))

        assert len(violations) >= 2, (
            f"Expected at least 2 SLA violations, got {len(violations)}"
        )

        for v in violations:
            assert v["workflow_id"] == wf.workflow_id
            assert v["hours_overdue"] > 0
            assert v["sla_hours"] == 0.001
            assert v["priority"] == "urgent"
            assert "step_name" in v
            assert "step_id" in v

    def test_no_sla_violations_when_on_track(self, workflow_engine, org_id):
        """Verify no violations are reported when steps are within SLA."""
        wf = workflow_engine.create_workflow(
            workflow_type="new_patient_intake",
            org_id=str(org_id),
            priority="normal",
        )

        # SLAs are 2-24 hours; workflow just created, so nothing is overdue
        violations = workflow_engine.check_sla_violations(str(org_id))
        assert len(violations) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 8. test_workflow_step_failure_and_retry — Resilience
# ═════════════════════════════════════════════════════════════════════════════


class TestWorkflowStepFailureAndRetry:
    """Workflow step failure, retry mechanism, and max-retry failure tests."""

    def test_workflow_step_failure_and_retry(self, workflow_engine, org_id):
        """
        Create a workflow, fail a step, assert retry mechanism works,
        fail past max retries, and assert workflow is marked as failed.
        """
        wf = workflow_engine.create_workflow(
            workflow_type="claim_submission",
            org_id=str(org_id),
        )

        # Get the first ready step (Validate Encounter)
        ready = workflow_engine.get_ready_steps(wf.workflow_id)
        first_step = ready[0]
        assert first_step.name == "Validate Encounter"
        assert first_step.max_retries == 2

        # Start the step
        started = workflow_engine.start_step(wf.workflow_id, first_step.step_id)
        assert started.status == StepStatus.IN_PROGRESS

        # ── Fail attempt 1: should trigger retry (back to READY) ─────────
        failed = workflow_engine.fail_step(
            wf.workflow_id, first_step.step_id, "Connection timeout to billing system"
        )
        assert failed is not None
        assert failed.retry_count == 1
        assert failed.status == StepStatus.READY  # retried, back to ready
        assert "Retry 1/2" in failed.error

        # Workflow should still be active
        wf_check = workflow_engine.get_workflow(wf.workflow_id)
        assert wf_check.status == WorkflowStatus.ACTIVE

        # ── Retry: start and fail again (attempt 2) ──────────────────────
        started2 = workflow_engine.start_step(wf.workflow_id, first_step.step_id)
        assert started2.status == StepStatus.IN_PROGRESS

        failed2 = workflow_engine.fail_step(
            wf.workflow_id, first_step.step_id, "Service unavailable"
        )
        assert failed2.retry_count == 2
        assert failed2.status == StepStatus.READY  # still within max_retries
        assert "Retry 2/2" in failed2.error

        # Workflow should still be active after second retry
        wf_check2 = workflow_engine.get_workflow(wf.workflow_id)
        assert wf_check2.status == WorkflowStatus.ACTIVE

        # ── Final failure: attempt 3 exceeds max_retries=2 ───────────────
        started3 = workflow_engine.start_step(wf.workflow_id, first_step.step_id)
        assert started3.status == StepStatus.IN_PROGRESS

        failed3 = workflow_engine.fail_step(
            wf.workflow_id, first_step.step_id, "Persistent system failure"
        )
        assert failed3.retry_count == 3
        assert failed3.status == StepStatus.FAILED
        assert failed3.error == "Persistent system failure"

        # ── Workflow should now be marked as failed ───────────────────────
        final_wf = workflow_engine.get_workflow(wf.workflow_id)
        assert final_wf.status == WorkflowStatus.FAILED

        # Summary should reflect the failure
        summary = workflow_engine.get_workflow_summary(wf.workflow_id)
        assert summary["status"] == "failed"
        assert summary["step_counts"].get("failed", 0) >= 1

    def test_step_retry_then_success(self, workflow_engine, org_id):
        """
        Verify a step can fail once, be retried, and then succeed normally.
        """
        custom_steps = [
            {
                "name": "Flaky Step",
                "agent_name": "insurance_verification",
                "action": "verify_eligibility",
                "max_retries": 2,
            },
            {
                "name": "Next Step",
                "agent_name": "task_orchestration",
                "action": "create_task",
                "depends_on_index": [0],
            },
        ]

        wf = workflow_engine.create_workflow(
            workflow_type="retry_test",
            org_id=str(org_id),
            custom_steps=custom_steps,
        )

        ready = workflow_engine.get_ready_steps(wf.workflow_id)
        step = ready[0]
        assert step.name == "Flaky Step"

        # Start and fail once
        workflow_engine.start_step(wf.workflow_id, step.step_id)
        failed = workflow_engine.fail_step(
            wf.workflow_id, step.step_id, "Transient error"
        )
        assert failed.status == StepStatus.READY
        assert failed.retry_count == 1

        # Retry: start and succeed
        workflow_engine.start_step(wf.workflow_id, step.step_id)
        completed = workflow_engine.complete_step(
            wf.workflow_id, step.step_id, {"eligible": True}
        )
        assert completed.status == StepStatus.COMPLETED

        # Next Step should now be ready
        ready_after = workflow_engine.get_ready_steps(wf.workflow_id)
        assert len(ready_after) == 1
        assert ready_after[0].name == "Next Step"

        # Complete the second step to finish workflow
        workflow_engine.start_step(wf.workflow_id, ready_after[0].step_id)
        workflow_engine.complete_step(
            wf.workflow_id, ready_after[0].step_id, {"task_id": "T-001"}
        )

        final_wf = workflow_engine.get_workflow(wf.workflow_id)
        assert final_wf.status == WorkflowStatus.COMPLETED


# ═════════════════════════════════════════════════════════════════════════════
# 9. Referral coordination agent — direct agent test
# ═════════════════════════════════════════════════════════════════════════════


class TestReferralCoordinationAgent:
    """Direct tests for ReferralCoordinationAgent."""

    @pytest.mark.asyncio
    async def test_referral_create_and_match(
        self, org_id, patient_id, sample_referral_context
    ):
        """
        Create a referral, then match a specialist. Assert the full pipeline
        produces valid referral IDs and specialist matches.
        """
        agent = ReferralCoordinationAgent()

        # ── Create referral ──────────────────────────────────────────────
        create_input = make_ops_input(
            org_id, patient_id, sample_referral_context, trigger="referral.create"
        )
        create_out = await agent.process(create_input)

        _assert_valid_output(create_out, agent_name="referral_coordination")
        result = create_out.result

        assert result["referral_id"].startswith("REF-")
        assert result["specialty"] == "cardiology"
        assert result["urgency"] == "urgent"
        assert result["status"] == "created"
        assert result["insurance_verified"] is True
        assert result["insurance_warning"] is False
        # Urgent cardiology: base 7 days * 0.3 = 2.1 -> 2 days
        assert result["target_days"] <= 7
        assert "target_appointment_date" in result
        assert len(result["next_steps"]) >= 2

        # ── Match specialist ─────────────────────────────────────────────
        match_ctx = {
            "action": "match_specialist",
            "specialty": "cardiology",
            "urgency": "urgent",
            "insurance_network": "BlueCross PPO",
        }
        match_input = make_ops_input(
            org_id, patient_id, match_ctx, trigger="referral.match"
        )
        match_out = await agent.process(match_input)

        _assert_valid_output(match_out, agent_name="referral_coordination")
        match_result = match_out.result

        assert match_result["matches_found"] >= 1
        assert match_result["specialty"] == "cardiology"

        # Validate each specialist in the results
        for spec in match_result["specialists"]:
            assert "provider_id" in spec
            assert spec["provider_id"]  # non-empty
            assert spec["specialty"] == "cardiology"
            assert spec["in_network"] is True
            assert spec["accepting_patients"] is True
            assert "next_available" in spec


# ═════════════════════════════════════════════════════════════════════════════
# 10. Workflow engine — template listing and edge cases
# ═════════════════════════════════════════════════════════════════════════════


class TestWorkflowEngineEdgeCases:
    """Additional workflow engine tests for coverage."""

    def test_available_templates(self, workflow_engine):
        """Verify all expected templates are listed."""
        templates = workflow_engine.available_templates
        template_types = {t["type"] for t in templates}

        expected = {
            "new_patient_intake",
            "surgical_prep",
            "specialist_referral",
            "discharge_follow_up",
            "claim_submission",
        }
        assert template_types == expected

        for t in templates:
            assert t["steps"] > 0
            assert t["name"]  # non-empty

    def test_unknown_workflow_type_raises(self, workflow_engine, org_id):
        """Creating a workflow with an unknown type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown workflow type"):
            workflow_engine.create_workflow(
                workflow_type="nonexistent_workflow",
                org_id=str(org_id),
            )

    def test_list_workflows_by_org(self, workflow_engine, org_id):
        """Verify listing workflows filters by org and status."""
        org = str(org_id)
        workflow_engine.create_workflow(
            workflow_type="new_patient_intake", org_id=org
        )
        workflow_engine.create_workflow(
            workflow_type="claim_submission", org_id=org
        )
        workflow_engine.create_workflow(
            workflow_type="specialist_referral", org_id="OTHER-ORG"
        )

        all_wfs = workflow_engine.list_workflows(org)
        assert len(all_wfs) == 2

        active_wfs = workflow_engine.list_workflows(org, status="active")
        assert len(active_wfs) == 2

        completed_wfs = workflow_engine.list_workflows(org, status="completed")
        assert len(completed_wfs) == 0

    def test_get_nonexistent_workflow(self, workflow_engine):
        """Getting a nonexistent workflow returns None."""
        assert workflow_engine.get_workflow("WF-does-not-exist") is None
        assert workflow_engine.get_workflow_summary("WF-does-not-exist") is None

    def test_get_ready_steps_inactive_workflow(self, workflow_engine, org_id):
        """Ready steps for a failed/completed workflow should return empty."""
        wf = workflow_engine.create_workflow(
            workflow_type="new_patient_intake", org_id=str(org_id)
        )
        # Manually mark as completed to test guard
        wf.status = WorkflowStatus.COMPLETED
        ready = workflow_engine.get_ready_steps(wf.workflow_id)
        assert ready == []
