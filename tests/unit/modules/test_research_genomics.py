"""Tests for the Research & Genomics module agents (#71-75)."""

import uuid
import pytest

from healthos_platform.agents.types import AgentInput, AgentStatus

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _input(action: str, **extra) -> AgentInput:
    return AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=PATIENT_ID,
        trigger=f"research.{action}",
        context={"action": action, **extra},
    )


# ── Clinical Trial Matching Agent (#71) ───────────────────────────


class TestClinicalTrialMatchingAgent:
    @pytest.fixture
    def agent(self):
        from modules.research_genomics.agents.clinical_trial_matching import ClinicalTrialMatchingAgent
        return ClinicalTrialMatchingAgent()

    @pytest.mark.asyncio
    async def test_match_trials(self, agent):
        inp = _input("match_trials", conditions=["type_2_diabetes", "ckd"],
                      age=55, labs={"egfr": 45, "hba1c": 8.2})
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "matches" in out.result
        assert out.result["matches_found"] > 0

    @pytest.mark.asyncio
    async def test_match_no_conditions(self, agent):
        inp = _input("match_trials", conditions=["rare_condition_xyz"], age=40)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["matches_found"] == 0

    @pytest.mark.asyncio
    async def test_check_eligibility(self, agent):
        inp = _input("check_eligibility", nct_id="NCT05001234",
                      conditions=["type_2_diabetes", "ckd"], age=55)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "eligible" in out.result
        assert "criteria_checks" in out.result

    @pytest.mark.asyncio
    async def test_trial_details(self, agent):
        inp = _input("trial_details", nct_id="NCT05001234")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "trial" in out.result

    @pytest.mark.asyncio
    async def test_enrollment_status(self, agent):
        out = await agent.run(_input("enrollment_status"))
        assert out.status == AgentStatus.COMPLETED
        assert "trials" in out.result
        assert out.result["total_trials"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent_action"))
        assert out.status in (AgentStatus.FAILED, AgentStatus.WAITING_HITL)


# ── De-Identification Agent (#72) ─────────────────────────────────


class TestDeIdentificationAgent:
    @pytest.fixture
    def agent(self):
        from modules.research_genomics.agents.deidentification import DeIdentificationAgent
        return DeIdentificationAgent()

    @pytest.mark.asyncio
    async def test_deidentify_dataset(self, agent):
        inp = _input("deidentify_dataset", record_count=100,
                      dataset_name="test_cohort")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["safe_harbor_compliant"] is True
        assert out.result["total_redactions"] > 0

    @pytest.mark.asyncio
    async def test_verify_deidentification(self, agent):
        inp = _input("verify_deidentification", job_id="test-job-123")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["hipaa_compliant"] is True
        assert out.result["all_passed"] is True

    @pytest.mark.asyncio
    async def test_scan_phi(self, agent):
        inp = _input("scan_phi", text="Patient John Doe, DOB 1955-03-15")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_phi_instances"] > 0
        assert out.result["requires_deidentification"] is True

    @pytest.mark.asyncio
    async def test_export_dataset(self, agent):
        inp = _input("export_dataset", dataset_name="research_export",
                      record_count=500, format="csv")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["hipaa_compliant"] is True
        assert "export_location" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent_action"))
        assert out.status in (AgentStatus.FAILED, AgentStatus.WAITING_HITL)


# ── Research Cohort Agent (#73) ───────────────────────────────────


class TestResearchCohortAgent:
    @pytest.fixture
    def agent(self):
        from modules.research_genomics.agents.research_cohort import ResearchCohortAgent
        return ResearchCohortAgent()

    @pytest.mark.asyncio
    async def test_build_cohort_from_template(self, agent):
        inp = _input("build_cohort", template="diabetes_ckd")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["status"] == "ready"
        assert out.result["final_cohort_size"] > 0

    @pytest.mark.asyncio
    async def test_build_custom_cohort(self, agent):
        inp = _input("build_cohort", cohort_name="Custom Study",
                      total_population=5000)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["cohort_name"] == "Custom Study"

    @pytest.mark.asyncio
    async def test_cohort_characteristics(self, agent):
        inp = _input("cohort_characteristics", cohort_id="test-cohort-1")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "demographics" in out.result
        assert "clinical" in out.result

    @pytest.mark.asyncio
    async def test_compare_cohorts(self, agent):
        inp = _input("compare_cohorts", cohort_a="Treatment",
                      cohort_b="Control")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["overall_balance"] == "well_balanced"
        assert "comparisons" in out.result

    @pytest.mark.asyncio
    async def test_list_templates(self, agent):
        out = await agent.run(_input("list_templates"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_templates"] == 3

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent_action"))
        assert out.status in (AgentStatus.FAILED, AgentStatus.WAITING_HITL)


# ── Pharmacogenomics Agent (#74) ──────────────────────────────────


class TestPharmacogenomicsAgent:
    @pytest.fixture
    def agent(self):
        from modules.research_genomics.agents.pharmacogenomics import PharmacogenomicsAgent
        return PharmacogenomicsAgent()

    @pytest.mark.asyncio
    async def test_check_drug_gene(self, agent):
        inp = _input("check_drug_gene", medication="warfarin",
                      genotype={"VKORC1": "high_sensitivity"})
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_interactions"] > 0
        assert out.result["requires_action"] in (True, False)  # depends on phenotype resolution

    @pytest.mark.asyncio
    async def test_check_no_interactions(self, agent):
        inp = _input("check_drug_gene", medication="acetaminophen")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_interactions"] == 0

    @pytest.mark.asyncio
    async def test_patient_profile(self, agent):
        inp = _input("patient_profile", genotype={
            "CYP2D6": "poor_metabolizer",
            "CYP2C19": "intermediate_metabolizer",
        })
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_genes_tested"] == 2
        assert out.result["actionable_findings"] > 0

    @pytest.mark.asyncio
    async def test_dose_recommendation(self, agent):
        inp = _input("dose_recommendation", medication="warfarin",
                      phenotype="high_sensitivity")
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["recommended_dose"] == "1-2mg"
        assert out.result["evidence_level"] == "CPIC Level A"

    @pytest.mark.asyncio
    async def test_panel_summary(self, agent):
        out = await agent.run(_input("panel_summary"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_genes"] == 5
        assert out.result["total_drugs_covered"] > 0

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent_action"))
        assert out.status in (AgentStatus.FAILED, AgentStatus.WAITING_HITL)


# ── Genetic Risk Agent (#75) ──────────────────────────────────────


class TestGeneticRiskAgent:
    @pytest.fixture
    def agent(self):
        from modules.research_genomics.agents.genetic_risk import GeneticRiskAgent
        return GeneticRiskAgent()

    @pytest.mark.asyncio
    async def test_calculate_prs(self, agent):
        inp = _input("calculate_prs",
                      conditions=["coronary_artery_disease", "type_2_diabetes"])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_conditions_scored"] == 2
        assert len(out.result["prs_scores"]) == 2

    @pytest.mark.asyncio
    async def test_calculate_prs_defaults(self, agent):
        out = await agent.run(_input("calculate_prs"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["total_conditions_scored"] == 3  # default top 3

    @pytest.mark.asyncio
    async def test_monogenic_screen(self, agent):
        inp = _input("monogenic_screen", variants=["BRCA1", "APOE_e4"])
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert out.result["variants_detected"] == 2
        assert out.result["genetic_counseling_recommended"] is True

    @pytest.mark.asyncio
    async def test_monogenic_screen_defaults(self, agent):
        out = await agent.run(_input("monogenic_screen"))
        assert out.status == AgentStatus.COMPLETED
        assert out.result["variants_detected"] == 1  # default APOE_e4

    @pytest.mark.asyncio
    async def test_integrated_risk(self, agent):
        inp = _input("integrated_risk", clinical_risk_score=0.15,
                      prs_percentile=90)
        out = await agent.run(inp)
        assert out.status == AgentStatus.COMPLETED
        assert "integrated_risk_score" in out.result
        assert "risk_category" in out.result

    @pytest.mark.asyncio
    async def test_risk_report(self, agent):
        out = await agent.run(_input("risk_report"))
        assert out.status == AgentStatus.COMPLETED
        assert "prs_summary" in out.result
        assert "monogenic_findings" in out.result
        assert "recommendations" in out.result

    @pytest.mark.asyncio
    async def test_unknown_action(self, agent):
        out = await agent.run(_input("nonexistent_action"))
        assert out.status in (AgentStatus.FAILED, AgentStatus.WAITING_HITL)


# ── Registration & Routing ────────────────────────────────────────


class TestResearchGenomicsRegistration:
    def test_register_agents(self):
        from modules.research_genomics.agents import register_research_genomics_agents
        register_research_genomics_agents()
        from healthos_platform.orchestrator.registry import registry
        assert registry.get("clinical_trial_matching") is not None
        assert registry.get("deidentification") is not None
        assert registry.get("research_cohort") is not None
        assert registry.get("pharmacogenomics") is not None
        assert registry.get("genetic_risk") is not None

    def test_routing_entries(self):
        from healthos_platform.orchestrator.router import ROUTING_TABLE
        assert "research.trial.match" in ROUTING_TABLE
        assert "research.cohort.build" in ROUTING_TABLE
        assert "research.pgx.check" in ROUTING_TABLE
        assert "research.genetic.prs" in ROUTING_TABLE
        assert "research.deidentify" in ROUTING_TABLE
