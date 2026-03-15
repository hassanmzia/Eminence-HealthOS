"""Research & Genomics module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TrialMatchRequest(BaseModel):
    patient_id: UUID
    conditions: list[str]
    medications: list[str] = []
    age: Optional[int] = None
    include_phase: list[str] = Field(default=["2", "3", "4"])


class TrialMatchResult(BaseModel):
    trial_id: str
    title: str
    phase: str
    eligibility_score: float
    location: Optional[str] = None
    status: str


class DeidentifyRequest(BaseModel):
    dataset_id: str
    method: str = Field("safe_harbor", description="safe_harbor, expert_determination")
    fields_to_protect: list[str] = []


class CohortBuild(BaseModel):
    name: str
    criteria: dict
    min_size: int = Field(10, ge=1)
    include_demographics: bool = True


class PGxCheckRequest(BaseModel):
    patient_id: UUID
    medication: str
    gene: Optional[str] = None


class PGxResult(BaseModel):
    patient_id: str
    medication: str
    gene: str
    phenotype: str
    recommendation: str
    dose_adjustment: Optional[str] = None


class GeneticRiskRequest(BaseModel):
    patient_id: UUID
    conditions: list[str]
    include_prs: bool = True
