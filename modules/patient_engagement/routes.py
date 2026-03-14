"""Patient Engagement & SDOH module API routes — literacy, multilingual, triage, navigation, SDOH, resources, engagement."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/patient-engagement", tags=["patient-engagement"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Health Literacy ───────────────────────────────────────────────────────


@router.post("/literacy/adapt")
async def adapt_content(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Adapt clinical content to patient reading level."""
    from modules.patient_engagement.agents.health_literacy import HealthLiteracyAgent

    agent = HealthLiteracyAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.literacy.adapt",
        context={"action": "adapt_content", **body},
    ))
    return output.result


@router.post("/literacy/assess")
async def assess_readability(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Assess readability of clinical content."""
    from modules.patient_engagement.agents.health_literacy import HealthLiteracyAgent

    agent = HealthLiteracyAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="engagement.literacy.assess",
        context={"action": "assess_readability", **body},
    ))
    return output.result


# ── Multilingual Communication ────────────────────────────────────────────


@router.post("/translate")
async def translate_content(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Translate clinical content to target language."""
    from modules.patient_engagement.agents.multilingual_communication import MultilingualCommunicationAgent

    agent = MultilingualCommunicationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="engagement.translate",
        context={"action": "translate", **body},
    ))
    return output.result


@router.get("/translate/languages")
async def supported_languages(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get list of supported languages."""
    from modules.patient_engagement.agents.multilingual_communication import MultilingualCommunicationAgent

    agent = MultilingualCommunicationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="engagement.translate.languages",
        context={"action": "supported_languages"},
    ))
    return output.result


# ── Conversational Triage ─────────────────────────────────────────────────


@router.post("/triage/assess")
async def triage_symptoms(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Triage patient symptoms."""
    from modules.patient_engagement.agents.conversational_triage import ConversationalTriageAgent

    agent = ConversationalTriageAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.triage.assess",
        context={"action": "triage_symptoms", **body},
    ))
    return output.result


@router.post("/triage/recommendation")
async def triage_recommendation(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get triage recommendation."""
    from modules.patient_engagement.agents.conversational_triage import ConversationalTriageAgent

    agent = ConversationalTriageAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="engagement.triage.recommendation",
        context={"action": "get_recommendation", **body},
    ))
    return output.result


# ── Care Navigation ──────────────────────────────────────────────────────


@router.post("/navigation/create-journey")
async def create_journey(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a care navigation journey for a patient."""
    from modules.patient_engagement.agents.care_navigation import CareNavigationAgent

    agent = CareNavigationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.navigation.create",
        context={"action": "create_journey", **body},
    ))
    return output.result


@router.post("/navigation/next-step")
async def next_step(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get next step in care journey."""
    from modules.patient_engagement.agents.care_navigation import CareNavigationAgent

    agent = CareNavigationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="engagement.navigation.next",
        context={"action": "get_next_step", **body},
    ))
    return output.result


# ── SDOH Screening ────────────────────────────────────────────────────────


@router.post("/sdoh/screen")
async def screen_patient(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Screen patient for social determinants of health."""
    from modules.patient_engagement.agents.sdoh_screening import SDOHScreeningAgent

    agent = SDOHScreeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.sdoh.screen",
        context={"action": "screen_patient", **body},
    ))
    return output.result


@router.get("/sdoh/questions")
async def sdoh_questions(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get SDOH screening questions."""
    from modules.patient_engagement.agents.sdoh_screening import SDOHScreeningAgent

    agent = SDOHScreeningAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="engagement.sdoh.questions",
        context={"action": "get_questions"},
    ))
    return output.result


# ── Community Resources ───────────────────────────────────────────────────


@router.post("/resources/find")
async def find_resources(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Find community resources matching patient needs."""
    from modules.patient_engagement.agents.community_resource import CommunityResourceAgent

    agent = CommunityResourceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.resources.find",
        context={"action": "find_resources", **body},
    ))
    return output.result


@router.post("/resources/referral")
async def create_referral(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Create a referral to a community resource."""
    from modules.patient_engagement.agents.community_resource import CommunityResourceAgent

    agent = CommunityResourceAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.resources.referral",
        context={"action": "create_referral", **body},
    ))
    return output.result


# ── Motivational Engagement ──────────────────────────────────────────────


@router.post("/engagement/nudge")
async def send_nudge(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Send a behavioral nudge to a patient."""
    from modules.patient_engagement.agents.motivational_engagement import MotivationalEngagementAgent

    agent = MotivationalEngagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.nudge.send",
        context={"action": "send_nudge", **body},
    ))
    return output.result


@router.post("/engagement/score")
async def engagement_score(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Calculate patient engagement score."""
    from modules.patient_engagement.agents.motivational_engagement import MotivationalEngagementAgent

    agent = MotivationalEngagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="engagement.score",
        context={"action": "engagement_score", **body},
    ))
    return output.result


@router.get("/engagement/report")
async def engagement_report(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get engagement analytics report."""
    from modules.patient_engagement.agents.motivational_engagement import MotivationalEngagementAgent

    agent = MotivationalEngagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="engagement.report",
        context={"action": "engagement_report"},
    ))
    return output.result
