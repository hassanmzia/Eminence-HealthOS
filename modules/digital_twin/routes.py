"""Digital Twin & Simulation module API routes — twin management, what-if scenarios, trajectory forecasting, and treatment optimization."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/digital-twin", tags=["digital-twin"])

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Patient Digital Twin ────────────────────────────────────────────────────


@router.post("/twin/build")
async def build_twin(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Build a patient digital twin from clinical data."""
    from modules.digital_twin.agents.patient_digital_twin import PatientDigitalTwinAgent

    agent = PatientDigitalTwinAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="digital_twin.build",
        context={"action": "build_twin", **body},
    ))
    return output.result


@router.post("/twin/update")
async def update_twin(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Update an existing digital twin with new observations."""
    from modules.digital_twin.agents.patient_digital_twin import PatientDigitalTwinAgent

    agent = PatientDigitalTwinAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="digital_twin.update",
        context={"action": "update_twin", **body},
    ))
    return output.result


@router.get("/twin/state")
async def get_twin_state(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get current digital twin state snapshot."""
    from modules.digital_twin.agents.patient_digital_twin import PatientDigitalTwinAgent

    agent = PatientDigitalTwinAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="digital_twin.get_state",
        context={"action": "get_state"},
    ))
    return output.result


@router.get("/twin/timeline")
async def get_health_timeline(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get projected health timeline for a patient's digital twin."""
    from modules.digital_twin.agents.patient_digital_twin import PatientDigitalTwinAgent

    agent = PatientDigitalTwinAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="digital_twin.health_timeline",
        context={"action": "health_timeline"},
    ))
    return output.result


# ── What-If Scenarios ───────────────────────────────────────────────────────


@router.post("/scenario/medication")
async def simulate_medication_change(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Simulate the effect of a medication change on patient vitals."""
    from modules.digital_twin.agents.whatif_scenario import WhatIfScenarioAgent

    agent = WhatIfScenarioAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="scenario.medication_change",
        context={"action": "simulate_medication_change", **body},
    ))
    return output.result


@router.post("/scenario/lifestyle")
async def simulate_lifestyle_change(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Simulate the impact of lifestyle changes on health metrics."""
    from modules.digital_twin.agents.whatif_scenario import WhatIfScenarioAgent

    agent = WhatIfScenarioAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="scenario.lifestyle_change",
        context={"action": "simulate_lifestyle_change", **body},
    ))
    return output.result


@router.post("/scenario/treatment-stop")
async def simulate_treatment_stop(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Simulate the projected deterioration from stopping a treatment."""
    from modules.digital_twin.agents.whatif_scenario import WhatIfScenarioAgent

    agent = WhatIfScenarioAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="scenario.treatment_stop",
        context={"action": "simulate_treatment_stop", **body},
    ))
    return output.result


@router.post("/scenario/compare")
async def compare_scenarios(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Compare multiple what-if scenarios side by side."""
    from modules.digital_twin.agents.whatif_scenario import WhatIfScenarioAgent

    agent = WhatIfScenarioAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="scenario.compare",
        context={"action": "compare_scenarios", **body},
    ))
    return output.result


# ── Predictive Trajectory ───────────────────────────────────────────────────


@router.post("/trajectory/forecast")
async def forecast_trajectory(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Forecast health trajectory over 30/60/90 days."""
    from modules.digital_twin.agents.predictive_trajectory import PredictiveTrajectoryAgent

    agent = PredictiveTrajectoryAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="trajectory.forecast",
        context={"action": "forecast", **body},
    ))
    return output.result


@router.get("/trajectory/trends")
async def get_trend_analysis(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get trend analysis for patient health metrics."""
    from modules.digital_twin.agents.predictive_trajectory import PredictiveTrajectoryAgent

    agent = PredictiveTrajectoryAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="trajectory.trend_analysis",
        context={"action": "trend_analysis"},
    ))
    return output.result


@router.post("/trajectory/deterioration")
async def assess_deterioration_risk(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Assess risk of clinical deterioration events."""
    from modules.digital_twin.agents.predictive_trajectory import PredictiveTrajectoryAgent

    agent = PredictiveTrajectoryAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="trajectory.deterioration_risk",
        context={"action": "deterioration_risk", **body},
    ))
    return output.result


# ── Treatment Optimization ──────────────────────────────────────────────────


@router.post("/optimize/plan")
async def optimize_care_plan(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Optimize care plan and generate alternative treatment strategies."""
    from modules.digital_twin.agents.treatment_optimization import TreatmentOptimizationAgent

    agent = TreatmentOptimizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="optimize.plan",
        context={"action": "optimize_plan", **body},
    ))
    return output.result


@router.post("/optimize/interventions")
async def rank_interventions(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Rank available interventions by efficacy, cost, and adherence profile."""
    from modules.digital_twin.agents.treatment_optimization import TreatmentOptimizationAgent

    agent = TreatmentOptimizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="optimize.rank_interventions",
        context={"action": "rank_interventions", **body},
    ))
    return output.result


@router.post("/optimize/cost-effectiveness")
async def cost_effectiveness_analysis(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Compare treatment options by QALY-based cost-effectiveness."""
    from modules.digital_twin.agents.treatment_optimization import TreatmentOptimizationAgent

    agent = TreatmentOptimizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="optimize.cost_effectiveness",
        context={"action": "cost_effectiveness", **body},
    ))
    return output.result
