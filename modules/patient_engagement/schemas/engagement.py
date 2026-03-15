"""Patient Engagement module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    patient_id: UUID
    symptoms: list[str]
    duration: str = "unknown"
    severity: int = Field(5, ge=1, le=10)


class TriageResponse(BaseModel):
    urgency: str
    recommendation: str
    suggested_visit_type: str
    red_flags: list[str]


class SDOHScreening(BaseModel):
    patient_id: UUID
    responses: dict[str, str]


class SDOHResult(BaseModel):
    patient_id: str
    risk_domains: list[str]
    overall_risk: str
    interventions: list[str]


class CommunityResource(BaseModel):
    name: str
    category: str
    address: Optional[str] = None
    phone: Optional[str] = None
    eligibility: Optional[str] = None


class ContentAdaptation(BaseModel):
    content: str
    target_reading_level: int = Field(6, ge=1, le=12)
    language: str = "en"


class EngagementNudge(BaseModel):
    patient_id: UUID
    nudge_type: str = Field("reminder", description="reminder, encouragement, education")
    channel: str = Field("in_app", description="in_app, sms, email")
    message: Optional[str] = None
