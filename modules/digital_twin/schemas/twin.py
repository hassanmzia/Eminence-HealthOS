"""Digital Twin module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TwinBuild(BaseModel):
    patient_id: UUID
    include_genomics: bool = False
    include_social_determinants: bool = True
    time_horizon_years: int = Field(5, ge=1, le=30)


class TwinResponse(BaseModel):
    twin_id: str
    patient_id: str
    status: str
    health_score: float
    risk_factors: list[str]
    created_at: str


class ScenarioSimulation(BaseModel):
    twin_id: str
    scenario_type: str = Field(..., description="medication, lifestyle, treatment_stop")
    parameters: dict


class ScenarioResult(BaseModel):
    twin_id: str
    scenario_type: str
    projected_outcome: dict
    confidence: float
    time_horizon: str


class TrajectoryForecast(BaseModel):
    twin_id: str
    metrics: list[str]
    horizon_months: int = Field(12, ge=1, le=120)


class CareOptimization(BaseModel):
    twin_id: str
    target_outcomes: list[str]
    constraints: Optional[dict] = None
