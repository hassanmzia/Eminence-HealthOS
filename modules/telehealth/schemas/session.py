"""Telehealth session schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    patient_id: UUID
    visit_type: str = Field("follow_up", description="follow_up, new_patient, urgent, wellness")
    urgency: str = Field("routine", description="routine, same_day, urgent, emergency")
    chief_complaint: Optional[str] = None
    symptoms: list[str] = []


class SessionResponse(BaseModel):
    session_id: str
    patient_id: str
    visit_type: str
    urgency: str
    status: str
    estimated_wait_minutes: int
    created_at: str


class SymptomCheckRequest(BaseModel):
    symptoms: list[str]
    duration: str = "unknown"
    severity_rating: int = Field(5, ge=1, le=10)
    additional_notes: Optional[str] = None


class SymptomCheckResponse(BaseModel):
    chief_complaint: str
    symptoms: list[str]
    systems_affected: list[str]
    red_flags: list[str]
    urgency: str
    recommended_visit_type: str
