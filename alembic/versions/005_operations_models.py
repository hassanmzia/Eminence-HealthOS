"""Add prior_auth_requests, insurance_verifications, referrals, and billing_claims tables.

Revision ID: 005_operations_models
Revises: 004_telehealth_models
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "005_operations_models"
down_revision = "004_telehealth_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Prior Auth Requests ────────────────────────────────────────────────
    op.create_table(
        "prior_auth_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=True),
        sa.Column("payer_id", sa.String(100), nullable=False),
        sa.Column("cpt_code", sa.String(20), nullable=False),
        sa.Column("icd10_codes", JSONB, server_default="[]"),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("urgency", sa.String(20), server_default="routine"),
        sa.Column("clinical_necessity_score", sa.Float, nullable=True),
        sa.Column("documentation_checklist", JSONB, server_default="{}"),
        sa.Column("payer_response", JSONB, nullable=True),
        sa.Column("auth_number", sa.String(100), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_recommendation", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prior_auth_requests_tenant_status", "prior_auth_requests", ["tenant_id", "status"])
    op.create_index("ix_prior_auth_requests_patient", "prior_auth_requests", ["patient_id"])

    # ── Insurance Verifications ────────────────────────────────────────────
    op.create_table(
        "insurance_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("payer_name", sa.String(255), nullable=False),
        sa.Column("payer_id", sa.String(100), nullable=False),
        sa.Column("member_id", sa.String(100), nullable=False),
        sa.Column("group_number", sa.String(100), nullable=True),
        sa.Column("plan_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("eligibility_status", sa.String(30), server_default="active"),
        sa.Column("coverage_start", sa.Date, nullable=True),
        sa.Column("coverage_end", sa.Date, nullable=True),
        sa.Column("copay_amount", sa.Float, nullable=True),
        sa.Column("deductible", sa.Float, nullable=True),
        sa.Column("deductible_met", sa.Float, nullable=True),
        sa.Column("out_of_pocket_max", sa.Float, nullable=True),
        sa.Column("benefits_summary", JSONB, server_default="{}"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_insurance_verifications_tenant_status", "insurance_verifications", ["tenant_id", "status"])
    op.create_index("ix_insurance_verifications_patient", "insurance_verifications", ["patient_id"])

    # ── Referrals ──────────────────────────────────────────────────────────
    op.create_table(
        "referrals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("referring_provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("specialist_provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=True),
        sa.Column("referral_type", sa.String(50), nullable=False),
        sa.Column("specialty", sa.String(100), nullable=False),
        sa.Column("urgency", sa.String(20), server_default="routine"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("clinical_notes", sa.Text, nullable=True),
        sa.Column("icd10_codes", JSONB, server_default="[]"),
        sa.Column("turnaround_days", sa.Integer, nullable=False, server_default="14"),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_referrals_tenant_status", "referrals", ["tenant_id", "status"])
    op.create_index("ix_referrals_patient", "referrals", ["patient_id"])

    # ── Billing Claims ─────────────────────────────────────────────────────
    op.create_table(
        "billing_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("rendering_provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("payer_id", sa.String(100), nullable=False),
        sa.Column("claim_number", sa.String(100), unique=True, nullable=True),
        sa.Column("claim_type", sa.String(30), server_default="professional"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("cpt_codes", JSONB, server_default="[]"),
        sa.Column("icd10_codes", JSONB, server_default="[]"),
        sa.Column("total_charge", sa.Float, nullable=False),
        sa.Column("allowed_amount", sa.Float, nullable=True),
        sa.Column("paid_amount", sa.Float, nullable=True),
        sa.Column("patient_responsibility", sa.Float, nullable=True),
        sa.Column("place_of_service", sa.String(10), nullable=False),
        sa.Column("billing_notes", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("adjudicated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("denial_reason", sa.Text, nullable=True),
        sa.Column("edi_transaction_id", sa.String(100), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_billing_claims_tenant_status", "billing_claims", ["tenant_id", "status"])
    op.create_index("ix_billing_claims_patient", "billing_claims", ["patient_id"])
    op.create_index("ix_billing_claims_encounter", "billing_claims", ["encounter_id"])


def downgrade() -> None:
    op.drop_table("billing_claims")
    op.drop_table("referrals")
    op.drop_table("insurance_verifications")
    op.drop_table("prior_auth_requests")
