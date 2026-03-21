"""
Eminence HealthOS — Clinical Data API Routes (Phase 2)
Normalized EHR models: Diagnosis, Prescription, Allergy, MedicalHistory,
SocialHistory, FamilyHistory, LabTest.
Imported from InhealthUSA clinical models.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from healthos_platform.api.middleware.tenant import (
    TenantContext,
    get_current_user,
    require_clinician,
)
from healthos_platform.security.rbac import Permission
from healthos_platform.database import get_db
from healthos_platform.models import (
    Allergy,
    Diagnosis,
    FamilyHistory,
    LabTest,
    MedicalHistory,
    Prescription,
    SocialHistory,
)

router = APIRouter(prefix="/clinical", tags=["clinical"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class DiagnosisCreate(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID | None = None
    diagnosis_description: str
    icd10_code: str | None = None
    icd11_code: str | None = None
    diagnosis_type: str = "Primary"
    status: str = "Active"
    notes: str | None = None


class DiagnosisResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID | None
    diagnosis_description: str
    icd10_code: str | None
    icd11_code: str | None
    diagnosis_type: str
    status: str
    diagnosed_by: uuid.UUID | None
    diagnosed_at: datetime
    notes: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class PrescriptionCreate(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID | None = None
    medication_name: str
    dosage: str
    frequency: str
    route: str | None = None
    start_date: date
    end_date: date | None = None
    refills: int = 0
    quantity: int | None = None
    instructions: str | None = None
    status: str = "Active"
    notes: str | None = None


class PrescriptionResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None
    medication_name: str
    dosage: str
    frequency: str
    route: str | None
    start_date: date
    end_date: date | None
    refills: int
    quantity: int | None
    instructions: str | None
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AllergyCreate(BaseModel):
    patient_id: uuid.UUID
    allergen: str
    allergy_type: str
    severity: str
    reaction: str | None = None
    onset_date: date | None = None
    notes: str | None = None


class AllergyResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    allergen: str
    allergy_type: str
    severity: str
    reaction: str | None
    onset_date: date | None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class MedicalHistoryCreate(BaseModel):
    patient_id: uuid.UUID
    condition: str
    diagnosis_date: date | None = None
    resolution_date: date | None = None
    status: str = "Active"
    treatment_notes: str | None = None


class MedicalHistoryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    condition: str
    diagnosis_date: date | None
    resolution_date: date | None
    status: str
    treatment_notes: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class SocialHistoryCreate(BaseModel):
    patient_id: uuid.UUID
    smoking_status: str = "Never"
    alcohol_use: str = "Never"
    drug_use: str | None = None
    occupation: str | None = None
    marital_status: str | None = None
    living_situation: str | None = None
    exercise: str | None = None
    diet: str | None = None
    notes: str | None = None


class SocialHistoryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    smoking_status: str
    alcohol_use: str
    occupation: str | None
    marital_status: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class FamilyHistoryCreate(BaseModel):
    patient_id: uuid.UUID
    relationship: str
    condition: str
    age_at_diagnosis: int | None = None
    is_alive: bool = True
    age_at_death: int | None = None
    cause_of_death: str | None = None
    notes: str | None = None


class FamilyHistoryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    relationship: str
    condition: str
    age_at_diagnosis: int | None
    is_alive: bool
    cause_of_death: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class LabTestCreate(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID | None = None
    test_name: str
    test_code: str | None = None
    status: str = "Ordered"
    notes: str | None = None


class LabTestUpdate(BaseModel):
    status: str | None = None
    result_value: str | None = None
    result_unit: str | None = None
    reference_range: str | None = None
    abnormal_flag: bool | None = None
    interpretation: str | None = None
    notes: str | None = None


class LabTestResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None
    test_name: str
    test_code: str | None
    ordered_date: datetime
    sample_collected_date: datetime | None
    result_date: datetime | None
    status: str
    result_value: str | None
    result_unit: str | None
    reference_range: str | None
    abnormal_flag: bool
    interpretation: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSIS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/diagnoses/{patient_id}", response_model=list[DiagnosisResponse])
async def list_diagnoses(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Diagnosis)
        .where(Diagnosis.patient_id == patient_id, Diagnosis.org_id == ctx.org_id)
        .order_by(Diagnosis.diagnosed_at.desc())
    )
    return result.scalars().all()


@router.post("/diagnoses", response_model=DiagnosisResponse, status_code=201)
async def create_diagnosis(
    body: DiagnosisCreate,
    ctx: TenantContext = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
):
    diag = Diagnosis(org_id=ctx.org_id, diagnosed_by=ctx.user_id, **body.model_dump())
    db.add(diag)
    await db.flush()
    return diag


# ═══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/prescriptions/{patient_id}", response_model=list[PrescriptionResponse])
async def list_prescriptions(
    patient_id: uuid.UUID,
    status: str | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Prescription).where(
        Prescription.patient_id == patient_id, Prescription.org_id == ctx.org_id
    )
    if status:
        q = q.where(Prescription.status == status)
    result = await db.execute(q.order_by(Prescription.start_date.desc()))
    return result.scalars().all()


@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=201)
async def create_prescription(
    body: PrescriptionCreate,
    ctx: TenantContext = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
):
    rx = Prescription(org_id=ctx.org_id, provider_id=ctx.user_id, **body.model_dump())
    db.add(rx)
    await db.flush()
    return rx


# ═══════════════════════════════════════════════════════════════════════════════
# ALLERGY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/allergies/{patient_id}", response_model=list[AllergyResponse])
async def list_allergies(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Allergy)
        .where(Allergy.patient_id == patient_id, Allergy.org_id == ctx.org_id, Allergy.is_active.is_(True))
        .order_by(Allergy.severity.desc())
    )
    return result.scalars().all()


@router.post("/allergies", response_model=AllergyResponse, status_code=201)
async def create_allergy(
    body: AllergyCreate,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx.require_permission(Permission.ALLERGY_WRITE)
    allergy = Allergy(org_id=ctx.org_id, **body.model_dump())
    db.add(allergy)
    await db.flush()
    return allergy


# ═══════════════════════════════════════════════════════════════════════════════
# MEDICAL HISTORY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/medical-history/{patient_id}", response_model=list[MedicalHistoryResponse])
async def list_medical_history(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalHistory)
        .where(MedicalHistory.patient_id == patient_id, MedicalHistory.org_id == ctx.org_id)
        .order_by(MedicalHistory.diagnosis_date.desc())
    )
    return result.scalars().all()


@router.post("/medical-history", response_model=MedicalHistoryResponse, status_code=201)
async def create_medical_history(
    body: MedicalHistoryCreate,
    ctx: TenantContext = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
):
    mh = MedicalHistory(org_id=ctx.org_id, **body.model_dump())
    db.add(mh)
    await db.flush()
    return mh


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL HISTORY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/social-history/{patient_id}", response_model=list[SocialHistoryResponse])
async def list_social_history(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SocialHistory)
        .where(SocialHistory.patient_id == patient_id, SocialHistory.org_id == ctx.org_id)
        .order_by(SocialHistory.recorded_date.desc())
    )
    return result.scalars().all()


@router.post("/social-history", response_model=SocialHistoryResponse, status_code=201)
async def create_social_history(
    body: SocialHistoryCreate,
    ctx: TenantContext = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
):
    sh = SocialHistory(org_id=ctx.org_id, **body.model_dump())
    db.add(sh)
    await db.flush()
    return sh


# ═══════════════════════════════════════════════════════════════════════════════
# FAMILY HISTORY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/family-history/{patient_id}", response_model=list[FamilyHistoryResponse])
async def list_family_history(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamilyHistory)
        .where(FamilyHistory.patient_id == patient_id, FamilyHistory.org_id == ctx.org_id)
    )
    return result.scalars().all()


@router.post("/family-history", response_model=FamilyHistoryResponse, status_code=201)
async def create_family_history(
    body: FamilyHistoryCreate,
    ctx: TenantContext = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
):
    fh = FamilyHistory(org_id=ctx.org_id, **body.model_dump())
    db.add(fh)
    await db.flush()
    return fh


# ═══════════════════════════════════════════════════════════════════════════════
# LAB TEST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/labs/{patient_id}", response_model=list[LabTestResponse])
async def list_lab_tests(
    patient_id: uuid.UUID,
    status: str | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(LabTest).where(LabTest.patient_id == patient_id, LabTest.org_id == ctx.org_id)
    if status:
        q = q.where(LabTest.status == status)
    result = await db.execute(q.order_by(LabTest.ordered_date.desc()))
    return result.scalars().all()


@router.post("/labs", response_model=LabTestResponse, status_code=201)
async def create_lab_test(
    body: LabTestCreate,
    ctx: TenantContext = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
):
    lab = LabTest(org_id=ctx.org_id, provider_id=ctx.user_id, **body.model_dump())
    db.add(lab)
    await db.flush()
    return lab


@router.patch("/labs/{lab_id}", response_model=LabTestResponse)
async def update_lab_test(
    lab_id: uuid.UUID,
    body: LabTestUpdate,
    ctx: TenantContext = Depends(require_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LabTest).where(LabTest.id == lab_id, LabTest.org_id == ctx.org_id)
    )
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(404, "Lab test not found")

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(lab, k, v)

    if body.result_value and not lab.result_date:
        from datetime import datetime, timezone
        lab.result_date = datetime.now(timezone.utc)

    await db.flush()
    return lab
