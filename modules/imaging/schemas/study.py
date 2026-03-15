"""Imaging module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StudyIngest(BaseModel):
    patient_id: UUID
    modality: str = Field(..., description="CT, MRI, XR, US, NM, PET")
    accession_number: str
    study_description: Optional[str] = None
    referring_provider_id: Optional[UUID] = None
    priority: str = Field("routine", description="routine, stat, urgent")


class StudyResponse(BaseModel):
    study_id: str
    patient_id: str
    modality: str
    accession_number: str
    status: str
    created_at: str


class ImageAnalysisRequest(BaseModel):
    study_id: str
    analysis_type: str = Field("general", description="general, chest_xr, brain_mri, mammo")


class ImageAnalysisResult(BaseModel):
    study_id: str
    findings: list[dict]
    impression: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    critical_finding: bool = False


class RadiologyReport(BaseModel):
    study_id: str
    clinical_history: str
    technique: str
    findings: str
    impression: str
    provider_id: Optional[str] = None


class CriticalFinding(BaseModel):
    study_id: str
    finding: str
    severity: str = Field("high", description="moderate, high, critical")
    requires_immediate_action: bool = True
