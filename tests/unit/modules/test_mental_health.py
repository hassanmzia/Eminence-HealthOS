"""Tests for the Mental Health module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"mental_health.{action}",
        context={"action": action, **extra},
    )


# ── Mental Health Screening Agent ───────────────────────────────────

class TestMentalHealthScreeningAgent:
    @pytest.fixture
    def agent(self):
        from modules.mental_health.agents.mental_health_screening import MentalHealthScreeningAgent
        return MentalHealthScreeningAgent()

    @pytest.mark.asyncio
    async def test_phq9_minimal(self, agent):
        inp = _input("phq9_screen", responses=[0, 0, 1, 0, 0, 0, 1, 0, 0])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_score"] == 2
        assert out.result["severity"] == "minimal"

    @pytest.mark.asyncio
    async def test_phq9_severe(self, agent):
        inp = _input("phq9_screen", responses=[3, 3, 3, 2, 3, 2, 3, 2, 3])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_score"] == 24
        assert out.result["severity"] == "severe"
        assert out.result["clinical_flags"]["suicidal_ideation"] is True

    @pytest.mark.asyncio
    async def test_gad7_moderate(self, agent):
        inp = _input("gad7_screen", responses=[2, 1, 2, 2, 1, 2, 1])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["severity"] == "moderate"

    @pytest.mark.asyncio
    async def test_audit_c_at_risk_male(self, agent):
        inp = _input("audit_c_screen", responses=[2, 2, 1], gender="male")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["score"] == 5
        assert out.result["at_risk"] is True

    @pytest.mark.asyncio
    async def test_audit_c_not_at_risk_female(self, agent):
        inp = _input("audit_c_screen", responses=[1, 0, 0], gender="female")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["at_risk"] is False

    @pytest.mark.asyncio
    async def test_comprehensive_screen(self, agent):
        inp = _input("comprehensive_screen",
                      phq9_responses=[2, 1, 2, 1, 1, 2, 1, 1, 0],
                      gad7_responses=[1, 2, 1, 2, 1, 1, 1],
                      audit_c_responses=[1, 1, 0],
                      gender="female")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "phq9" in out.result
        assert "gad7" in out.result
        assert "audit_c" in out.result
        assert "overall_risk" in out.result

    @pytest.mark.asyncio
    async def test_screening_history(self, agent):
        out = await agent.run(_input("screening_history"))
        assert out.status == AgentStatus.COMPLETED


# ── Behavioral Health Workflow Agent ────────────────────────────────

class TestBehavioralHealthWorkflowAgent:
    @pytest.fixture
    def agent(self):
        from modules.mental_health.agents.behavioral_health_workflow import BehavioralHealthWorkflowAgent
        return BehavioralHealthWorkflowAgent()

    @pytest.mark.asyncio
    async def test_create_referral(self, agent):
        inp = _input("create_referral", condition="depression",
                      severity="moderate", phq9_score=14)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "referral_id" in out.result
        assert "matched_providers" in out.result

    @pytest.mark.asyncio
    async def test_schedule_session(self, agent):
        inp = _input("schedule_session", modality="telehealth",
                      provider_type="psychologist")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_treatment_plan(self, agent):
        inp = _input("treatment_plan", diagnosis="major_depressive_disorder",
                      severity="moderate")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "goals" in out.result
        assert "interventions" in out.result

    @pytest.mark.asyncio
    async def test_follow_up_check(self, agent):
        out = await agent.run(_input("follow_up_check"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_care_coordination(self, agent):
        out = await agent.run(_input("care_coordination"))
        assert out.status == AgentStatus.COMPLETED


# ── Crisis Detection Agent ──────────────────────────────────────────

class TestCrisisDetectionAgent:
    @pytest.fixture
    def agent(self):
        from modules.mental_health.agents.crisis_detection import CrisisDetectionAgent
        return CrisisDetectionAgent()

    @pytest.mark.asyncio
    async def test_assess_low_risk(self, agent):
        inp = _input("assess_risk", phq9_item9=0, recent_scores={"phq9": 5, "gad7": 4})
        out = await agent.run(inp)
        assert out.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_HITL)
        assert "risk_level" in out.result

    @pytest.mark.asyncio
    async def test_assess_high_risk(self, agent):
        inp = _input("assess_risk", phq9_item9=3,
                      recent_scores={"phq9": 22, "gad7": 18})
        out = await agent.run(inp)
        # High risk should always require HITL
        assert out.requires_hitl is True
        assert out.result["risk_level"] in ("high", "imminent")

    @pytest.mark.asyncio
    async def test_screen_text_no_crisis(self, agent):
        inp = _input("screen_text", text="Patient reports feeling better today and sleeping well.")
        out = await agent.run(inp)
        assert out.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_HITL)

    @pytest.mark.asyncio
    async def test_screen_text_crisis_indicators(self, agent):
        inp = _input("screen_text", text="Patient expressed feeling hopeless and not wanting to go on.")
        out = await agent.run(inp)
        assert out.requires_hitl is True
        assert len(out.result.get("detections", [])) > 0

    @pytest.mark.asyncio
    async def test_safety_plan(self, agent):
        out = await agent.run(_input("safety_plan"))
        assert out.status in (AgentStatus.COMPLETED, AgentStatus.WAITING_HITL)
        assert "crisis_resources" in out.result

    @pytest.mark.asyncio
    async def test_escalation_protocol(self, agent):
        inp = _input("escalation_protocol", risk_level="high")
        out = await agent.run(inp)
        assert "escalation_path" in out.result


# ── Therapeutic Engagement Agent ────────────────────────────────────

class TestTherapeuticEngagementAgent:
    @pytest.fixture
    def agent(self):
        from modules.mental_health.agents.therapeutic_engagement import TherapeuticEngagementAgent
        return TherapeuticEngagementAgent()

    @pytest.mark.asyncio
    async def test_mood_check_in(self, agent):
        inp = _input("mood_check_in", mood=6, sleep=7, energy=5, anxiety=4)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "response" in out.result

    @pytest.mark.asyncio
    async def test_cbt_exercise(self, agent):
        inp = _input("cbt_exercise", symptom="depression")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "exercise" in out.result

    @pytest.mark.asyncio
    async def test_mindfulness_prompt(self, agent):
        inp = _input("mindfulness_prompt", stress_level=7)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "exercise" in out.result

    @pytest.mark.asyncio
    async def test_progress_summary(self, agent):
        out = await agent.run(_input("progress_summary", period_days=30))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_engagement_plan(self, agent):
        out = await agent.run(_input("engagement_plan"))
        assert out.status == AgentStatus.COMPLETED
        assert "schedule" in out.result


# ── Registration & Routing ──────────────────────────────────────────

class TestMentalHealthRegistration:
    def test_register_agents(self):
        from modules.mental_health.agents import register_mental_health_agents
        register_mental_health_agents()
        from healthos_platform.orchestrator.registry import registry
        assert registry.get("mental_health_screening") is not None
        assert registry.get("behavioral_health_workflow") is not None
        assert registry.get("crisis_detection") is not None
        assert registry.get("therapeutic_engagement") is not None

    def test_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        assert "mental_health.screening" in ROUTING_TABLE
        assert "mental_health.crisis.assess" in ROUTING_TABLE
        assert "mental_health.workflow.referral" in ROUTING_TABLE
        assert "mental_health.engagement" in ROUTING_TABLE
