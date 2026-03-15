"""
SDOH Assessment Service Layer.

Pure business-logic functions that mirror the Django model methods from
Inhealth-Capstone-project, adapted for async SQLAlchemy / FastAPI.
All risk-scoring and intervention-recommendation logic is preserved.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional, Sequence

from modules.sdoh.schemas.assessment import (
    InterventionItem,
    SDOHAssessmentCreate,
    SDOHAssessmentUpdate,
    SDOHRiskLevel,
)

logger = logging.getLogger("healthos.sdoh.service")


# ── Risk Calculation ─────────────────────────────────────────────────────────


def calculate_risk(
    food_security_score: int,
    housing_stability_score: int,
    transportation_score: int,
    social_support_score: int,
    financial_stress_score: int,
) -> tuple[int, SDOHRiskLevel]:
    """Compute total score and overall SDOH risk level.

    Mirrors ``SDOHAssessment.calculate_risk()`` from the Inhealth Django model.

    Returns
    -------
    tuple[int, SDOHRiskLevel]
        (total_score, risk_level)
    """
    total = (
        food_security_score
        + housing_stability_score
        + transportation_score
        + social_support_score
        + financial_stress_score
    )
    if total <= 4:
        level = SDOHRiskLevel.LOW
    elif total <= 10:
        level = SDOHRiskLevel.MEDIUM
    else:
        level = SDOHRiskLevel.HIGH
    return total, level


# ── Intervention Recommendations ─────────────────────────────────────────────


def generate_intervention_recommendations(
    food_security_score: int = 0,
    housing_stability_score: int = 0,
    transportation_score: int = 0,
    social_support_score: int = 0,
    financial_stress_score: int = 0,
) -> list[InterventionItem]:
    """Generate AI-recommended interventions based on domain scores.

    Preserves the full recommendation logic from the Inhealth Django model's
    ``get_intervention_recommendations()`` method.
    """
    recommendations: list[InterventionItem] = []

    if food_security_score >= 2:
        recommendations.append(InterventionItem(
            domain="food",
            priority="high" if food_security_score >= 3 else "medium",
            intervention="Refer to local food bank or SNAP enrollment",
            resources=["foodpantries.org", "benefits.gov/snap"],
        ))

    if housing_stability_score >= 2:
        recommendations.append(InterventionItem(
            domain="housing",
            priority="high" if housing_stability_score >= 3 else "medium",
            intervention="Connect with housing assistance programs and social worker",
            resources=["211.org", "hud.gov"],
        ))

    if transportation_score >= 2:
        recommendations.append(InterventionItem(
            domain="transportation",
            priority="medium",
            intervention="Arrange medical transportation or telehealth visits",
            resources=["Non-emergency medical transport", "Telehealth portal"],
        ))

    if social_support_score >= 2:
        recommendations.append(InterventionItem(
            domain="social_support",
            priority="medium",
            intervention="Refer to community support groups and senior services",
            resources=["eldercare.acl.gov", "NAMI"],
        ))

    if financial_stress_score >= 2:
        recommendations.append(InterventionItem(
            domain="financial",
            priority="high" if financial_stress_score >= 3 else "medium",
            intervention="Connect with financial assistance programs and prescription assistance",
            resources=["NeedyMeds.org", "RxAssist.org"],
        ))

    return recommendations


# ── CRUD Operations ──────────────────────────────────────────────────────────

# In-memory store for assessments.  Replace with async SQLAlchemy queries once
# the ``sdoh_assessments`` table is migrated into the shared model layer.

_assessments: dict[uuid.UUID, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_assessment(
    tenant_id: uuid.UUID,
    payload: SDOHAssessmentCreate,
) -> dict[str, Any]:
    """Create and persist a new SDOH assessment, computing risk automatically."""
    total_score, risk_level = calculate_risk(
        payload.food_security_score,
        payload.housing_stability_score,
        payload.transportation_score,
        payload.social_support_score,
        payload.financial_stress_score,
    )

    recommendations = generate_intervention_recommendations(
        payload.food_security_score,
        payload.housing_stability_score,
        payload.transportation_score,
        payload.social_support_score,
        payload.financial_stress_score,
    )

    assessment_id = uuid.uuid4()
    now = _now()
    record: dict[str, Any] = {
        "id": assessment_id,
        "tenant_id": tenant_id,
        "patient_id": payload.patient_id,
        "assessed_by_id": payload.assessed_by_id,
        # Domain scores
        "food_security_score": payload.food_security_score,
        "housing_stability_score": payload.housing_stability_score,
        "transportation_score": payload.transportation_score,
        "social_support_score": payload.social_support_score,
        "financial_stress_score": payload.financial_stress_score,
        # Additional factors
        "education_barrier": payload.education_barrier,
        "employment_barrier": payload.employment_barrier,
        "health_literacy_barrier": payload.health_literacy_barrier,
        "interpersonal_violence": payload.interpersonal_violence,
        "substance_use_concern": payload.substance_use_concern,
        "mental_health_concern": payload.mental_health_concern,
        # Computed
        "overall_sdoh_risk": risk_level,
        "total_score": total_score,
        # Interventions
        "interventions_recommended": [r.model_dump() for r in (payload.interventions_recommended or [])],
        "community_resources_referred": payload.community_resources_referred or [],
        "intervention_recommendations": [r.model_dump() for r in recommendations],
        # Dates
        "follow_up_date": payload.follow_up_date,
        "notes": payload.notes or "",
        "assessment_date": payload.assessment_date or date.today(),
        "created_at": now,
        "updated_at": now,
    }

    _assessments[assessment_id] = record
    logger.info("sdoh.assessment.created", extra={"id": str(assessment_id), "risk": risk_level.value})
    return record


async def get_assessment(
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
) -> Optional[dict[str, Any]]:
    """Retrieve a single assessment by ID, scoped to tenant."""
    record = _assessments.get(assessment_id)
    if record and record["tenant_id"] == tenant_id:
        return record
    return None


async def list_assessments(
    tenant_id: uuid.UUID,
    patient_id: Optional[uuid.UUID] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List assessments for a tenant with optional filters."""
    results = [
        r for r in _assessments.values()
        if r["tenant_id"] == tenant_id
    ]
    if patient_id:
        results = [r for r in results if r["patient_id"] == patient_id]
    if risk_level:
        results = [r for r in results if r["overall_sdoh_risk"].value == risk_level]

    # Sort by assessment_date descending
    results.sort(key=lambda r: r["assessment_date"], reverse=True)
    return results[offset : offset + limit]


async def update_assessment(
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
    payload: SDOHAssessmentUpdate,
) -> Optional[dict[str, Any]]:
    """Partially update an assessment, recalculating risk if scores changed."""
    record = _assessments.get(assessment_id)
    if not record or record["tenant_id"] != tenant_id:
        return None

    update_data = payload.model_dump(exclude_none=True)
    # Serialize InterventionItems if present
    if "interventions_recommended" in update_data:
        update_data["interventions_recommended"] = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in update_data["interventions_recommended"]
        ]

    record.update(update_data)
    record["updated_at"] = _now()

    # Recalculate risk
    total_score, risk_level = calculate_risk(
        record["food_security_score"],
        record["housing_stability_score"],
        record["transportation_score"],
        record["social_support_score"],
        record["financial_stress_score"],
    )
    record["total_score"] = total_score
    record["overall_sdoh_risk"] = risk_level

    # Regenerate recommendations
    record["intervention_recommendations"] = [
        r.model_dump() for r in generate_intervention_recommendations(
            record["food_security_score"],
            record["housing_stability_score"],
            record["transportation_score"],
            record["social_support_score"],
            record["financial_stress_score"],
        )
    ]

    logger.info("sdoh.assessment.updated", extra={"id": str(assessment_id)})
    return record


async def delete_assessment(
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
) -> bool:
    """Delete an assessment. Returns True if deleted, False if not found."""
    record = _assessments.get(assessment_id)
    if record and record["tenant_id"] == tenant_id:
        del _assessments[assessment_id]
        return True
    return False


async def update_intervention_status(
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
    domain: str,
    new_status: str,
) -> Optional[dict[str, Any]]:
    """Update the status of a specific intervention within an assessment."""
    record = _assessments.get(assessment_id)
    if not record or record["tenant_id"] != tenant_id:
        return None

    interventions = record.get("interventions_recommended", [])
    for intervention in interventions:
        if intervention.get("domain") == domain:
            intervention["status"] = new_status

    record["interventions_recommended"] = interventions
    record["updated_at"] = _now()
    return record


async def get_high_risk_assessments(
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return assessments with HIGH SDOH risk, sorted by total_score descending."""
    results = [
        r for r in _assessments.values()
        if r["tenant_id"] == tenant_id
        and r["overall_sdoh_risk"] == SDOHRiskLevel.HIGH
    ]
    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results[:limit]


async def get_screening_summary(
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Compute aggregate screening statistics for a tenant."""
    records = [r for r in _assessments.values() if r["tenant_id"] == tenant_id]
    total = len(records)
    if total == 0:
        return {
            "total_assessments": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "avg_total_score": 0.0,
            "top_domains": [],
        }

    high = sum(1 for r in records if r["overall_sdoh_risk"] == SDOHRiskLevel.HIGH)
    medium = sum(1 for r in records if r["overall_sdoh_risk"] == SDOHRiskLevel.MEDIUM)
    low = sum(1 for r in records if r["overall_sdoh_risk"] == SDOHRiskLevel.LOW)
    avg_score = sum(r["total_score"] for r in records) / total

    # Calculate top contributing domains
    domain_totals: dict[str, int] = {
        "food_security": 0,
        "housing_stability": 0,
        "transportation": 0,
        "social_support": 0,
        "financial_stress": 0,
    }
    for r in records:
        domain_totals["food_security"] += r["food_security_score"]
        domain_totals["housing_stability"] += r["housing_stability_score"]
        domain_totals["transportation"] += r["transportation_score"]
        domain_totals["social_support"] += r["social_support_score"]
        domain_totals["financial_stress"] += r["financial_stress_score"]

    top_domains = sorted(
        [{"domain": k, "total_score": v, "avg_score": round(v / total, 2)} for k, v in domain_totals.items()],
        key=lambda d: d["total_score"],
        reverse=True,
    )

    return {
        "total_assessments": total,
        "high_risk_count": high,
        "medium_risk_count": medium,
        "low_risk_count": low,
        "avg_total_score": round(avg_score, 2),
        "top_domains": top_domains,
    }
