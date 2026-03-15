"""Revenue Cycle Management module schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChargeCapture(BaseModel):
    encounter_id: str
    patient_id: UUID
    cpt_codes: list[str]
    icd10_codes: list[str]
    provider_id: Optional[UUID] = None
    place_of_service: str = "11"


class ClaimOptimize(BaseModel):
    claim_id: str
    cpt_codes: list[str]
    icd10_codes: list[str]
    modifiers: list[str] = []


class ClaimResponse(BaseModel):
    claim_id: str
    status: str
    estimated_reimbursement: float
    clean_claim: bool
    issues: list[str]


class DenialAnalysis(BaseModel):
    claim_id: str
    denial_code: str
    denial_reason: str
    payer: str


class AppealGeneration(BaseModel):
    claim_id: str
    denial_code: str
    supporting_documentation: list[str] = []


class PaymentPosting(BaseModel):
    claim_id: str
    payment_amount: float
    payer: str
    check_number: Optional[str] = None
    adjustment_codes: list[str] = []
