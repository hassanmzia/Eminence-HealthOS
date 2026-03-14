"""
Unit tests for the Drug Interaction Agent.
Tests DDI checks, allergy cross-reactivity, contraindications, and full safety checks.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus


@pytest.fixture
def agent():
    from modules.pharmacy.agents.drug_interaction import DrugInteractionAgent
    return DrugInteractionAgent()


@pytest.fixture
def trace_id():
    return uuid.uuid4()


def _make_input(trace_id, **ctx):
    return AgentInput(trace_id=trace_id, org_id=uuid.uuid4(), trigger="test", context=ctx)


# ── Drug-Drug Interaction Checks ─────────────────────────────────────────────


class TestCheckInteractions:
    def test_no_interactions(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_interactions",
            new_drug="acetaminophen",
            current_medications=["metformin", "lisinopril"],
        )
        out = agent._check_interactions(inp)
        assert out.result["interactions_found"] == 0
        assert out.result["safe_to_prescribe"] is True

    def test_major_interaction_detected(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_interactions",
            new_drug="losartan",
            current_medications=["lisinopril"],
        )
        out = agent._check_interactions(inp)
        assert out.result["interactions_found"] >= 1
        assert out.result["has_major_interaction"] is True
        assert out.result["safe_to_prescribe"] is False

    def test_moderate_interaction(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_interactions",
            new_drug="simvastatin",
            current_medications=["amlodipine"],
        )
        out = agent._check_interactions(inp)
        assert out.result["interactions_found"] >= 1
        # Moderate interactions are still safe but flagged
        ints = out.result["interactions"]
        assert any(i["severity"] == "moderate" for i in ints)

    def test_case_insensitive(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_interactions",
            new_drug="Warfarin",
            current_medications=["ASPIRIN"],
        )
        out = agent._check_interactions(inp)
        assert out.result["interactions_found"] >= 1

    def test_serotonin_syndrome_detected(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_interactions",
            new_drug="tramadol",
            current_medications=["sertraline"],
        )
        out = agent._check_interactions(inp)
        assert out.result["has_major_interaction"] is True
        assert any("serotonin" in i["description"].lower() for i in out.result["interactions"])


# ── Allergy Checks ───────────────────────────────────────────────────────────


class TestCheckAllergies:
    def test_no_allergy(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_allergies",
            new_drug="metformin",
            allergies=["penicillin"],
        )
        out = agent._check_allergies(inp)
        assert out.result["has_allergy_conflict"] is False
        assert out.result["safe_to_prescribe"] is True

    def test_direct_allergy_match(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_allergies",
            new_drug="amoxicillin",
            allergies=["amoxicillin"],
        )
        out = agent._check_allergies(inp)
        assert out.result["has_allergy_conflict"] is True
        assert any(a["type"] == "direct_allergy" for a in out.result["alerts"])

    def test_cross_reactivity_penicillin_class(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_allergies",
            new_drug="amoxicillin",
            allergies=["penicillin"],
        )
        out = agent._check_allergies(inp)
        assert out.result["has_allergy_conflict"] is True
        alerts = out.result["alerts"]
        cross = [a for a in alerts if a["type"] == "cross_reactivity"]
        assert len(cross) >= 1
        assert cross[0]["drug_class"] == "penicillin"

    def test_nsaid_cross_reactivity(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_allergies",
            new_drug="ibuprofen",
            allergies=["aspirin"],
        )
        out = agent._check_allergies(inp)
        assert out.result["has_allergy_conflict"] is True


# ── Contraindication Checks ──────────────────────────────────────────────────


class TestCheckContraindications:
    def test_no_contraindications(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_contraindications",
            new_drug="metformin",
            patient_age=45,
            conditions=[],
        )
        out = agent._check_contraindications(inp)
        assert out.result["has_contraindication"] is False

    def test_age_warning_elderly(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_contraindications",
            new_drug="gabapentin",
            patient_age=72,
            conditions=[],
        )
        out = agent._check_contraindications(inp)
        warnings = out.result["warnings"]
        age_warnings = [w for w in warnings if w["type"] == "age_warning"]
        assert len(age_warnings) >= 1

    def test_pregnancy_contraindication(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_contraindications",
            new_drug="lisinopril",
            patient_age=30,
            conditions=["pregnancy"],
        )
        out = agent._check_contraindications(inp)
        assert out.result["has_contraindication"] is True
        assert out.result["safe_to_prescribe"] is False

    def test_renal_failure_metformin(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_contraindications",
            new_drug="metformin",
            patient_age=65,
            conditions=["renal_failure"],
        )
        out = agent._check_contraindications(inp)
        assert out.result["has_contraindication"] is True


# ── Full Safety Check ────────────────────────────────────────────────────────


class TestFullSafetyCheck:
    @pytest.mark.asyncio
    async def test_full_check_safe(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="full_safety_check",
            new_drug="acetaminophen",
            current_medications=["metformin"],
            allergies=[],
            patient_age=45,
            conditions=[],
        )
        with patch.object(agent, "_full_safety_check", wraps=agent._full_safety_check):
            out = await agent.process(inp)
        assert out.result["safe_to_prescribe"] is True
        assert out.result["total_issues"] == 0

    @pytest.mark.asyncio
    async def test_full_check_unsafe(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="full_safety_check",
            new_drug="lisinopril",
            current_medications=["losartan", "spironolactone"],
            allergies=[],
            patient_age=30,
            conditions=["pregnancy"],
        )
        out = await agent.process(inp)
        assert out.result["safe_to_prescribe"] is False
        assert out.result["total_issues"] >= 2

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent, trace_id):
        inp = _make_input(trace_id, action="invalid_action")
        out = await agent.process(inp)
        assert out.status == AgentStatus.FAILED


# ── Process Dispatch ─────────────────────────────────────────────────────────


class TestProcessDispatch:
    @pytest.mark.asyncio
    async def test_routes_to_check_interactions(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_interactions",
            new_drug="warfarin",
            current_medications=["aspirin"],
        )
        out = await agent.process(inp)
        assert "interactions" in out.result

    @pytest.mark.asyncio
    async def test_routes_to_check_allergies(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_allergies",
            new_drug="amoxicillin",
            allergies=["penicillin"],
        )
        out = await agent.process(inp)
        assert "alerts" in out.result

    @pytest.mark.asyncio
    async def test_routes_to_check_contraindications(self, agent, trace_id):
        inp = _make_input(
            trace_id,
            action="check_contraindications",
            new_drug="metformin",
            patient_age=85,
            conditions=[],
        )
        out = await agent.process(inp)
        assert "warnings" in out.result
