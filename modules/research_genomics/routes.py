"""Research & Genomics module API routes — clinical trial matching, de-identification, cohort building, pharmacogenomics, and genetic risk scoring."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput, parse_patient_id
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/research-genomics", tags=["research-genomics"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Clinical Trial Matching ───────────────────────────────────────────────


@router.post("/trials/match")
async def match_trials(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Match a patient to eligible clinical trials."""
    from modules.research_genomics.agents.clinical_trial_matching import ClinicalTrialMatchingAgent

    agent = ClinicalTrialMatchingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.trials.match",
        context={"action": "match_trials", **body},
    ))
    return output.result


@router.post("/trials/eligibility")
async def check_eligibility(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check patient eligibility for a specific trial."""
    from modules.research_genomics.agents.clinical_trial_matching import ClinicalTrialMatchingAgent

    agent = ClinicalTrialMatchingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.trials.eligibility",
        context={"action": "check_eligibility", **body},
    ))
    return output.result


@router.get("/trials/enrollment")
async def enrollment_status(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get enrollment status for all active trials."""
    from modules.research_genomics.agents.clinical_trial_matching import ClinicalTrialMatchingAgent

    agent = ClinicalTrialMatchingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.trials.enrollment",
        context={"action": "enrollment_status"},
    ))
    return output.result


# ── De-Identification ─────────────────────────────────────────────────────


@router.post("/deidentify/dataset")
async def deidentify_dataset(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """De-identify a dataset using HIPAA Safe Harbor method."""
    from modules.research_genomics.agents.deidentification import DeIdentificationAgent

    agent = DeIdentificationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.deidentify.dataset",
        context={"action": "deidentify_dataset", **body},
    ))
    return output.result


@router.post("/deidentify/verify")
async def verify_deidentification(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Verify that a dataset is properly de-identified."""
    from modules.research_genomics.agents.deidentification import DeIdentificationAgent

    agent = DeIdentificationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.deidentify.verify",
        context={"action": "verify_deidentification", **body},
    ))
    return output.result


@router.post("/deidentify/scan")
async def scan_phi(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Scan data for PHI before export."""
    from modules.research_genomics.agents.deidentification import DeIdentificationAgent

    agent = DeIdentificationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.deidentify.scan",
        context={"action": "scan_phi", **body},
    ))
    return output.result


@router.post("/deidentify/export")
async def export_dataset(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Export a de-identified dataset for research use."""
    from modules.research_genomics.agents.deidentification import DeIdentificationAgent

    agent = DeIdentificationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.deidentify.export",
        context={"action": "export_dataset", **body},
    ))
    return output.result


# ── Research Cohort ───────────────────────────────────────────────────────


@router.post("/cohort/build")
async def build_cohort(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Build a research cohort from clinical criteria."""
    from modules.research_genomics.agents.research_cohort import ResearchCohortAgent

    agent = ResearchCohortAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.cohort.build",
        context={"action": "build_cohort", **body},
    ))
    return output.result


@router.post("/cohort/characteristics")
async def cohort_characteristics(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Analyze cohort demographic and clinical characteristics."""
    from modules.research_genomics.agents.research_cohort import ResearchCohortAgent

    agent = ResearchCohortAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.cohort.characteristics",
        context={"action": "cohort_characteristics", **body},
    ))
    return output.result


@router.post("/cohort/compare")
async def compare_cohorts(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Compare two cohorts for balance assessment."""
    from modules.research_genomics.agents.research_cohort import ResearchCohortAgent

    agent = ResearchCohortAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.cohort.compare",
        context={"action": "compare_cohorts", **body},
    ))
    return output.result


@router.get("/cohort/templates")
async def list_templates(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """List available cohort templates."""
    from modules.research_genomics.agents.research_cohort import ResearchCohortAgent

    agent = ResearchCohortAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.cohort.templates",
        context={"action": "list_templates"},
    ))
    return output.result


# ── Pharmacogenomics ──────────────────────────────────────────────────────


@router.post("/pgx/check")
async def check_drug_gene(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Check drug-gene interactions for a medication."""
    from modules.research_genomics.agents.pharmacogenomics import PharmacogenomicsAgent

    agent = PharmacogenomicsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.pgx.check",
        context={"action": "check_drug_gene", **body},
    ))
    return output.result


@router.post("/pgx/profile")
async def patient_pgx_profile(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get pharmacogenomic profile for a patient."""
    from modules.research_genomics.agents.pharmacogenomics import PharmacogenomicsAgent

    agent = PharmacogenomicsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.pgx.profile",
        context={"action": "patient_profile", **body},
    ))
    return output.result


@router.post("/pgx/dose")
async def dose_recommendation(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get PGx-guided dose recommendation."""
    from modules.research_genomics.agents.pharmacogenomics import PharmacogenomicsAgent

    agent = PharmacogenomicsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.pgx.dose",
        context={"action": "dose_recommendation", **body},
    ))
    return output.result


@router.get("/pgx/panel")
async def panel_summary(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get pharmacogenomic panel summary."""
    from modules.research_genomics.agents.pharmacogenomics import PharmacogenomicsAgent

    agent = PharmacogenomicsAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="research.pgx.panel",
        context={"action": "panel_summary"},
    ))
    return output.result


# ── Genetic Risk ──────────────────────────────────────────────────────────


@router.post("/genetic/prs")
async def calculate_prs(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Calculate polygenic risk scores for a patient."""
    from modules.research_genomics.agents.genetic_risk import GeneticRiskAgent

    agent = GeneticRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.genetic.prs",
        context={"action": "calculate_prs", **body},
    ))
    return output.result


@router.post("/genetic/monogenic")
async def monogenic_screen(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Screen for high-impact monogenic variants."""
    from modules.research_genomics.agents.genetic_risk import GeneticRiskAgent

    agent = GeneticRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.genetic.monogenic",
        context={"action": "monogenic_screen", **body},
    ))
    return output.result


@router.post("/genetic/integrated-risk")
async def integrated_risk(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Calculate integrated clinical-genomic risk score."""
    from modules.research_genomics.agents.genetic_risk import GeneticRiskAgent

    agent = GeneticRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.genetic.integrated_risk",
        context={"action": "integrated_risk", **body},
    ))
    return output.result


@router.post("/genetic/report")
async def risk_report(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate comprehensive genetic risk report."""
    from modules.research_genomics.agents.genetic_risk import GeneticRiskAgent

    agent = GeneticRiskAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=parse_patient_id(body.get("patient_id")),
        trigger="research.genetic.report",
        context={"action": "risk_report", **body},
    ))
    return output.result
