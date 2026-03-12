"""Tests for the Patient Engagement & SDOH module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"engagement.{action}",
        context={"action": action, **extra},
    )


# ── Health Literacy Agent ────────────────────────────────────────


class TestHealthLiteracyAgent:
    @pytest.fixture
    def agent(self):
        from modules.patient_engagement.agents.health_literacy import HealthLiteracyAgent
        return HealthLiteracyAgent()

    @pytest.mark.asyncio
    async def test_adapt_content(self, agent):
        out = await agent.run(_input("adapt_content", target_level="5th_grade"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["target_level"] == "5th_grade"

    @pytest.mark.asyncio
    async def test_assess_readability(self, agent):
        out = await agent.run(_input("assess_readability",
            text="The patient presents with essential hypertension."))
        assert out.status == AgentStatus.COMPLETED
        assert "flesch_kincaid_grade" in out.result

    @pytest.mark.asyncio
    async def test_simplify_terms(self, agent):
        out = await agent.run(_input("simplify_terms",
            terms=["hypertension", "dyspnea"]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_simplified"] == 2

    @pytest.mark.asyncio
    async def test_generate_handout(self, agent):
        out = await agent.run(_input("generate_handout",
            condition="hypertension", target_level="8th_grade"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["sections"]) > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Multilingual Communication Agent ────────────────────────────


class TestMultilingualCommunicationAgent:
    @pytest.fixture
    def agent(self):
        from modules.patient_engagement.agents.multilingual_communication import MultilingualCommunicationAgent
        return MultilingualCommunicationAgent()

    @pytest.mark.asyncio
    async def test_translate(self, agent):
        out = await agent.run(_input("translate",
            source_language="en", target_language="es",
            text="Take your medication daily."))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["target_language"] == "es"

    @pytest.mark.asyncio
    async def test_detect_language(self, agent):
        out = await agent.run(_input("detect_language",
            text="Hello, how are you?"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["detected_language"] is not None

    @pytest.mark.asyncio
    async def test_translate_form(self, agent):
        out = await agent.run(_input("translate_form",
            form_type="intake", target_language="es"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_fields"] > 0

    @pytest.mark.asyncio
    async def test_supported_languages(self, agent):
        out = await agent.run(_input("supported_languages"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_supported"] >= 10

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Conversational Triage Agent ──────────────────────────────────


class TestConversationalTriageAgent:
    @pytest.fixture
    def agent(self):
        from modules.patient_engagement.agents.conversational_triage import ConversationalTriageAgent
        return ConversationalTriageAgent()

    @pytest.mark.asyncio
    async def test_triage_chest_pain(self, agent):
        out = await agent.run(_input("triage_symptoms",
            chief_complaint="chest pain",
            red_flags=["radiating to arm"]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["triage_level"] == "emergent"

    @pytest.mark.asyncio
    async def test_triage_headache(self, agent):
        out = await agent.run(_input("triage_symptoms",
            chief_complaint="headache", symptoms=["throbbing"]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["triage_level"] in ("semi_urgent", "routine")

    @pytest.mark.asyncio
    async def test_ask_followup(self, agent):
        out = await agent.run(_input("ask_followup",
            protocol="headache", question_index=0))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["question"] is not None

    @pytest.mark.asyncio
    async def test_get_recommendation(self, agent):
        out = await agent.run(_input("get_recommendation",
            triage_level="routine"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["can_schedule_online"] is True

    @pytest.mark.asyncio
    async def test_triage_summary(self, agent):
        out = await agent.run(_input("triage_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_triages"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Care Navigation Agent ───────────────────────────────────────


class TestCareNavigationAgent:
    @pytest.fixture
    def agent(self):
        from modules.patient_engagement.agents.care_navigation import CareNavigationAgent
        return CareNavigationAgent()

    @pytest.mark.asyncio
    async def test_create_journey(self, agent):
        out = await agent.run(_input("create_journey",
            pathway="diabetes_management"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_steps"] == 6
        assert out.result["current_step"] == 1

    @pytest.mark.asyncio
    async def test_get_next_step(self, agent):
        out = await agent.run(_input("get_next_step",
            pathway="diabetes_management", current_step=2))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["next_step"] is not None

    @pytest.mark.asyncio
    async def test_update_progress(self, agent):
        out = await agent.run(_input("update_progress",
            step_number=1, status="completed"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["next_step_unlocked"] is True

    @pytest.mark.asyncio
    async def test_journey_summary(self, agent):
        out = await agent.run(_input("journey_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["active_journeys"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── SDOH Screening Agent ────────────────────────────────────────


class TestSDOHScreeningAgent:
    @pytest.fixture
    def agent(self):
        from modules.patient_engagement.agents.sdoh_screening import SDOHScreeningAgent
        return SDOHScreeningAgent()

    @pytest.mark.asyncio
    async def test_screen_patient_defaults(self, agent):
        out = await agent.run(_input("screen_patient"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_domains_screened"] == 5
        assert out.result["domains_at_risk"] >= 1

    @pytest.mark.asyncio
    async def test_screen_patient_all_ok(self, agent):
        responses = {
            "food_insecurity": {"positive_responses": 0, "total_questions": 2},
            "housing_instability": {"positive_responses": 0, "total_questions": 3},
            "transportation": {"positive_responses": 0, "total_questions": 2},
            "social_isolation": {"positive_responses": 0, "total_questions": 2},
            "financial_strain": {"positive_responses": 0, "total_questions": 2},
        }
        out = await agent.run(_input("screen_patient", responses=responses))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["overall_risk"] == "low"
        assert out.result["referral_recommended"] is False

    @pytest.mark.asyncio
    async def test_score_responses(self, agent):
        out = await agent.run(_input("score_responses",
            domain="food_insecurity",
            answers=[{"positive": True}, {"positive": False}]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["at_risk"] is True

    @pytest.mark.asyncio
    async def test_get_questions(self, agent):
        out = await agent.run(_input("get_questions"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_questions"] >= 10

    @pytest.mark.asyncio
    async def test_sdoh_summary(self, agent):
        out = await agent.run(_input("sdoh_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_screenings"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Community Resource Agent ─────────────────────────────────────


class TestCommunityResourceAgent:
    @pytest.fixture
    def agent(self):
        from modules.patient_engagement.agents.community_resource import CommunityResourceAgent
        return CommunityResourceAgent()

    @pytest.mark.asyncio
    async def test_find_resources(self, agent):
        out = await agent.run(_input("find_resources",
            needs=["food_insecurity", "transportation"], zip_code="10001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_resources"] >= 4

    @pytest.mark.asyncio
    async def test_create_referral(self, agent):
        out = await agent.run(_input("create_referral",
            resource_name="Community Food Bank", need_category="food_insecurity"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_referral_status(self, agent):
        out = await agent.run(_input("referral_status",
            referral_id="REF-001"))
        assert out.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_resource_directory(self, agent):
        out = await agent.run(_input("resource_directory"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_categories"] == 5
        assert out.result["total_resources"] >= 15

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Motivational Engagement Agent ────────────────────────────────


class TestMotivationalEngagementAgent:
    @pytest.fixture
    def agent(self):
        from modules.patient_engagement.agents.motivational_engagement import MotivationalEngagementAgent
        return MotivationalEngagementAgent()

    @pytest.mark.asyncio
    async def test_send_nudge(self, agent):
        out = await agent.run(_input("send_nudge",
            nudge_type="medication_reminder"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_award_badge(self, agent):
        out = await agent.run(_input("award_badge",
            badge="med_streak_7", current_points=100, current_badges=3))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["points_earned"] == 50
        assert out.result["total_points"] == 150

    @pytest.mark.asyncio
    async def test_engagement_score(self, agent):
        out = await agent.run(_input("engagement_score"))
        assert out.status == AgentStatus.COMPLETED
        assert 0 <= out.result["engagement_score"] <= 100

    @pytest.mark.asyncio
    async def test_engagement_report(self, agent):
        out = await agent.run(_input("engagement_report"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_patients"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Registration & Routing ───────────────────────────────────────


class TestPatientEngagementRegistration:
    def test_register_patient_engagement_agents(self):
        from modules.patient_engagement.agents import register_patient_engagement_agents
        from healthos_platform.orchestrator.registry import registry
        register_patient_engagement_agents()
        for name in ["health_literacy", "multilingual_communication", "conversational_triage",
                      "care_navigation", "sdoh_screening", "community_resource", "motivational_engagement"]:
            assert registry.get(name) is not None, f"Agent '{name}' not registered"

    def test_patient_engagement_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        engagement_events = [k for k in ROUTING_TABLE if k.startswith("engagement.")]
        assert len(engagement_events) >= 6, f"Expected >=6 engagement routes, got {len(engagement_events)}"
