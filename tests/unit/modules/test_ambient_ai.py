"""Tests for the Ambient AI Documentation module agents."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"ambient.{action}",
        context={"action": action, **extra},
    )


# ── Ambient Listening Agent ────────────────────────────────────────


class TestAmbientListeningAgent:
    @pytest.fixture
    def agent(self):
        from modules.ambient_ai.agents.ambient_listening import AmbientListeningAgent
        return AmbientListeningAgent()

    @pytest.mark.asyncio
    async def test_start_session(self, agent):
        out = await agent.run(_input("start_session", encounter_id="ENC-001", audio_source="telehealth_webrtc"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "recording"
        assert out.result["audio_source"] == "telehealth_webrtc"

    @pytest.mark.asyncio
    async def test_start_session_invalid_source(self, agent):
        out = await agent.run(_input("start_session", audio_source="invalid_source"))
        assert out.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_transcribe_default(self, agent):
        out = await agent.run(_input("transcribe", encounter_id="ENC-001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_segments"] > 0
        assert "segments" in out.result

    @pytest.mark.asyncio
    async def test_transcribe_with_chunks(self, agent):
        chunks = [
            {"text": "Hello, how are you?", "duration_sec": 3.0, "confidence": 0.95},
            {"text": "I have a headache.", "duration_sec": 2.5, "confidence": 0.93},
        ]
        out = await agent.run(_input("transcribe", audio_chunks=chunks))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_segments"] == 2

    @pytest.mark.asyncio
    async def test_end_session(self, agent):
        out = await agent.run(_input("end_session", session_id="sess-123"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "completed"
        assert out.result["next_step"] == "speaker_diarization"

    @pytest.mark.asyncio
    async def test_language_detect(self, agent):
        out = await agent.run(_input("language_detect", detected_language="es"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["detected_language"] == "es"

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Speaker Diarization Agent ──────────────────────────────────────


class TestSpeakerDiarizationAgent:
    @pytest.fixture
    def agent(self):
        from modules.ambient_ai.agents.speaker_diarization import SpeakerDiarizationAgent
        return SpeakerDiarizationAgent()

    @pytest.mark.asyncio
    async def test_diarize_default(self, agent):
        out = await agent.run(_input("diarize", encounter_id="ENC-001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_segments"] > 0
        assert out.result["speaker_count"] >= 2
        assert "talk_ratio" in out.result

    @pytest.mark.asyncio
    async def test_diarize_with_segments(self, agent):
        segments = [
            {"segment_id": 0, "start_sec": 0, "end_sec": 3, "text": "Let me check your vitals."},
            {"segment_id": 1, "start_sec": 3, "end_sec": 6, "text": "I've been having headaches."},
        ]
        out = await agent.run(_input("diarize", segments=segments))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_segments"] == 2

    @pytest.mark.asyncio
    async def test_identify_speakers(self, agent):
        out = await agent.run(_input("identify_speakers", expected_speakers=3))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_speakers"] == 3

    @pytest.mark.asyncio
    async def test_merge_segments(self, agent):
        segments = [
            {"speaker_id": "S1", "start_sec": 0, "end_sec": 2, "text": "Hello."},
            {"speaker_id": "S1", "start_sec": 2, "end_sec": 5, "text": "How are you?"},
            {"speaker_id": "S2", "start_sec": 5, "end_sec": 8, "text": "Fine thanks."},
        ]
        out = await agent.run(_input("merge_segments", segments=segments))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["merged_segments"] == 2

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── SOAP Note Generator Agent ─────────────────────────────────────


class TestSOAPNoteGeneratorAgent:
    @pytest.fixture
    def agent(self):
        from modules.ambient_ai.agents.soap_note_generator import SOAPNoteGeneratorAgent
        return SOAPNoteGeneratorAgent()

    @pytest.mark.asyncio
    async def test_generate_soap(self, agent):
        out = await agent.run(_input("generate_soap", encounter_id="ENC-001"))
        assert out.status == AgentStatus.COMPLETED
        assert "soap" in out.result
        soap = out.result["soap"]
        assert "subjective" in soap
        assert "objective" in soap
        assert "assessment" in soap
        assert "plan" in soap

    @pytest.mark.asyncio
    async def test_extract_entities(self, agent):
        out = await agent.run(_input("extract_entities", text_segments=["Patient has hypertension and diabetes"]))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_entities"] > 0

    @pytest.mark.asyncio
    async def test_generate_section(self, agent):
        out = await agent.run(_input("generate_section", section="subjective"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["section"] == "subjective"

    @pytest.mark.asyncio
    async def test_generate_section_invalid(self, agent):
        out = await agent.run(_input("generate_section", section="invalid"))
        assert out.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_validate_note(self, agent):
        soap = {
            "subjective": {"narrative": "CC: Headache"},
            "objective": {"narrative": "Vitals normal"},
            "assessment": {"narrative": "Tension headache", "diagnoses": []},
            "plan": {"narrative": "Acetaminophen PRN", "items": []},
        }
        out = await agent.run(_input("validate_note", soap=soap))
        assert out.status == AgentStatus.COMPLETED
        assert "is_valid" in out.result

    @pytest.mark.asyncio
    async def test_amend_note(self, agent):
        out = await agent.run(_input("amend_note", note_id="NOTE-001", amendments={"subjective": "Updated CC"}))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "amended"

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Auto-Coding Agent ─────────────────────────────────────────────


class TestAutoCodingAgent:
    @pytest.fixture
    def agent(self):
        from modules.ambient_ai.agents.auto_coding import AutoCodingAgent
        return AutoCodingAgent()

    @pytest.mark.asyncio
    async def test_code_encounter(self, agent):
        out = await agent.run(_input("code_encounter", encounter_id="ENC-001"))
        assert out.status == AgentStatus.COMPLETED
        assert "icd10_codes" in out.result
        assert "cpt_codes" in out.result
        assert "em_code" in out.result
        assert out.result["requires_provider_review"] is True

    @pytest.mark.asyncio
    async def test_suggest_icd10(self, agent):
        diagnoses = [
            {"name": "Hypertension", "icd10": "I10", "status": "existing", "certainty": "confirmed"},
        ]
        out = await agent.run(_input("suggest_icd10", diagnoses=diagnoses))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["icd10_codes"]) == 1

    @pytest.mark.asyncio
    async def test_suggest_icd10_from_text(self, agent):
        out = await agent.run(_input("suggest_icd10", text="Patient with diabetes and hypertension"))
        assert out.status == AgentStatus.COMPLETED
        assert len(out.result["icd10_codes"]) >= 2

    @pytest.mark.asyncio
    async def test_determine_em_level(self, agent):
        diagnoses = [
            {"name": "HTN", "icd10": "I10", "status": "existing"},
            {"name": "Edema", "icd10": "R60.0", "status": "new"},
        ]
        out = await agent.run(_input("determine_em_level", diagnoses=diagnoses, duration_min=20))
        assert out.status == AgentStatus.COMPLETED
        assert "code" in out.result["em_code"]

    @pytest.mark.asyncio
    async def test_validate_codes(self, agent):
        out = await agent.run(_input("validate_codes",
            icd10_codes=[{"code": "I10"}], cpt_codes=[{"code": "80048"}],
            em_code={"code": "99213"}))
        assert out.status == AgentStatus.COMPLETED
        assert "is_valid" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Provider Attestation Agent ─────────────────────────────────────


class TestProviderAttestationAgent:
    @pytest.fixture
    def agent(self):
        from modules.ambient_ai.agents.provider_attestation import ProviderAttestationAgent
        return ProviderAttestationAgent()

    @pytest.mark.asyncio
    async def test_submit_for_review(self, agent):
        out = await agent.run(_input("submit_for_review",
            note_id="NOTE-001", encounter_id="ENC-001", provider_id="DR-100"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "pending_review"

    @pytest.mark.asyncio
    async def test_approve(self, agent):
        out = await agent.run(_input("approve",
            attestation_id="ATT-001", provider_id="DR-100", note_id="NOTE-001"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "approved"
        assert out.result["finalized"] is True
        assert out.result["ready_for_billing"] is True

    @pytest.mark.asyncio
    async def test_reject(self, agent):
        out = await agent.run(_input("reject",
            attestation_id="ATT-001", rejection_reason="Incorrect assessment"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_request_amendment(self, agent):
        amendments = [{"section": "assessment", "description": "Fix diagnosis"}]
        out = await agent.run(_input("request_amendment",
            attestation_id="ATT-001", amendments=amendments))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_amendments"] == 1

    @pytest.mark.asyncio
    async def test_get_review_status(self, agent):
        out = await agent.run(_input("get_review_status", attestation_id="ATT-001"))
        assert out.status == AgentStatus.COMPLETED
        assert "status" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent"))
        assert out.status == AgentStatus.FAILED


# ── Registration & Routing ─────────────────────────────────────────


class TestAmbientAIRegistration:
    def test_register_agents(self):
        from modules.ambient_ai.agents import register_ambient_ai_agents
        register_ambient_ai_agents()
        from healthos_platform.orchestrator.registry import registry
        assert registry.get("ambient_listening") is not None
        assert registry.get("speaker_diarization") is not None
        assert registry.get("soap_note_generator") is not None
        assert registry.get("auto_coding") is not None
        assert registry.get("provider_attestation") is not None

    def test_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        assert "ambient.session.start" in ROUTING_TABLE
        assert "ambient.transcription.complete" in ROUTING_TABLE
        assert "ambient.soap.generated" in ROUTING_TABLE
        assert "ambient.encounter.complete" in ROUTING_TABLE
        assert "ambient.attestation.approved" in ROUTING_TABLE
