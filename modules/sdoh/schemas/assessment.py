"""
Pydantic schemas for SDOH assessments.

Covers screening domain scores, intervention tracking, risk levels, and
response envelopes consumed by FastAPI routes.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────────────────────


class SDOHRiskLevel(str, Enum):
    LOW = "low"          # Total 0-4
    MEDIUM = "medium"    # Total 5-10
    HIGH = "high"        # Total 11-20


# ── Nested models ────────────────────────────────────────────────────────────


class InterventionItem(BaseModel):
    """A single SDOH intervention recommendation or referral."""
    domain: str
    priority: str = "medium"
    intervention: str
    resources: list[str] = Field(default_factory=list)
    status: str = "pending"


class CommunityResource(BaseModel):
    """A matched community resource from RAG / vector search."""
    title: str
    description: str = ""
    url: str = ""
    phone: str = ""
    relevance_score: float = 0.0


# ── Request schemas ──────────────────────────────────────────────────────────


class SDOHAssessmentCreate(BaseModel):
    """Create a new SDOH screening assessment."""
    patient_id: uuid.UUID
    assessed_by_id: Optional[uuid.UUID] = None

    # Domain scores (0=none, 1=mild, 2=moderate, 3=severe, 4=extreme)
    food_security_score: int = Field(default=0, ge=0, le=4)
    housing_stability_score: int = Field(default=0, ge=0, le=4)
    transportation_score: int = Field(default=0, ge=0, le=4)
    social_support_score: int = Field(default=0, ge=0, le=4)
    financial_stress_score: int = Field(default=0, ge=0, le=4)

    # Additional boolean factors
    education_barrier: bool = False
    employment_barrier: bool = False
    health_literacy_barrier: bool = False
    interpersonal_violence: bool = False
    substance_use_concern: bool = False
    mental_health_concern: bool = False

    # Optional fields
    interventions_recommended: list[InterventionItem] = Field(default_factory=list)
    community_resources_referred: list[dict[str, Any]] = Field(default_factory=list)
    follow_up_date: Optional[date] = None
    notes: str = ""
    assessment_date: Optional[date] = None

    @field_validator(
        "food_security_score",
        "housing_stability_score",
        "transportation_score",
        "social_support_score",
        "financial_stress_score",
    )
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        if not 0 <= v <= 4:
            raise ValueError("Domain score must be between 0 and 4")
        return v


class SDOHAssessmentUpdate(BaseModel):
    """Partial update for an existing assessment."""
    food_security_score: Optional[int] = Field(default=None, ge=0, le=4)
    housing_stability_score: Optional[int] = Field(default=None, ge=0, le=4)
    transportation_score: Optional[int] = Field(default=None, ge=0, le=4)
    social_support_score: Optional[int] = Field(default=None, ge=0, le=4)
    financial_stress_score: Optional[int] = Field(default=None, ge=0, le=4)

    education_barrier: Optional[bool] = None
    employment_barrier: Optional[bool] = None
    health_literacy_barrier: Optional[bool] = None
    interpersonal_violence: Optional[bool] = None
    substance_use_concern: Optional[bool] = None
    mental_health_concern: Optional[bool] = None

    interventions_recommended: Optional[list[InterventionItem]] = None
    community_resources_referred: Optional[list[dict[str, Any]]] = None
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None


class InterventionStatusUpdate(BaseModel):
    """Update the status of a single intervention by domain."""
    domain: str
    status: str  # pending, in_progress, completed, declined


# ── Response schemas ─────────────────────────────────────────────────────────


class SDOHAssessmentResponse(BaseModel):
    """Full SDOH assessment record returned to the client."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    assessed_by_id: Optional[uuid.UUID] = None

    # Domain scores
    food_security_score: int
    housing_stability_score: int
    transportation_score: int
    social_support_score: int
    financial_stress_score: int

    # Additional factors
    education_barrier: bool
    employment_barrier: bool
    health_literacy_barrier: bool
    interpersonal_violence: bool
    substance_use_concern: bool
    mental_health_concern: bool

    # Computed
    overall_sdoh_risk: SDOHRiskLevel
    total_score: int

    # Interventions
    interventions_recommended: list[InterventionItem] = Field(default_factory=list)
    community_resources_referred: list[dict[str, Any]] = Field(default_factory=list)
    intervention_recommendations: list[InterventionItem] = Field(default_factory=list)

    # Dates
    follow_up_date: Optional[date] = None
    notes: str = ""
    assessment_date: date
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SDOHRecommendationsResponse(BaseModel):
    """Intervention recommendations for a single assessment."""
    assessment_id: uuid.UUID
    overall_risk: SDOHRiskLevel
    total_score: int
    recommendations: list[InterventionItem]


class SDOHHighRiskResponse(BaseModel):
    """Summary of high-risk SDOH patients."""
    count: int
    assessments: list[SDOHAssessmentResponse]


class SDOHScreeningSummary(BaseModel):
    """Aggregate screening statistics for a tenant."""
    total_assessments: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    avg_total_score: float = 0.0
    top_domains: list[dict[str, Any]] = Field(default_factory=list)
