"""Add all InhealthUSA-imported tables (Phases 1-6):
  Phase 1: hospitals, departments, provider_profiles, nurse_profiles, office_admin_profiles
  Phase 2: diagnoses, prescriptions, allergies, medical_histories, social_histories, family_histories, lab_tests
  Phase 3: devices, device_api_keys, device_data_readings, device_activity_logs, device_alert_rules
  Phase 4: messages, notifications, notification_preferences, vital_sign_alert_responses
  Phase 5: billings, billing_items, payments, insurance_information
  Phase 6: authentication_configs, password_histories, user_sessions
  Plus: ai_proposed_treatment_plans, doctor_treatment_plans

Revision ID: 008_inhealth_usa
Revises: 007_analytics_models
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "008_inhealth_usa"
down_revision = "007_analytics_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1: RBAC — Hospital, Department, Role-specific Profiles
    # ══════════════════════════════════════════════════════════════════════════

    op.create_table(
        "hospitals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(50)),
        sa.Column("zip_code", sa.String(20)),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("website", sa.String(500)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_hospitals_org", "hospitals", ["org_id"])

    op.create_table(
        "departments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("hospital_id", UUID(as_uuid=True), sa.ForeignKey("hospitals.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("head_of_department", sa.String(255)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_departments_hospital", "departments", ["hospital_id"])

    op.create_table(
        "provider_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("specialty", sa.String(100), nullable=False),
        sa.Column("npi", sa.String(20), nullable=False),
        sa.Column("license_number", sa.String(100)),
        sa.Column("hospital_id", UUID(as_uuid=True), sa.ForeignKey("hospitals.id")),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_provider_npi", "provider_profiles", ["npi"], unique=True)
    op.create_index("idx_provider_org", "provider_profiles", ["org_id"])

    op.create_table(
        "nurse_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("specialty", sa.String(100), server_default="General"),
        sa.Column("license_number", sa.String(100), nullable=False),
        sa.Column("hospital_id", UUID(as_uuid=True), sa.ForeignKey("hospitals.id")),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_nurse_license", "nurse_profiles", ["license_number"], unique=True)
    op.create_index("idx_nurse_org", "nurse_profiles", ["org_id"])

    op.create_table(
        "office_admin_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("position", sa.String(100), server_default="Office Administrator"),
        sa.Column("employee_id", sa.String(50), nullable=False),
        sa.Column("hospital_id", UUID(as_uuid=True), sa.ForeignKey("hospitals.id")),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_officeadmin_employee", "office_admin_profiles", ["employee_id"], unique=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2: EHR Clinical Models
    # ══════════════════════════════════════════════════════════════════════════

    op.create_table(
        "diagnoses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id")),
        sa.Column("diagnosis_description", sa.Text, nullable=False),
        sa.Column("icd10_code", sa.String(20)),
        sa.Column("icd11_code", sa.String(20)),
        sa.Column("diagnosis_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("diagnosed_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("diagnosed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_diagnosis_patient", "diagnoses", ["patient_id", "diagnosed_at"])
    op.create_index("idx_diagnosis_icd10", "diagnoses", ["icd10_code"])

    op.create_table(
        "prescriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id")),
        sa.Column("medication_name", sa.String(255), nullable=False),
        sa.Column("dosage", sa.String(100), nullable=False),
        sa.Column("frequency", sa.String(100), nullable=False),
        sa.Column("route", sa.String(50)),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("refills", sa.Integer, server_default="0"),
        sa.Column("quantity", sa.Integer),
        sa.Column("instructions", sa.Text),
        sa.Column("status", sa.String(20), server_default="Active"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_prescription_patient", "prescriptions", ["patient_id", "start_date"])
    op.create_index("idx_prescription_status", "prescriptions", ["org_id", "status"])

    op.create_table(
        "allergies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("allergen", sa.String(255), nullable=False),
        sa.Column("allergy_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("reaction", sa.Text),
        sa.Column("onset_date", sa.Date),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_allergy_patient", "allergies", ["patient_id"])

    op.create_table(
        "medical_histories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("condition", sa.String(255), nullable=False),
        sa.Column("diagnosis_date", sa.Date),
        sa.Column("resolution_date", sa.Date),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("treatment_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_medhist_patient", "medical_histories", ["patient_id"])

    op.create_table(
        "social_histories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("smoking_status", sa.String(20), server_default="Never"),
        sa.Column("alcohol_use", sa.String(20), server_default="Never"),
        sa.Column("drug_use", sa.Text),
        sa.Column("occupation", sa.String(255)),
        sa.Column("marital_status", sa.String(20)),
        sa.Column("living_situation", sa.Text),
        sa.Column("exercise", sa.Text),
        sa.Column("diet", sa.Text),
        sa.Column("recorded_date", sa.Date, server_default=sa.func.current_date()),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_socialhist_patient", "social_histories", ["patient_id"])

    op.create_table(
        "family_histories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("relationship", sa.String(50), nullable=False),
        sa.Column("condition", sa.String(255), nullable=False),
        sa.Column("age_at_diagnosis", sa.Integer),
        sa.Column("is_alive", sa.Boolean, server_default="true"),
        sa.Column("age_at_death", sa.Integer),
        sa.Column("cause_of_death", sa.String(255)),
        sa.Column("recorded_date", sa.Date, server_default=sa.func.current_date()),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_familyhist_patient", "family_histories", ["patient_id"])

    op.create_table(
        "lab_tests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id")),
        sa.Column("test_name", sa.String(255), nullable=False),
        sa.Column("test_code", sa.String(50)),
        sa.Column("ordered_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sample_collected_date", sa.DateTime(timezone=True)),
        sa.Column("result_date", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), server_default="Ordered"),
        sa.Column("result_value", sa.Text),
        sa.Column("result_unit", sa.String(50)),
        sa.Column("reference_range", sa.String(100)),
        sa.Column("abnormal_flag", sa.Boolean, server_default="false"),
        sa.Column("interpretation", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_labtest_patient", "lab_tests", ["patient_id", "ordered_date"])
    op.create_index("idx_labtest_status", "lab_tests", ["org_id", "status"])

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3: IoT Device API & Data Ingestion
    # ══════════════════════════════════════════════════════════════════════════

    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("device_unique_id", sa.String(255), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False),
        sa.Column("manufacturer", sa.String(255)),
        sa.Column("model_number", sa.String(100)),
        sa.Column("serial_number", sa.String(100)),
        sa.Column("firmware_version", sa.String(50)),
        sa.Column("status", sa.String(20), server_default="Active"),
        sa.Column("last_sync", sa.DateTime(timezone=True)),
        sa.Column("battery_level", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_device_unique_id", "devices", ["device_unique_id"], unique=True)
    op.create_index("idx_device_patient", "devices", ["patient_id"])
    op.create_index("idx_device_org", "devices", ["org_id"])

    op.create_table(
        "device_api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("key_name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("hashed_key", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used", sa.DateTime(timezone=True)),
        sa.Column("can_write_vitals", sa.Boolean, server_default="true"),
        sa.Column("can_read_patient", sa.Boolean, server_default="false"),
        sa.Column("request_count_today", sa.Integer, server_default="0"),
        sa.Column("last_reset_date", sa.Date, server_default=sa.func.current_date()),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_apikey_prefix", "device_api_keys", ["key_prefix"], unique=True)
    op.create_index("idx_apikey_device_active", "device_api_keys", ["device_id", "is_active"])

    op.create_table(
        "device_data_readings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("reading_type", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("signal_quality", sa.Integer),
        sa.Column("battery_level", sa.Integer),
        sa.Column("processed", sa.Boolean, server_default="false"),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("vital_sign_id", UUID(as_uuid=True)),
        sa.Column("device_firmware", sa.String(50)),
        sa.Column("notes", sa.Text),
    )
    op.create_index("idx_reading_device_time", "device_data_readings", ["device_id", "timestamp"])
    op.create_index("idx_reading_patient_time", "device_data_readings", ["patient_id", "timestamp"])
    op.create_index("idx_reading_type_processed", "device_data_readings", ["reading_type", "processed"])

    op.create_table(
        "device_activity_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id")),
        sa.Column("api_key_id", UUID(as_uuid=True), sa.ForeignKey("device_api_keys.id")),
        sa.Column("action_type", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
        sa.Column("endpoint", sa.String(255)),
        sa.Column("http_method", sa.String(10)),
        sa.Column("status_code", sa.Integer),
        sa.Column("response_time_ms", sa.Integer),
        sa.Column("details", JSONB),
        sa.Column("error_message", sa.Text),
    )
    op.create_index("idx_devlog_device_time", "device_activity_logs", ["device_id", "timestamp"])
    op.create_index("idx_devlog_action_time", "device_activity_logs", ["action_type", "timestamp"])

    op.create_table(
        "device_alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id")),
        sa.Column("rule_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("condition", sa.String(10), nullable=False),
        sa.Column("threshold_value", sa.Float, nullable=False),
        sa.Column("alert_level", sa.String(10), nullable=False),
        sa.Column("alert_message", sa.Text, nullable=False),
        sa.Column("notify_patient", sa.Boolean, server_default="false"),
        sa.Column("notify_provider", sa.Boolean, server_default="true"),
        sa.Column("notification_email", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_alertrule_patient", "device_alert_rules", ["patient_id"])

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 4: Messaging & Notifications
    # ══════════════════════════════════════════════════════════════════════════

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("sender_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("parent_message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_message_sender", "messages", ["sender_id", "created_at"])
    op.create_index("idx_message_recipient", "messages", ["recipient_id", "created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("notification_type", sa.String(20), nullable=False),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("link", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_notification_user", "notifications", ["user_id", "created_at"])
    op.create_index("idx_notification_type", "notifications", ["notification_type", "is_read"])

    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("email_enabled", sa.Boolean, server_default="true"),
        sa.Column("email_emergency", sa.Boolean, server_default="true"),
        sa.Column("email_critical", sa.Boolean, server_default="true"),
        sa.Column("email_warning", sa.Boolean, server_default="true"),
        sa.Column("sms_enabled", sa.Boolean, server_default="false"),
        sa.Column("sms_emergency", sa.Boolean, server_default="true"),
        sa.Column("sms_critical", sa.Boolean, server_default="true"),
        sa.Column("sms_warning", sa.Boolean, server_default="false"),
        sa.Column("whatsapp_enabled", sa.Boolean, server_default="false"),
        sa.Column("whatsapp_number", sa.String(20)),
        sa.Column("whatsapp_emergency", sa.Boolean, server_default="true"),
        sa.Column("whatsapp_critical", sa.Boolean, server_default="true"),
        sa.Column("whatsapp_warning", sa.Boolean, server_default="false"),
        sa.Column("enable_quiet_hours", sa.Boolean, server_default="false"),
        sa.Column("quiet_start_time", sa.Time),
        sa.Column("quiet_end_time", sa.Time),
        sa.Column("digest_mode", sa.Boolean, server_default="false"),
        sa.Column("digest_frequency_hours", sa.Integer, server_default="24"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "vital_sign_alert_responses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vital_id", UUID(as_uuid=True), sa.ForeignKey("vitals.id")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("alert_type", sa.String(20), nullable=False),
        sa.Column("patient_response_status", sa.String(20), server_default="none"),
        sa.Column("patient_wants_doctor", sa.Boolean, server_default="false"),
        sa.Column("patient_wants_nurse", sa.Boolean, server_default="false"),
        sa.Column("patient_wants_ems", sa.Boolean, server_default="false"),
        sa.Column("patient_response_time", sa.DateTime(timezone=True)),
        sa.Column("patient_response_method", sa.String(20)),
        sa.Column("timeout_minutes", sa.Integer, server_default="15"),
        sa.Column("auto_escalated", sa.Boolean, server_default="false"),
        sa.Column("auto_escalation_time", sa.DateTime(timezone=True)),
        sa.Column("doctor_notified", sa.Boolean, server_default="false"),
        sa.Column("nurse_notified", sa.Boolean, server_default="false"),
        sa.Column("ems_notified", sa.Boolean, server_default="false"),
        sa.Column("notifications_sent_at", sa.DateTime(timezone=True)),
        sa.Column("response_token", UUID(as_uuid=True), unique=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 5: Billing & Insurance
    # ══════════════════════════════════════════════════════════════════════════

    op.create_table(
        "billings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id")),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("billing_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(10, 2), server_default="0"),
        sa.Column("amount_due", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="Pending"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_billing_patient", "billings", ["patient_id", "billing_date"])
    op.create_index("idx_billing_status", "billings", ["org_id", "status"])
    op.create_index("idx_billing_invoice", "billings", ["invoice_number"], unique=True)

    op.create_table(
        "billing_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("billing_id", UUID(as_uuid=True), sa.ForeignKey("billings.id"), nullable=False),
        sa.Column("service_code", sa.String(50), nullable=False),
        sa.Column("service_description", sa.Text, nullable=False),
        sa.Column("quantity", sa.Integer, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("billing_id", UUID(as_uuid=True), sa.ForeignKey("billings.id"), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("transaction_id", sa.String(255)),
        sa.Column("status", sa.String(20), server_default="Completed"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_payment_patient", "payments", ["patient_id", "payment_date"])
    op.create_index("idx_payment_billing", "payments", ["billing_id"])

    op.create_table(
        "insurance_information",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_name", sa.String(255), nullable=False),
        sa.Column("policy_number", sa.String(100), nullable=False),
        sa.Column("group_number", sa.String(100)),
        sa.Column("policyholder_name", sa.String(255), nullable=False),
        sa.Column("policyholder_relationship", sa.String(50), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("termination_date", sa.Date),
        sa.Column("is_primary", sa.Boolean, server_default="true"),
        sa.Column("copay_amount", sa.Numeric(10, 2)),
        sa.Column("deductible_amount", sa.Numeric(10, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_insurance_patient", "insurance_information", ["patient_id"])

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 6: Enterprise Auth
    # ══════════════════════════════════════════════════════════════════════════

    op.create_table(
        "authentication_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("auth_method", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="false"),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "password_histories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_token", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
        sa.Column("last_activity", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_session_user", "user_sessions", ["user_id"])
    op.create_index("idx_session_token", "user_sessions", ["session_token"], unique=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Treatment Plans (AI-proposed + Doctor-created)
    # ══════════════════════════════════════════════════════════════════════════

    op.create_table(
        "ai_proposed_treatment_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("proposed_treatment", sa.Text, nullable=False),
        sa.Column("medications_suggested", sa.Text),
        sa.Column("lifestyle_recommendations", sa.Text),
        sa.Column("follow_up_recommendations", sa.Text),
        sa.Column("warnings_and_precautions", sa.Text),
        sa.Column("vital_signs_data", JSONB, server_default="{}"),
        sa.Column("diagnosis_data", JSONB, server_default="{}"),
        sa.Column("lab_test_data", JSONB, server_default="{}"),
        sa.Column("medical_history_data", JSONB, server_default="{}"),
        sa.Column("ai_model_name", sa.String(100)),
        sa.Column("ai_model_version", sa.String(50)),
        sa.Column("generation_time_seconds", sa.Numeric(8, 3)),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("doctor_notes", sa.Text),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ai_plan_patient_status", "ai_proposed_treatment_plans", ["patient_id", "status"])
    op.create_index("ix_ai_plan_provider_status", "ai_proposed_treatment_plans", ["provider_id", "status"])

    op.create_table(
        "doctor_treatment_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("plan_title", sa.String(255), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("encounter_id", UUID(as_uuid=True), sa.ForeignKey("encounters.id")),
        sa.Column("ai_proposal_id", UUID(as_uuid=True), sa.ForeignKey("ai_proposed_treatment_plans.id")),
        sa.Column("chief_complaint", sa.Text),
        sa.Column("assessment", sa.Text),
        sa.Column("treatment_goals", sa.Text, nullable=False),
        sa.Column("medications", sa.Text),
        sa.Column("procedures", sa.Text),
        sa.Column("lifestyle_modifications", sa.Text),
        sa.Column("dietary_recommendations", sa.Text),
        sa.Column("exercise_recommendations", sa.Text),
        sa.Column("follow_up_instructions", sa.Text),
        sa.Column("warning_signs", sa.Text),
        sa.Column("emergency_instructions", sa.Text),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("plan_start_date", sa.Date),
        sa.Column("plan_end_date", sa.Date),
        sa.Column("next_review_date", sa.Date),
        sa.Column("is_visible_to_patient", sa.Boolean, server_default="false"),
        sa.Column("patient_viewed_at", sa.DateTime(timezone=True)),
        sa.Column("patient_acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("patient_feedback", sa.Text),
        sa.Column("additional_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_doctor_plan_patient_status", "doctor_treatment_plans", ["patient_id", "status"])
    op.create_index("ix_doctor_plan_provider", "doctor_treatment_plans", ["provider_id", "status"])


def downgrade() -> None:
    op.drop_table("doctor_treatment_plans")
    op.drop_table("ai_proposed_treatment_plans")
    op.drop_table("user_sessions")
    op.drop_table("password_histories")
    op.drop_table("authentication_configs")
    op.drop_table("insurance_information")
    op.drop_table("payments")
    op.drop_table("billing_items")
    op.drop_table("billings")
    op.drop_table("vital_sign_alert_responses")
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
    op.drop_table("messages")
    op.drop_table("device_alert_rules")
    op.drop_table("device_activity_logs")
    op.drop_table("device_data_readings")
    op.drop_table("device_api_keys")
    op.drop_table("devices")
    op.drop_table("lab_tests")
    op.drop_table("family_histories")
    op.drop_table("social_histories")
    op.drop_table("medical_histories")
    op.drop_table("allergies")
    op.drop_table("prescriptions")
    op.drop_table("diagnoses")
    op.drop_table("office_admin_profiles")
    op.drop_table("nurse_profiles")
    op.drop_table("provider_profiles")
    op.drop_table("departments")
    op.drop_table("hospitals")
