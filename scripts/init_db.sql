-- Eminence HealthOS — Database Initialization
-- Run on PostgreSQL container startup

-- Create keycloak database for Keycloak identity provider
CREATE DATABASE keycloak;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO healthos;

-- Create temporal databases for Temporal workflow engine
CREATE DATABASE temporal;
GRANT ALL PRIVILEGES ON DATABASE temporal TO healthos;
CREATE DATABASE temporal_visibility;
GRANT ALL PRIVILEGES ON DATABASE temporal_visibility TO healthos;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for AI embeddings

-- Create schemas for multi-tenant isolation
CREATE SCHEMA IF NOT EXISTS healthos;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions
GRANT ALL ON SCHEMA healthos TO healthos;
GRANT ALL ON SCHEMA audit TO healthos;
