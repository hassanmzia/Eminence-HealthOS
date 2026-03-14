"""
End-to-end Telehealth encounter workflow tests.

Full workflow: session creation -> symptom check -> visit preparation
             -> clinical note -> follow-up plan -> visit summary.

Each test exercises one or more telehealth agents via their ``process()``
method, passing realistic clinical context and asserting on both the
structure and semantics of every AgentOutput.
"""

from __future__ import annotations

import uuid

import pytest

from healthos_platform.agents.types import AgentInput, AgentOutput, AgentStatus

from tests.e2e.conftest_telehealth import (
    make_communication_input,
    make_escalation_input,
    make_medication_review_input,
    make_scheduling_input,
    make_session_input,
    make_symptom_input,
    make_telehealth_input,
)


# ── Agent imports ────────────────────────────────────────────────────────────

from modules.telehealth.agents.session_manager import SessionManagerAgent
from modules.telehealth.agents.symptom_checker import SymptomCheckerAgent
from modules.telehealth.agents.visit_preparation import VisitPreparationAgent
from modules.telehealth.agents.clinical_note import ClinicalNoteAgent
from modules.telehealth.agents.follow_up_plan import FollowUpPlanAgent
from modules.telehealth.agents.visit_summarizer import VisitSummarizerAgent
from modules.telehealth.agents.escalation_routing import EscalationRoutingAgent
from modules.telehealth.agents.medication_review import MedicationReviewAgent
from modules.telehealth.agents.scheduling import SchedulingAgent
from modules.telehealth.agents.patient_communication import PatientCommunicationAgent


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


# ═════════════════════════════════════════════════════════════════════════════
# 1. Full encounter workflow — happy path
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_full_encounter_workflow(
    org_id, patient_id, sample_session_context, sample_clinical_context
):
    """
    Complete happy-path telehealth encounter:
      SessionManager -> SymptomChecker -> VisitPreparation
      -> ClinicalNote -> FollowUpPlan -> VisitSummarizer

    Each step produces valid output with required fields, and context flows
    downstream so that later agents can reference earlier results.
    """

    # ── Step 1: Create session ───────────────────────────────────────────
    session_agent = SessionManagerAgent()
    session_input = make_session_input(
        org_id,
        patient_id,
        visit_type=sample_session_context["visit_type"],
        urgency=sample_session_context["urgency"],
    )
    session_out = await session_agent.process(session_input)

    _assert_valid_output(session_out, agent_name="session_manager")
    assert session_out.result["session_id"]
    assert session_out.result["status"] == "waiting"
    assert session_out.result["visit_type"] == "follow_up"
    assert session_out.result["urgency"] == "routine"
    assert "estimated_wait_minutes" in session_out.result

    session_id = session_out.result["session_id"]

    # ── Step 2: Symptom check ────────────────────────────────────────────
    symptom_agent = SymptomCheckerAgent()
    symptom_input = make_symptom_input(
        org_id,
        patient_id,
        symptoms=sample_session_context["symptoms"],
        severity_rating=5,
    )
    symptom_out = await symptom_agent.process(symptom_input)

    _assert_valid_output(symptom_out, agent_name="symptom_checker")
    assessment = symptom_out.result
    assert assessment["chief_complaint"] == "headache"
    assert len(assessment["symptoms"]) == 3
    assert len(assessment["systems_affected"]) > 0
    assert assessment["urgency"] in ("routine", "same_day", "urgent", "emergency")
    assert assessment["recommended_visit_type"]
    # No red flags for these symptoms
    assert len(assessment["red_flags"]) == 0
    assert symptom_out.status == AgentStatus.COMPLETED

    # ── Step 3: Visit preparation ────────────────────────────────────────
    visit_prep_agent = VisitPreparationAgent()
    visit_prep_ctx = {
        **sample_clinical_context,
        "encounter_reason": sample_session_context["chief_complaint"],
    }
    visit_prep_input = make_telehealth_input(
        org_id, patient_id, visit_prep_ctx, trigger="visit.prepare"
    )
    visit_prep_out = await visit_prep_agent.process(visit_prep_input)

    _assert_valid_output(visit_prep_out, agent_name="visit_preparation")
    pre_visit = visit_prep_out.result["pre_visit_summary"]
    assert pre_visit["patient"]["name"] == "Jane Doe"
    assert pre_visit["encounter_reason"] == "headache"
    assert len(pre_visit["presenting_symptoms"]) == 3
    assert len(pre_visit["current_medications"]) > 0
    assert pre_visit["allergies"] == ["penicillin"]

    # ── Step 4: Clinical note ────────────────────────────────────────────
    clinical_note_agent = ClinicalNoteAgent()
    note_ctx = {
        "symptoms": sample_clinical_context["symptoms"],
        "vitals": sample_clinical_context["vitals"],
        "assessment": sample_clinical_context["assessment"],
        "plan": sample_clinical_context["plan"],
        "medications": sample_clinical_context["medications"],
        "encounter_type": "telehealth",
        "prior_outputs": [
            {
                "agent_name": "symptom_checker",
                "rationale": symptom_out.rationale,
            },
        ],
    }
    note_input = make_telehealth_input(
        org_id, patient_id, note_ctx, trigger="note.generate"
    )
    note_out = await clinical_note_agent.process(note_input)

    _assert_valid_output(note_out, agent_name="clinical_note")
    note_result = note_out.result
    assert "soap_note" in note_result
    assert "icd10_suggestions" in note_result
    assert note_result["note_status"] == "draft"

    # ── Step 5: Follow-up plan ───────────────────────────────────────────
    follow_up_agent = FollowUpPlanAgent()
    follow_up_ctx = {
        "conditions": sample_clinical_context["conditions"],
        "symptoms": sample_clinical_context["symptoms"],
        "medications": sample_clinical_context["medications"],
        "plan": sample_clinical_context["plan"],
        "encounter_type": "telehealth",
        "risk_assessments": [],
    }
    follow_up_input = make_telehealth_input(
        org_id, patient_id, follow_up_ctx, trigger="follow_up.plan"
    )
    follow_up_out = await follow_up_agent.process(follow_up_input)

    _assert_valid_output(follow_up_out, agent_name="follow_up_plan")
    plan = follow_up_out.result["follow_up_plan"]
    assert plan["follow_up_days"] > 0
    assert plan["monitoring_cadence"]["vitals_frequency"]
    assert len(plan["action_items"]) > 0
    assert len(plan["escalation_criteria"]) > 0

    # ── Step 6: Visit summary ────────────────────────────────────────────
    summarizer_agent = VisitSummarizerAgent()
    summary_ctx = {
        "symptoms": sample_clinical_context["symptoms"],
        "vitals": sample_clinical_context["vitals"],
        "assessment": sample_clinical_context["assessment"],
        "plan": sample_clinical_context["plan"],
        "medications": sample_clinical_context["medications"],
        "session": {"session_id": session_id},
        "prior_outputs": [],
    }
    summary_input = make_telehealth_input(
        org_id, patient_id, summary_ctx, trigger="visit.summarize"
    )
    summary_out = await summarizer_agent.process(summary_input)

    _assert_valid_output(summary_out, agent_name="visit_summarizer")
    summary_result = summary_out.result
    assert "soap_note" in summary_result
    assert "after_visit_summary" in summary_result
    assert summary_result["session_id"] == session_id
    avs = summary_result["after_visit_summary"]
    assert "your_plan" in avs
    assert "when_to_seek_care" in avs
    assert len(avs["medications"]) > 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. Urgent escalation workflow — emergency routing
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_urgent_escalation_workflow(org_id, patient_id):
    """
    Emergency scenario: red-flag symptoms trigger escalation.

    1. Create session with urgency=emergency.
    2. Symptom check with chest_pain + shortness_of_breath (red flags).
    3. Escalation routing detects critical severity.
    4. Assert escalation targets emergency department / physician,
       HITL is required, and response window is tight.
    """

    # ── Step 1: Emergency session ────────────────────────────────────────
    session_agent = SessionManagerAgent()
    session_input = make_session_input(
        org_id, patient_id, urgency="urgent", visit_type="follow_up"
    )
    session_out = await session_agent.process(session_input)

    _assert_valid_output(session_out, agent_name="session_manager")
    assert session_out.result["urgency"] == "urgent"
    assert session_out.result["estimated_wait_minutes"] == 5

    # ── Step 2: Symptom check with red-flag symptoms ─────────────────────
    symptom_agent = SymptomCheckerAgent()
    red_flag_symptoms = ["chest_pain", "shortness_of_breath", "dizziness"]
    symptom_input = make_symptom_input(
        org_id,
        patient_id,
        symptoms=red_flag_symptoms,
        severity_rating=9,
    )
    symptom_out = await symptom_agent.process(symptom_input)

    _assert_valid_output(symptom_out, agent_name="symptom_checker")
    assessment = symptom_out.result
    assert len(assessment["red_flags"]) >= 2, (
        f"Expected at least 2 red flags, got {assessment['red_flags']}"
    )
    assert assessment["urgency"] == "emergency"
    assert assessment["recommended_visit_type"] == "emergency_department"
    assert symptom_out.status == AgentStatus.WAITING_HITL
    assert symptom_out.requires_hitl is True

    # ── Step 3: Escalation routing ───────────────────────────────────────
    escalation_agent = EscalationRoutingAgent()
    escalation_input = make_escalation_input(
        org_id,
        patient_id,
        severity="high",
        systems_affected=assessment["systems_affected"],
        red_flags=assessment["red_flags"],
        risk_score=0.85,
        urgency="emergency",
    )
    escalation_out = await escalation_agent.process(escalation_input)

    _assert_valid_output(escalation_out, agent_name="escalation_routing")
    escalation = escalation_out.result

    # Red flags override severity to critical
    assert escalation["severity"] == "critical"
    assert escalation["target_role"] == "physician"
    assert escalation["alert_type"] == "emergency"
    assert escalation["response_window_minutes"] == 15
    assert escalation["notify_supervisor"] is True
    assert escalation_out.status == AgentStatus.WAITING_HITL
    assert escalation_out.requires_hitl is True


# ═════════════════════════════════════════════════════════════════════════════
# 3. Medication review — drug interaction detection
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_medication_review_in_encounter(org_id, patient_id, sample_medication_list):
    """
    Provide a medication list with known interaction pairs (warfarin + aspirin)
    and verify the MedicationReviewAgent detects them.
    """

    med_agent = MedicationReviewAgent()
    med_input = make_medication_review_input(
        org_id,
        patient_id,
        medications=sample_medication_list,
        conditions=["chronic_kidney_disease"],
    )
    med_out = await med_agent.process(med_input)

    _assert_valid_output(med_out, agent_name="medication_review")
    result = med_out.result

    # Warfarin + aspirin is a known high-severity interaction
    assert result["total_findings"] > 0, "Should detect at least one finding"
    assert len(result["interactions"]) >= 1, (
        f"Expected warfarin-aspirin interaction, got: {result['interactions']}"
    )

    # Verify the warfarin-aspirin interaction specifically
    interaction_pairs = {
        (i["drug_a"], i["drug_b"]) for i in result["interactions"]
    }
    assert ("warfarin", "aspirin") in interaction_pairs or (
        "aspirin", "warfarin"
    ) in interaction_pairs, (
        f"Warfarin-aspirin interaction not found in: {interaction_pairs}"
    )

    # Verify severity classification
    warfarin_aspirin = [
        i
        for i in result["interactions"]
        if {i["drug_a"], i["drug_b"]} == {"warfarin", "aspirin"}
    ]
    assert warfarin_aspirin[0]["severity"] == "high"

    # Contraindication: metformin with chronic kidney disease
    assert len(result["contraindications"]) >= 1, (
        f"Expected metformin-CKD contraindication, got: {result['contraindications']}"
    )
    ckd_contras = [c for c in result["contraindications"] if c["condition"] == "chronic_kidney_disease"]
    assert len(ckd_contras) >= 1

    # Critical findings should trigger HITL
    assert result["has_critical_findings"] is True
    assert med_out.status == AgentStatus.WAITING_HITL
    assert med_out.requires_hitl is True


# ═════════════════════════════════════════════════════════════════════════════
# 4. Scheduling follow-up — post-visit scheduling
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_scheduling_follow_up(org_id, patient_id, sample_clinical_context):
    """
    After an encounter, generate a follow-up plan and then schedule
    the appointment. Assert that the SchedulingAgent produces valid
    slots and the timing aligns with the follow-up plan.
    """

    # ── First: generate follow-up plan to determine timing ───────────────
    follow_up_agent = FollowUpPlanAgent()
    follow_up_ctx = {
        "conditions": sample_clinical_context["conditions"],
        "symptoms": sample_clinical_context["symptoms"],
        "medications": sample_clinical_context["medications"],
        "plan": sample_clinical_context["plan"],
        "risk_assessments": [{"score": 0.3, "risk_level": "moderate"}],
    }
    follow_up_input = make_telehealth_input(
        org_id, patient_id, follow_up_ctx, trigger="follow_up.plan"
    )
    follow_up_out = await follow_up_agent.process(follow_up_input)

    _assert_valid_output(follow_up_out, agent_name="follow_up_plan")
    plan = follow_up_out.result["follow_up_plan"]
    follow_up_days = plan["follow_up_days"]
    assert follow_up_days > 0

    # ── Second: schedule the follow-up ───────────────────────────────────
    scheduling_agent = SchedulingAgent()
    sched_input = make_scheduling_input(
        org_id,
        patient_id,
        action="follow_up",
        visit_type="follow_up",
        follow_up_days=follow_up_days,
    )
    sched_out = await scheduling_agent.process(sched_input)

    _assert_valid_output(sched_out, agent_name="scheduling")
    sched_result = sched_out.result

    assert sched_result["status"] in ("scheduled", "pending")
    assert sched_result["visit_type"] == "follow_up"
    assert sched_result["follow_up_target_date"], "Should have a target date"
    assert sched_result["duration_minutes"] > 0

    # ── Third: schedule a standard appointment ───────────────────────────
    sched_input_std = make_scheduling_input(
        org_id,
        patient_id,
        action="schedule",
        visit_type="follow_up",
        urgency="routine",
    )
    sched_out_std = await scheduling_agent.process(sched_input_std)

    _assert_valid_output(sched_out_std, agent_name="scheduling")
    std_result = sched_out_std.result

    assert std_result["status"] == "scheduled"
    assert std_result["scheduled_at"]
    assert len(std_result["available_slots"]) > 0, "Should provide available slot options"
    assert std_result["duration_minutes"] > 0


# ═════════════════════════════════════════════════════════════════════════════
# 5. Patient communication workflow — post-visit messaging
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_patient_communication_workflow(org_id, patient_id, sample_clinical_context):
    """
    After a visit summary is generated, the PatientCommunicationAgent
    sends follow-up instructions via appropriate channels.
    """

    # ── Generate visit summary first ─────────────────────────────────────
    summarizer_agent = VisitSummarizerAgent()
    summary_ctx = {
        "symptoms": sample_clinical_context["symptoms"],
        "vitals": sample_clinical_context["vitals"],
        "assessment": sample_clinical_context["assessment"],
        "plan": sample_clinical_context["plan"],
        "medications": sample_clinical_context["medications"],
        "session": {"session_id": str(uuid.uuid4())},
        "prior_outputs": [],
    }
    summary_input = make_telehealth_input(
        org_id, patient_id, summary_ctx, trigger="visit.summarize"
    )
    summary_out = await summarizer_agent.process(summary_input)
    _assert_valid_output(summary_out, agent_name="visit_summarizer")

    avs = summary_out.result["after_visit_summary"]

    # ── Send follow-up instructions ──────────────────────────────────────
    comm_agent = PatientCommunicationAgent()
    instructions = "; ".join(avs["your_plan"])
    comm_input = make_communication_input(
        org_id,
        patient_id,
        message_type="follow_up_instructions",
        urgency="routine",
        patient_name="Jane Doe",
        template_vars={"instructions": instructions},
    )
    comm_out = await comm_agent.process(comm_input)

    _assert_valid_output(comm_out, agent_name="patient_communication")
    comm_result = comm_out.result

    assert comm_result["message_type"] == "follow_up_instructions"
    assert len(comm_result["channels"]) > 0, "Should select at least one channel"
    assert "in_app" in comm_result["channels"], "Routine messages should include in_app"
    assert len(comm_result["communication_plan"]) > 0

    # Message should contain the patient name and instructions
    message = comm_result["message"]
    assert "Jane Doe" in message
    assert len(message) > 20, "Message should be substantive"

    # Each entry in the communication plan should be queued
    for entry in comm_result["communication_plan"]:
        assert entry["status"] == "queued"
        assert entry["channel"] in comm_result["channels"]
        assert entry["scheduled_at"]

    # ── Send urgent communication ────────────────────────────────────────
    urgent_comm_input = make_communication_input(
        org_id,
        patient_id,
        message_type="alert_notification",
        urgency="emergency",
        patient_name="Jane Doe",
    )
    urgent_comm_out = await comm_agent.process(urgent_comm_input)

    _assert_valid_output(urgent_comm_out, agent_name="patient_communication")
    urgent_result = urgent_comm_out.result
    # Emergency should use phone, sms, and in_app
    assert "phone" in urgent_result["channels"]
    assert "sms" in urgent_result["channels"]


# ═════════════════════════════════════════════════════════════════════════════
# 6. Clinical note quality — SOAP completeness and ICD-10 coding
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_clinical_note_quality(org_id, patient_id, sample_clinical_context):
    """
    Generate a clinical note with comprehensive context and verify:
    - All four SOAP sections are present and populated.
    - ICD-10 codes are suggested based on symptoms.
    - The note is marked as draft requiring provider review (HITL).
    - Billing suggestions are generated.
    """

    clinical_note_agent = ClinicalNoteAgent()

    note_ctx = {
        "symptoms": ["headache", "fatigue", "nausea", "dizziness", "palpitations"],
        "vitals": sample_clinical_context["vitals"],
        "assessment": "Tension-type headache with autonomic symptoms",
        "plan": [
            "Continue current medications",
            "Obtain ECG to evaluate palpitations",
            "Follow up in 1 week",
            "Patient education on stress management",
        ],
        "medications": ["ibuprofen", "metoprolol", "sertraline"],
        "encounter_type": "telehealth",
        "prior_outputs": [
            {"agent_name": "symptom_checker", "rationale": "5 symptoms across 3 systems"},
            {"agent_name": "visit_preparation", "rationale": "Pre-visit summary generated"},
        ],
    }
    note_input = make_telehealth_input(
        org_id, patient_id, note_ctx, trigger="note.generate"
    )
    note_out = await clinical_note_agent.process(note_input)

    _assert_valid_output(note_out, agent_name="clinical_note")
    result = note_out.result

    # ── SOAP sections ────────────────────────────────────────────────────
    soap = result["soap_note"]
    assert "subjective" in soap
    assert "objective" in soap
    assert "assessment" in soap
    assert "plan" in soap

    # Subjective section content
    subjective = soap["subjective"]
    assert subjective["chief_complaint"] == "headache"
    assert "headache" in subjective["history_of_present_illness"]
    assert isinstance(subjective["review_of_systems"], dict)
    assert len(subjective["review_of_systems"]) > 0, (
        "ROS should group symptoms by system"
    )

    # Objective section content
    objective = soap["objective"]
    assert objective["vital_signs"], "Vitals should be recorded"
    assert len(objective["ai_agent_findings"]) == 2, (
        "Should include findings from prior agents"
    )

    # Assessment section
    assessment = soap["assessment"]
    assert "Tension-type headache" in assessment["clinical_impression"]

    # Plan section
    plan_section = soap["plan"]
    assert len(plan_section["treatment"]) >= 3

    # ── ICD-10 suggestions ───────────────────────────────────────────────
    icd_suggestions = result["icd10_suggestions"]
    assert len(icd_suggestions) >= 3, (
        f"Expected ICD-10 suggestions for headache, fatigue, nausea, dizziness, palpitations; "
        f"got {len(icd_suggestions)}: {icd_suggestions}"
    )

    # Verify specific codes
    icd_codes = {s["code"] for s in icd_suggestions}
    assert "R51.9" in icd_codes, "Headache ICD-10 code R51.9 should be suggested"
    assert "R53.83" in icd_codes, "Fatigue ICD-10 code R53.83 should be suggested"
    assert "R11.0" in icd_codes, "Nausea ICD-10 code R11.0 should be suggested"

    # Each suggestion should have code and display
    for suggestion in icd_suggestions:
        assert "code" in suggestion
        assert "display" in suggestion

    # ── HITL / provider review ───────────────────────────────────────────
    # ClinicalNoteAgent has requires_hitl=True on the class, so after
    # run() wraps process(), the output is always WAITING_HITL.
    # When calling process() directly, the note_status field is "draft".
    assert result["note_status"] == "draft"

    # ── Billing suggestions ──────────────────────────────────────────────
    billing = result["billing_suggestions"]
    assert "code" in billing
    assert "suggested_level" in billing
    # 5 symptoms + vitals => moderate complexity
    assert billing["suggested_level"] == "Moderate"
    assert billing["modifier"] == "95", "Telehealth modifier should be 95"

    # ── Medications reviewed ─────────────────────────────────────────────
    assert result["medications_reviewed"] == ["ibuprofen", "metoprolol", "sertraline"]
