"""Pharmacy module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PrescriptionCreate(BaseModel):
    patient_id: UUID
    medication_name: str
    dosage: str
    frequency: str
    duration_days: int = Field(30, ge=1)
    prescriber_id: Optional[UUID] = None
    notes: Optional[str] = None


class PrescriptionResponse(BaseModel):
    prescription_id: str
    patient_id: str
    medication_name: str
    dosage: str
    frequency: str
    status: str
    created_at: str


class DrugInteractionCheck(BaseModel):
    medications: list[str]
    patient_id: Optional[UUID] = None


class DrugInteractionResult(BaseModel):
    interactions: list[dict]
    severity: str
    recommendation: str


class FormularyCheck(BaseModel):
    medication_name: str
    insurance_plan: Optional[str] = None


class RefillRequest(BaseModel):
    prescription_id: str
    patient_id: UUID
    pharmacy_id: Optional[str] = None
