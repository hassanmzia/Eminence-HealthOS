-- ============================================================
-- Eminence HealthOS - Row Level Security Policies
-- Reference schema for Alembic migrations
--
-- Enables multi-tenant isolation at the database level.
-- Depends on: all prior schema files (01-05)
-- ============================================================

-- ============================================================
-- Enable Row Level Security on all PHI tables
-- ============================================================
ALTER TABLE fhir_patient ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_observation ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_condition ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_medication_request ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_diagnostic_report ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_appointment ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_care_plan ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_allergy_intolerance ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_encounter ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_procedure ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_immunization ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_document_reference ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_demographics ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_engagement ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_registration ENABLE ROW LEVEL SECURITY;
ALTER TABLE care_gap ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification ENABLE ROW LEVEL SECURITY;
ALTER TABLE sdoh_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_score ENABLE ROW LEVEL SECURITY;
ALTER TABLE claim ENABLE ROW LEVEL SECURITY;
ALTER TABLE rpm_episode ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_action_log ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Tenant Isolation Policies
-- Each row is visible only when app.tenant_id matches.
-- ============================================================
CREATE POLICY tenant_isolation ON fhir_patient
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_observation
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_condition
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_medication_request
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_diagnostic_report
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_appointment
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_care_plan
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_allergy_intolerance
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_encounter
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_procedure
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_immunization
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_document_reference
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON patient_demographics
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON patient_engagement
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON device_registration
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON care_gap
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON notification
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON sdoh_assessment
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON risk_score
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON claim
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON rpm_episode
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON agent_action_log
    USING (tenant_id IS NULL OR tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ============================================================
-- Superuser / Migration bypass policy
-- Set app.bypass_rls = 'true' to bypass tenant isolation
-- (used by Alembic migrations and admin operations)
-- ============================================================
CREATE POLICY superuser_bypass ON fhir_patient
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_observation
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_condition
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_medication_request
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_diagnostic_report
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_appointment
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_care_plan
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_allergy_intolerance
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_encounter
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_procedure
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_immunization
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_document_reference
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON patient_demographics
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON patient_engagement
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON device_registration
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON care_gap
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON notification
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON sdoh_assessment
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON risk_score
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON claim
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON rpm_episode
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON agent_action_log
    USING (current_setting('app.bypass_rls', true) = 'true');
