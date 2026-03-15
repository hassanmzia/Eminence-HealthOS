-- ============================================================
-- Eminence HealthOS - PostgreSQL Extensions
-- Reference schema for Alembic migrations
--
-- Run after database creation (init.sql) to enable all
-- required extensions. Some extensions (uuid-ossp, pgcrypto,
-- vector) are also created in scripts/init_db.sql; the
-- IF NOT EXISTS guards keep this idempotent.
-- ============================================================

-- UUID generation (gen_random_uuid from pgcrypto preferred)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions (PHI encryption, password hashing)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- pgvector: vector similarity search for AI embeddings
CREATE EXTENSION IF NOT EXISTS "vector";

-- PostGIS: geographic queries (org locations, patient proximity)
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Trigram indexes for fuzzy text search (patient name lookup)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Optional: TimescaleDB for time-series vitals data
-- CREATE EXTENSION IF NOT EXISTS timescaledb;
