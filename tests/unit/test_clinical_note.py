"""
Unit tests for the Clinical Note Agent.
Tests SOAP note generation, ICD-10 suggestions, and billing level logic.
"""

from __future__ import annotations

import uuid

import pytest

from healthos_platform.agents.types import AgentInput


@pytest.fixture
def agent():
    from modules.telehealth.agents.clinical_note import ClinicalNoteAgent
    return ClinicalNoteAgent()


@pytest.fixture
def trace_id():
    return uuid.uuid4()


def _make_input(trace_id, **ctx):
    return AgentInput(trace_id=trace_id, org_id=uuid.uuid4(), trigger="test", context=ctx)


# ── SOAP Note Construction ───────────────────────────────────────────────────


class TestBuildSoap:
    def test_soap_sections_present(self, agent):
        soap = agent._build_soap(
            symptoms=["headache", "fever"],
            vitals={"heart_rate": 80, "temperature": 101.2},
            assessment="Likely viral URI",
            plan=["Rest", "Fluids", "Acetaminophen PRN"],
            prior_outputs=[],
        )
        assert "subjective" in soap
        assert "objective" in soap
        assert "assessment" in soap
        assert "plan" in soap

    def test_subjective_chief_complaint(self, agent):
        soap = agent._build_soap(
            symptoms=["chest_pain", "shortness_of_breath"],
            vitals={},
            assessment="",
            plan=[],
            prior_outputs=[],
        )
        assert soap["subjective"]["chief_complaint"] == "chest_pain"

    def test_subjective_no_symptoms(self, agent):
        soap = agent._build_soap(
            symptoms=[], vitals={}, assessment="", plan=[], prior_outputs=[],
        )
        assert soap["subjective"]["chief_complaint"] == "Not specified"

    def test_objective_includes_vitals(self, agent):
        vitals = {"heart_rate": 72, "blood_pressure": "120/80"}
        soap = agent._build_soap(
            symptoms=[], vitals=vitals, assessment="", plan=[], prior_outputs=[],
        )
        assert soap["objective"]["vital_signs"] == vitals

    def test_plan_from_input(self, agent):
        plan_items = ["Start amoxicillin 500mg TID", "Follow up in 7 days"]
        soap = agent._build_soap(
            symptoms=[], vitals={}, assessment="", plan=plan_items, prior_outputs=[],
        )
        assert soap["plan"]["treatment"] == plan_items

    def test_prior_outputs_included(self, agent):
        prior = [{"agent_name": "risk_scoring", "rationale": "Risk score: 0.72"}]
        soap = agent._build_soap(
            symptoms=[], vitals={}, assessment="", plan=[], prior_outputs=prior,
        )
        findings = soap["objective"]["ai_agent_findings"]
        assert len(findings) == 1
        assert findings[0]["agent"] == "risk_scoring"


# ── ICD-10 Suggestions ──────────────────────────────────────────────────────


class TestSuggestICD10:
    def test_known_symptoms_mapped(self, agent):
        suggestions = agent._suggest_icd10(["headache", "fever", "cough"])
        assert len(suggestions) == 3
        codes = {s["code"] for s in suggestions}
        assert "R51.9" in codes  # headache
        assert "R50.9" in codes  # fever
        assert "R05.9" in codes  # cough

    def test_unknown_symptom_ignored(self, agent):
        suggestions = agent._suggest_icd10(["headache", "alien_syndrome"])
        assert len(suggestions) == 1

    def test_empty_symptoms(self, agent):
        suggestions = agent._suggest_icd10([])
        assert suggestions == []

    def test_case_normalization(self, agent):
        suggestions = agent._suggest_icd10(["Chest Pain"])
        assert len(suggestions) == 1
        assert suggestions[0]["code"] == "R07.9"


# ── Billing Suggestions ──────────────────────────────────────────────────────


class TestSuggestBilling:
    def test_telehealth_straightforward(self, agent):
        billing = agent._suggest_billing("telehealth", symptom_count=1, has_vitals=False)
        assert billing["code"] == "99212"
        assert billing["modifier"] == "95"

    def test_telehealth_low(self, agent):
        billing = agent._suggest_billing("telehealth", symptom_count=2, has_vitals=False)
        assert billing["code"] == "99213"

    def test_telehealth_moderate(self, agent):
        billing = agent._suggest_billing("telehealth", symptom_count=5, has_vitals=True)
        assert billing["code"] == "99214"

    def test_telehealth_moderate_with_vitals(self, agent):
        billing = agent._suggest_billing("telehealth", symptom_count=3, has_vitals=True)
        assert billing["code"] == "99214"

    def test_non_telehealth_default(self, agent):
        billing = agent._suggest_billing("office_visit", symptom_count=5, has_vitals=True)
        assert billing["code"] == "99213"
        assert billing["modifier"] == ""


# ── Full Process ─────────────────────────────────────────────────────────────


class TestClinicalNoteProcess:
    @pytest.mark.asyncio
    async def test_process_generates_note(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            symptoms=["headache", "nausea"],
            vitals={"heart_rate": 78, "bp": "130/85"},
            assessment="Migraine with aura",
            plan=["Sumatriptan 50mg", "Dark room rest"],
            encounter_type="telehealth",
            medications=["lisinopril"],
        )
        out = await agent.process(inp)
        result = out.result
        assert "soap_note" in result
        assert "icd10_suggestions" in result
        assert "billing_suggestions" in result
        assert result["note_status"] == "draft"
        assert result["medications_reviewed"] == ["lisinopril"]

    @pytest.mark.asyncio
    async def test_process_confidence_without_llm(self, agent, trace_id):
        # LLM will fail in test env, so confidence should be lower
        inp = _make_input(trace_id, symptoms=["fever"], encounter_type="telehealth")
        out = await agent.process(inp)
        # Without LLM success, confidence is 0.75
        assert out.confidence in (0.75, 0.85)

    @pytest.mark.asyncio
    async def test_requires_hitl(self, agent):
        assert agent.requires_hitl is True
