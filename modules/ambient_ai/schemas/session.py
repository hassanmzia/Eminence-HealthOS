"""Ambient AI module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AmbientSessionStart(BaseModel):
    encounter_id: str
    patient_id: UUID
    provider_id: Optional[UUID] = None
    language: str = "en"


class TranscriptionSegment(BaseModel):
    speaker: str
    text: str
    timestamp_start: float
    timestamp_end: float
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class DiarizationResult(BaseModel):
    segments: list[TranscriptionSegment]
    speakers_detected: int
    speaker_labels: dict[str, str]


class SOAPNoteGenerated(BaseModel):
    encounter_id: str
    subjective: str
    objective: str
    assessment: str
    plan: list[str]
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class AutoCodeResult(BaseModel):
    encounter_id: str
    icd10_codes: list[dict]
    cpt_codes: list[dict]
    confidence: float


class AttestationRequest(BaseModel):
    encounter_id: str
    provider_id: UUID
    note_id: str
    approved: bool = False
    amendments: Optional[str] = None
