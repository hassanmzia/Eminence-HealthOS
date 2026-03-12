"""Revenue Cycle Management module API routes — charge capture, claims, denials, revenue integrity, payments."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends

from healthos_platform.agents.types import AgentInput
from services.api.middleware.auth import CurrentUser, require_auth, require_role
from services.api.middleware.tenant import get_tenant_id

router = APIRouter()

DEFAULT_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Charge Capture ─────────────────────────────────────────────────────────


@router.post("/charges/capture")
async def capture_charges(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Capture billable charges from an encounter."""
    from modules.rcm.agents.charge_capture import ChargeCaptureAgent

    agent = ChargeCaptureAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="rcm.charges.capture",
        context={"action": "capture_charges", **body},
    ))
    return output.result


@router.post("/charges/estimate")
async def estimate_reimbursement(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Estimate reimbursement for a set of codes."""
    from modules.rcm.agents.charge_capture import ChargeCaptureAgent

    agent = ChargeCaptureAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.charges.estimate",
        context={"action": "estimate_reimbursement", **body},
    ))
    return output.result


# ── Claims Optimization ────────────────────────────────────────────────────


@router.post("/claims/optimize")
async def optimize_claim(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Scrub and optimize a claim before submission."""
    from modules.rcm.agents.claims_optimization import ClaimsOptimizationAgent

    agent = ClaimsOptimizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.claims.optimize",
        context={"action": "optimize_claim", **body},
    ))
    return output.result


@router.get("/claims/clean-rate")
async def clean_claim_rate(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get clean claim rate metrics."""
    from modules.rcm.agents.claims_optimization import ClaimsOptimizationAgent

    agent = ClaimsOptimizationAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.claims.clean_rate",
        context={"action": "clean_claim_rate"},
    ))
    return output.result


# ── Denial Management ──────────────────────────────────────────────────────


@router.post("/denials/analyze")
async def analyze_denial(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Analyze a denied claim and recommend appeal strategy."""
    from modules.rcm.agents.denial_management import DenialManagementAgent

    agent = DenialManagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.denials.analyze",
        context={"action": "analyze_denial", **body},
    ))
    return output.result


@router.post("/denials/appeal")
async def generate_appeal(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Generate an appeal letter for a denied claim."""
    from modules.rcm.agents.denial_management import DenialManagementAgent

    agent = DenialManagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.denials.appeal",
        context={"action": "generate_appeal", **body},
    ))
    return output.result


@router.get("/denials/trends")
async def denial_trends(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Get denial trend analysis."""
    from modules.rcm.agents.denial_management import DenialManagementAgent

    agent = DenialManagementAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.denials.trends",
        context={"action": "denial_trends"},
    ))
    return output.result


# ── Revenue Integrity ──────────────────────────────────────────────────────


@router.post("/integrity/scan")
async def scan_chart(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Pre-bill chart scan for missed diagnoses and under-coding."""
    from modules.rcm.agents.revenue_integrity import RevenueIntegrityAgent

    agent = RevenueIntegrityAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="rcm.integrity.scan",
        context={"action": "scan_chart", **body},
    ))
    return output.result


@router.post("/integrity/hcc-gaps")
async def hcc_gap_analysis(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """HCC coding gap analysis for risk adjustment."""
    from modules.rcm.agents.revenue_integrity import RevenueIntegrityAgent

    agent = RevenueIntegrityAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        patient_id=uuid.UUID(body["patient_id"]) if body.get("patient_id") else None,
        trigger="rcm.integrity.hcc_gaps",
        context={"action": "hcc_gap_analysis", **body},
    ))
    return output.result


@router.get("/integrity/leakage")
async def revenue_leakage(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Revenue leakage report."""
    from modules.rcm.agents.revenue_integrity import RevenueIntegrityAgent

    agent = RevenueIntegrityAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.integrity.leakage",
        context={"action": "revenue_leakage_report"},
    ))
    return output.result


# ── Payment Posting ────────────────────────────────────────────────────────


@router.post("/payments/post")
async def post_payment(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Post a payment against a claim."""
    from modules.rcm.agents.payment_posting import PaymentPostingAgent

    agent = PaymentPostingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.payments.post",
        context={"action": "post_payment", **body},
    ))
    return output.result


@router.post("/payments/reconcile")
async def reconcile_era(
    body: dict[str, Any],
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Reconcile an ERA/835 against claims."""
    from modules.rcm.agents.payment_posting import PaymentPostingAgent

    agent = PaymentPostingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.payments.reconcile",
        context={"action": "reconcile_era", **body},
    ))
    return output.result


@router.get("/payments/ar-aging")
async def ar_aging(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Accounts receivable aging report."""
    from modules.rcm.agents.payment_posting import PaymentPostingAgent

    agent = PaymentPostingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.payments.ar_aging",
        context={"action": "ar_aging_report"},
    ))
    return output.result


@router.get("/payments/collections")
async def collections_summary(
    tenant_id: str = Depends(get_tenant_id),
    user: CurrentUser = Depends(require_auth),
):
    """Collection performance summary."""
    from modules.rcm.agents.payment_posting import PaymentPostingAgent

    agent = PaymentPostingAgent()
    output = await agent.run(AgentInput(
        org_id=DEFAULT_ORG,
        trigger="rcm.payments.collections",
        context={"action": "collections_summary"},
    ))
    return output.result
