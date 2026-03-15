-- ============================================================
-- Eminence HealthOS - Multi-Tenant Schema
-- Reference schema for Alembic migrations
--
-- NOTE: This must be run BEFORE 02_fhir_schema.sql since
-- the organizations table is referenced by fhir_patient
-- and other clinical tables.
--
-- The base organizations table is created by Alembic migration
-- 001_initial_schema.py. This script extends that table and
-- adds tenant configuration, API keys, RLS policies, and the
-- demo seed data.
-- ============================================================

-- ============================================================
-- Organizations (Tenants)
-- Extended version of the Alembic-managed organizations table.
-- If running standalone (outside Alembic), this creates the
-- full table. Otherwise the ALTER TABLE statements below add
-- columns that the Alembic migration does not yet include.
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identification
    name                        VARCHAR(500) NOT NULL,
    short_name                  VARCHAR(100),
    slug                        VARCHAR(100) UNIQUE NOT NULL,
    npi                         VARCHAR(20),
    tax_id_encrypted            BYTEA,
    cms_certification_number    VARCHAR(50),

    -- Organization type
    org_type                    VARCHAR(50) CHECK (org_type IN (
                                    'health_system','hospital','clinic','physician_group',
                                    'aco','mso','independent_practice','demo'
                                )),
    specialty                   VARCHAR(100),

    -- Contact
    address_line1               VARCHAR(500),
    address_line2               VARCHAR(200),
    city                        VARCHAR(100),
    state                       VARCHAR(2),
    zip                         VARCHAR(10),
    country                     VARCHAR(3) DEFAULT 'USA',
    phone                       VARCHAR(30),
    fax                         VARCHAR(30),
    website                     VARCHAR(500),

    -- Geographic
    location                    GEOMETRY(POINT, 4326),

    -- Status & tier
    status                      VARCHAR(20) CHECK (status IN (
                                    'active','inactive','suspended','demo','onboarding'
                                )) DEFAULT 'active',
    tier                        VARCHAR(50) CHECK (tier IN (
                                    'starter','professional','enterprise','custom'
                                )) DEFAULT 'starter',
    onboarded_at                TIMESTAMPTZ,
    contract_start_date         DATE,
    contract_end_date           DATE,

    -- Billing
    billing_email               VARCHAR(255),
    billing_contact             VARCHAR(200),
    patient_license_count       INTEGER,
    active_patient_count        INTEGER DEFAULT 0,

    -- Settings (JSONB bag for flexible config)
    settings                    JSONB DEFAULT '{}',

    -- HIPAA BAA
    hipaa_baa_signed            BOOLEAN DEFAULT FALSE,
    baa_signed_date             DATE,
    baa_signed_by               VARCHAR(200),

    -- Parent org (for health systems with multiple facilities)
    parent_org_id               UUID REFERENCES organizations(id),

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_org_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_org_status ON organizations(status);
CREATE INDEX IF NOT EXISTS idx_org_parent ON organizations(parent_org_id);
CREATE INDEX IF NOT EXISTS idx_org_location_gist ON organizations USING GIST(location);

-- ============================================================
-- Tenant Configuration
-- ============================================================
CREATE TABLE IF NOT EXISTS tenant_config (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Feature flags
    feature_flags               JSONB NOT NULL DEFAULT '{}',
    -- Expected keys: rpm_enabled, ccm_enabled, agents_enabled, ai_alerts_enabled,
    --                stemi_protocol, stroke_protocol, copd_protocol,
    --                neo4j_enabled, qdrant_enabled, hitl_required

    -- Agent configuration
    agent_config                JSONB NOT NULL DEFAULT '{}',
    -- Expected: enabled_agents, hitl_threshold, orchestration_mode, max_concurrent_pipelines

    -- Clinical thresholds (can be customized per tenant)
    clinical_thresholds         JSONB NOT NULL DEFAULT '{
        "glucose_critical_low": 50,
        "glucose_critical_high": 400,
        "glucose_high": 250,
        "systolic_critical": 180,
        "diastolic_critical": 120,
        "spo2_critical_low": 85,
        "spo2_low": 90,
        "heart_rate_high": 120,
        "heart_rate_low": 40
    }',

    -- Notification configuration
    notification_config         JSONB NOT NULL DEFAULT '{}',

    -- Integration configuration
    ehr_integration             JSONB DEFAULT '{}',
    lab_integration             JSONB DEFAULT '{}',
    pharmacy_integration        JSONB DEFAULT '{}',
    claims_integration          JSONB DEFAULT '{}',
    device_integration          JSONB DEFAULT '{}',

    -- Branding
    branding                    JSONB DEFAULT '{}',
    -- logo_url, primary_color, secondary_color, custom_css

    -- Compliance settings
    hipaa_config                JSONB DEFAULT '{}',
    audit_retention_days        INTEGER DEFAULT 2555,  -- 7 years
    data_retention_days         INTEGER DEFAULT 2555,

    -- Timezone
    timezone                    VARCHAR(100) DEFAULT 'America/Chicago',
    locale                      VARCHAR(20) DEFAULT 'en-US',

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT tenant_config_unique UNIQUE (tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_config_tenant ON tenant_config(tenant_id);

-- ============================================================
-- API Keys
-- ============================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Key identification
    name                        VARCHAR(200) NOT NULL,
    description                 TEXT,
    key_prefix                  VARCHAR(10) NOT NULL,
    key_hash                    VARCHAR(255) NOT NULL UNIQUE,  -- bcrypt hash of full key
    key_last4                   VARCHAR(4) NOT NULL,

    -- Permissions
    scopes                      JSONB NOT NULL DEFAULT '["read"]',
    allowed_ips                 JSONB DEFAULT '[]',
    allowed_origins             JSONB DEFAULT '[]',

    -- Rate limiting
    rate_limit_per_minute       INTEGER DEFAULT 60,
    rate_limit_per_day          INTEGER DEFAULT 10000,

    -- Status
    status                      VARCHAR(20) CHECK (status IN ('active','inactive','revoked','expired')) DEFAULT 'active',
    expires_at                  TIMESTAMPTZ,
    last_used_at                TIMESTAMPTZ,
    use_count                   BIGINT DEFAULT 0,

    -- Created by
    created_by_user_id          UUID,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);

-- ============================================================
-- Helper function to set tenant context (used by app layer)
-- ============================================================
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.tenant_id', p_tenant_id::text, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION set_bypass_rls(p_bypass BOOLEAN DEFAULT TRUE)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.bypass_rls', p_bypass::text, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- Update Timestamp Trigger (shared by all schemas)
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Update Triggers for tenant tables
-- ============================================================
CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_config_updated_at
    BEFORE UPDATE ON tenant_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
