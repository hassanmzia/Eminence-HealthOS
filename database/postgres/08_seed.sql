-- ============================================================
-- Eminence HealthOS - Seed Data
-- Reference schema for Alembic migrations
--
-- Creates the default demo organization and tenant config.
-- ============================================================

-- ============================================================
-- Demo Organization
-- ============================================================
INSERT INTO organizations (
    id,
    name,
    short_name,
    slug,
    org_type,
    city,
    state,
    country,
    status,
    tier,
    hipaa_baa_signed,
    baa_signed_date
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Eminence HealthOS Demo Organization',
    'HealthOS Demo',
    'healthos-demo',
    'health_system',
    'Chicago',
    'IL',
    'USA',
    'demo',
    'enterprise',
    TRUE,
    CURRENT_DATE
) ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- Demo Tenant Configuration
-- ============================================================
INSERT INTO tenant_config (
    tenant_id,
    feature_flags,
    agent_config,
    clinical_thresholds
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '{
        "rpm_enabled": true,
        "ccm_enabled": true,
        "agents_enabled": true,
        "ai_alerts_enabled": true,
        "stemi_protocol": true,
        "stroke_protocol": true,
        "copd_protocol": true,
        "neo4j_enabled": true,
        "qdrant_enabled": true,
        "hitl_required": false
    }',
    '{
        "enabled_agents": ["triage", "risk_stratification", "care_gap", "medication_review", "notification"],
        "hitl_threshold": 0.7,
        "orchestration_mode": "full_auto",
        "max_concurrent_pipelines": 10
    }',
    '{
        "glucose_critical_low": 50,
        "glucose_critical_high": 400,
        "glucose_high": 250,
        "systolic_critical": 180,
        "diastolic_critical": 120,
        "spo2_critical_low": 85,
        "spo2_low": 90,
        "heart_rate_high": 120,
        "heart_rate_low": 40
    }'
) ON CONFLICT (tenant_id) DO NOTHING;
