"""
Eminence HealthOS — Billing & Insurance Routes (Phase 5)
Invoice management, payment tracking, insurance information.
Imported from InhealthUSA Billing/Payment/InsuranceInformation models.
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
    require_admin,
    require_office_admin_or_above,
)
from healthos_platform.database import get_db
from healthos_platform.models import Billing, BillingItem, InsuranceInformation, Payment

router = APIRouter(prefix="/billing", tags=["billing"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class BillingItemCreate(BaseModel):
    service_code: str
    service_description: str
    quantity: int = 1
    unit_price: float


class BillingCreate(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID | None = None
    invoice_number: str
    billing_date: date
    due_date: date
    items: list[BillingItemCreate] = []
    notes: str | None = None


class BillingItemResponse(BaseModel):
    id: uuid.UUID
    service_code: str
    service_description: str
    quantity: int
    unit_price: float
    total_price: float
    model_config = {"from_attributes": True}


class BillingResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    invoice_number: str
    billing_date: date
    due_date: date
    total_amount: float
    amount_paid: float
    amount_due: float
    status: str
    notes: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    billing_id: uuid.UUID
    patient_id: uuid.UUID
    amount: float
    payment_method: str
    transaction_id: str | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    billing_id: uuid.UUID
    amount: float
    payment_method: str
    transaction_id: str | None
    status: str
    payment_date: datetime
    model_config = {"from_attributes": True}


class InsuranceCreate(BaseModel):
    patient_id: uuid.UUID
    provider_name: str
    policy_number: str
    group_number: str | None = None
    policyholder_name: str
    policyholder_relationship: str
    effective_date: date
    termination_date: date | None = None
    is_primary: bool = True
    copay_amount: float | None = None
    deductible_amount: float | None = None


class InsuranceResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_name: str
    policy_number: str
    group_number: str | None
    policyholder_name: str
    policyholder_relationship: str
    effective_date: date
    termination_date: date | None
    is_primary: bool
    copay_amount: float | None
    deductible_amount: float | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Billing Endpoints ────────────────────────────────────────────────────────


@router.get("/invoices", response_model=list[BillingResponse])
async def list_invoices(
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Billing).where(Billing.org_id == ctx.org_id)
    if patient_id:
        q = q.where(Billing.patient_id == patient_id)
    if status:
        q = q.where(Billing.status == status)
    # Patients can only see their own
    if ctx.role == "patient":
        from healthos_platform.models import Patient
        pat_result = await db.execute(
            select(Patient.id).where(Patient.org_id == ctx.org_id).limit(1)
        )
        # For now just filter by org; full patient-user link TBD
    offset = (page - 1) * page_size
    result = await db.execute(q.order_by(Billing.billing_date.desc()).offset(offset).limit(page_size))
    return result.scalars().all()


@router.post("/invoices", response_model=BillingResponse, status_code=201)
async def create_invoice(
    body: BillingCreate,
    ctx: TenantContext = Depends(require_office_admin_or_above),
    db: AsyncSession = Depends(get_db),
):
    total = sum(item.quantity * item.unit_price for item in body.items)
    billing = Billing(
        org_id=ctx.org_id,
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        invoice_number=body.invoice_number,
        billing_date=body.billing_date,
        due_date=body.due_date,
        total_amount=total,
        amount_paid=0,
        amount_due=total,
        notes=body.notes,
    )
    db.add(billing)
    await db.flush()

    for item in body.items:
        line = BillingItem(
            billing_id=billing.id,
            service_code=item.service_code,
            service_description=item.service_description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
        )
        db.add(line)

    return billing


@router.get("/invoices/{invoice_id}", response_model=BillingResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Billing).where(Billing.id == invoice_id, Billing.org_id == ctx.org_id)
    )
    billing = result.scalar_one_or_none()
    if not billing:
        raise HTTPException(404, "Invoice not found")
    return billing


@router.get("/invoices/{invoice_id}/items", response_model=list[BillingItemResponse])
async def get_invoice_items(
    invoice_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BillingItem).where(BillingItem.billing_id == invoice_id)
    )
    return result.scalars().all()


# ── Payment Endpoints ────────────────────────────────────────────────────────


@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(
    patient_id: uuid.UUID | None = None,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Payment).where(Payment.org_id == ctx.org_id)
    if patient_id:
        q = q.where(Payment.patient_id == patient_id)
    result = await db.execute(q.order_by(Payment.payment_date.desc()))
    return result.scalars().all()


@router.post("/payments", response_model=PaymentResponse, status_code=201)
async def record_payment(
    body: PaymentCreate,
    ctx: TenantContext = Depends(require_office_admin_or_above),
    db: AsyncSession = Depends(get_db),
):
    # Get billing to update
    billing_result = await db.execute(
        select(Billing).where(Billing.id == body.billing_id, Billing.org_id == ctx.org_id)
    )
    billing = billing_result.scalar_one_or_none()
    if not billing:
        raise HTTPException(404, "Invoice not found")

    payment = Payment(
        org_id=ctx.org_id,
        patient_id=body.patient_id,
        billing_id=body.billing_id,
        amount=body.amount,
        payment_method=body.payment_method,
        transaction_id=body.transaction_id,
        notes=body.notes,
    )
    db.add(payment)

    # Update billing amounts
    billing.amount_paid = float(billing.amount_paid or 0) + body.amount
    billing.amount_due = float(billing.total_amount) - float(billing.amount_paid)
    if billing.amount_due <= 0:
        billing.status = "Paid"
        billing.amount_due = 0
    else:
        billing.status = "Partially Paid"

    await db.flush()
    return payment


# ── Insurance Endpoints ──────────────────────────────────────────────────────


@router.get("/insurance/{patient_id}", response_model=list[InsuranceResponse])
async def list_insurance(
    patient_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsuranceInformation)
        .where(InsuranceInformation.patient_id == patient_id, InsuranceInformation.org_id == ctx.org_id)
        .order_by(InsuranceInformation.is_primary.desc())
    )
    return result.scalars().all()


@router.post("/insurance", response_model=InsuranceResponse, status_code=201)
async def create_insurance(
    body: InsuranceCreate,
    ctx: TenantContext = Depends(require_office_admin_or_above),
    db: AsyncSession = Depends(get_db),
):
    ins = InsuranceInformation(org_id=ctx.org_id, **body.model_dump())
    db.add(ins)
    await db.flush()
    return ins


@router.put("/insurance/{insurance_id}", response_model=InsuranceResponse)
async def update_insurance(
    insurance_id: uuid.UUID,
    body: InsuranceCreate,
    ctx: TenantContext = Depends(require_office_admin_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InsuranceInformation).where(
            InsuranceInformation.id == insurance_id, InsuranceInformation.org_id == ctx.org_id
        )
    )
    ins = result.scalar_one_or_none()
    if not ins:
        raise HTTPException(404, "Insurance not found")
    for k, v in body.model_dump().items():
        setattr(ins, k, v)
    await db.flush()
    return ins
