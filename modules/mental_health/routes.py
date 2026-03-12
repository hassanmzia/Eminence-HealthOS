"""Mental Health module API routes — screening, workflow, crisis detection, therapeutic engagement."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

logger = logging.getLogger("healthos.routes.mental_health")
router = APIRouter()

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ═════════════════════════════════════════════════════════════════════════════
# SCREENING ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/screening/phq9")
async def phq9_screen(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Score PHQ-9 depression screening instrument."""
    from modules.mental_health.agents.mental_health_screening import MentalHealthScreeningAgent

    agent = MentalHealthScreeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.screening.phq9",
        context={"action": "phq9_screen", **body},
    ))
    return output.result


@router.post("/screening/gad7")
async def gad7_screen(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Score GAD-7 anxiety screening instrument."""
    from modules.mental_health.agents.mental_health_screening import MentalHealthScreeningAgent

    agent = MentalHealthScreeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.screening.gad7",
        context={"action": "gad7_screen", **body},
    ))
    return output.result


@router.post("/screening/audit-c")
async def audit_c_screen(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Score AUDIT-C alcohol misuse screening instrument."""
    from modules.mental_health.agents.mental_health_screening import MentalHealthScreeningAgent

    agent = MentalHealthScreeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.screening.audit_c",
        context={"action": "audit_c_screen", **body},
    ))
    return output.result


@router.post("/screening/comprehensive")
async def comprehensive_screen(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Run all screening instruments (PHQ-9, GAD-7, AUDIT-C) at once."""
    from modules.mental_health.agents.mental_health_screening import MentalHealthScreeningAgent

    agent = MentalHealthScreeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.screening.comprehensive",
        context={"action": "comprehensive_screen", **body},
    ))
    return output.result


@router.get("/screening/history/{patient_id}")
async def screening_history(
    patient_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Retrieve screening history for a patient showing trends over time."""
    from modules.mental_health.agents.mental_health_screening import MentalHealthScreeningAgent

    agent = MentalHealthScreeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id),
        trigger="mental_health.screening.history",
        context={"action": "screening_history"},
    ))
    return output.result


# ═════════════════════════════════════════════════════════════════════════════
# WORKFLOW ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/workflow/referral")
async def create_referral(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a behavioral health referral based on screening results."""
    from modules.mental_health.agents.behavioral_health_workflow import BehavioralHealthWorkflowAgent

    agent = BehavioralHealthWorkflowAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.workflow.referral",
        context={"action": "create_referral", **body},
    ))
    return output.result


@router.post("/workflow/schedule")
async def schedule_session(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Schedule a therapy session with availability matching."""
    from modules.mental_health.agents.behavioral_health_workflow import BehavioralHealthWorkflowAgent

    agent = BehavioralHealthWorkflowAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.workflow.schedule",
        context={"action": "schedule_session", **body},
    ))
    return output.result


@router.post("/workflow/follow-up")
async def follow_up_check(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate follow-up assessment for behavioral health treatment adherence."""
    from modules.mental_health.agents.behavioral_health_workflow import BehavioralHealthWorkflowAgent

    agent = BehavioralHealthWorkflowAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.workflow.follow_up",
        context={"action": "follow_up_check", **body},
    ))
    return output.result


@router.post("/workflow/treatment-plan")
async def create_treatment_plan(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a structured behavioral health treatment plan."""
    from modules.mental_health.agents.behavioral_health_workflow import BehavioralHealthWorkflowAgent

    agent = BehavioralHealthWorkflowAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.workflow.treatment_plan",
        context={"action": "treatment_plan", **body},
    ))
    return output.result


# ═════════════════════════════════════════════════════════════════════════════
# CRISIS DETECTION ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/crisis/assess")
async def assess_crisis_risk(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Assess crisis risk from screening scores, clinical flags, and social factors."""
    from modules.mental_health.agents.crisis_detection import CrisisDetectionAgent

    agent = CrisisDetectionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.crisis.assess",
        context={"action": "assess_risk", **body},
    ))
    return output.result


@router.post("/crisis/screen-text")
async def screen_text_for_crisis(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Scan free-text input for crisis keywords and indicators."""
    from modules.mental_health.agents.crisis_detection import CrisisDetectionAgent

    agent = CrisisDetectionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.crisis.screen_text",
        context={"action": "screen_text", **body},
    ))
    return output.result


@router.post("/crisis/safety-plan")
async def generate_safety_plan(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate a personalized safety plan template for clinical review."""
    from modules.mental_health.agents.crisis_detection import CrisisDetectionAgent

    agent = CrisisDetectionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.crisis.safety_plan",
        context={"action": "safety_plan", **body},
    ))
    return output.result


@router.post("/crisis/escalate")
async def trigger_escalation(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Trigger escalation protocol based on assessed risk level."""
    from modules.mental_health.agents.crisis_detection import CrisisDetectionAgent

    agent = CrisisDetectionAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.crisis.escalate",
        context={"action": "escalation_protocol", **body},
    ))
    return output.result


# ═════════════════════════════════════════════════════════════════════════════
# THERAPEUTIC ENGAGEMENT ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


@router.post("/engagement/mood-check")
async def mood_check_in(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Submit or retrieve a structured mood check-in."""
    from modules.mental_health.agents.therapeutic_engagement import TherapeuticEngagementAgent

    agent = TherapeuticEngagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.engagement.mood_check",
        context={"action": "mood_check_in", **body},
    ))
    return output.result


@router.post("/engagement/cbt-exercise")
async def get_cbt_exercise(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Select and deliver an appropriate CBT exercise based on symptoms."""
    from modules.mental_health.agents.therapeutic_engagement import TherapeuticEngagementAgent

    agent = TherapeuticEngagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.engagement.cbt_exercise",
        context={"action": "cbt_exercise", **body},
    ))
    return output.result


@router.post("/engagement/mindfulness")
async def get_mindfulness_prompt(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get a contextual mindfulness exercise based on current anxiety/stress level."""
    from modules.mental_health.agents.therapeutic_engagement import TherapeuticEngagementAgent

    agent = TherapeuticEngagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="mental_health.engagement.mindfulness",
        context={"action": "mindfulness_prompt", **body},
    ))
    return output.result


@router.get("/engagement/progress/{patient_id}")
async def get_progress_summary(
    patient_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Aggregate progress summary including mood trends, exercises, and screening changes."""
    from modules.mental_health.agents.therapeutic_engagement import TherapeuticEngagementAgent

    agent = TherapeuticEngagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(patient_id),
        trigger="mental_health.engagement.progress",
        context={"action": "progress_summary"},
    ))
    return output.result
