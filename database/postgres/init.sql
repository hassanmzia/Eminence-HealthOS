-- ============================================================
-- Eminence HealthOS - Database Initialization (Bootstrap)
--
-- This script creates additional databases needed by services
-- and should be run by the PostgreSQL superuser on container
-- startup (e.g. via docker-entrypoint-initdb.d).
--
-- For the main HealthOS database, Alembic manages the schema.
-- The numbered SQL files in this directory serve as the
-- canonical reference and can be loaded manually for fresh
-- environments or CI/CD test databases.
--
-- Execution order:
--   1. init.sql           (this file - databases & service DBs)
--   2. 00_extensions.sql  (PostgreSQL extensions)
--   3. 01_tenant_schema.sql
--   4. 02_fhir_schema.sql
--   5. 03_clinical_schema.sql
--   6. 04_analytics_schema.sql
--   7. 05_audit_schema.sql
--   8. 06_rls_policies.sql
--   9. 07_indexes.sql
--  10. 08_seed.sql
-- ============================================================

-- Create keycloak database for Keycloak identity provider
SELECT 'CREATE DATABASE keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec

-- Create temporal databases for Temporal workflow engine
SELECT 'CREATE DATABASE temporal'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'temporal')\gexec

SELECT 'CREATE DATABASE temporal_visibility'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'temporal_visibility')\gexec

-- Create grafana database for monitoring dashboards
SELECT 'CREATE DATABASE grafana'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'grafana')\gexec

-- Create langfuse database for LLM observability
SELECT 'CREATE DATABASE langfuse'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec

-- Grant privileges to the healthos application user
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'healthos') THEN
        GRANT ALL PRIVILEGES ON DATABASE keycloak TO healthos;
        GRANT ALL PRIVILEGES ON DATABASE temporal TO healthos;
        GRANT ALL PRIVILEGES ON DATABASE temporal_visibility TO healthos;
        GRANT ALL PRIVILEGES ON DATABASE grafana TO healthos;
        GRANT ALL PRIVILEGES ON DATABASE langfuse TO healthos;
    END IF;
END $$;

-- Enable extensions on the main database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas for logical separation
CREATE SCHEMA IF NOT EXISTS healthos;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions to healthos user
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'healthos') THEN
        GRANT ALL ON SCHEMA healthos TO healthos;
        GRANT ALL ON SCHEMA audit TO healthos;
    END IF;
END $$;
