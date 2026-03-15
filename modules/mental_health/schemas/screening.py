"""Mental Health module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PHQ9Request(BaseModel):
    patient_id: UUID
    responses: list[int] = Field(..., min_length=9, max_length=9, description="9 items scored 0-3")


class GAD7Request(BaseModel):
    patient_id: UUID
    responses: list[int] = Field(..., min_length=7, max_length=7, description="7 items scored 0-3")


class ScreeningResult(BaseModel):
    patient_id: str
    instrument: str
    total_score: int
    severity: str
    recommendation: str
    risk_flags: list[str]


class CrisisAssessment(BaseModel):
    patient_id: UUID
    presenting_concern: str
    suicidal_ideation: bool = False
    self_harm: bool = False
    substance_use: bool = False


class CrisisResult(BaseModel):
    patient_id: str
    risk_level: str = Field(..., description="low, moderate, high, imminent")
    recommended_action: str
    safety_plan_needed: bool
    escalate: bool


class SafetyPlan(BaseModel):
    patient_id: str
    warning_signs: list[str]
    coping_strategies: list[str]
    support_contacts: list[dict]
    crisis_resources: list[dict]
    environmental_safety: list[str]


class TreatmentPlan(BaseModel):
    patient_id: UUID
    diagnoses: list[str]
    goals: list[str]
    interventions: list[str]
    medications: list[str] = []
    follow_up_weeks: int = Field(2, ge=1)


class MoodCheckIn(BaseModel):
    patient_id: UUID
    mood_rating: int = Field(..., ge=1, le=10)
    energy_level: int = Field(..., ge=1, le=10)
    sleep_quality: int = Field(..., ge=1, le=10)
    notes: Optional[str] = None
