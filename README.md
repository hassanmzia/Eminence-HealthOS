# Eminence HealthOS

Unified Healthcare AI Platform — 30 specialized agents orchestrating clinical workflows across RPM, Telehealth, Operations, and Population Health Analytics.

## Quick Start

```bash
cp .env.example .env
make setup
make dev

# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

## Architecture

```
platform/         Core agent framework, orchestration engine, security
services/api/     FastAPI application, routes, middleware
modules/          Domain modules (RPM, Telehealth, Operations, Analytics)
shared/           Shared models, utilities, events, constants
observability/    Tracing, audit, explainability, metrics, model cards
infrastructure/   Docker, Helm, Terraform
frontend/         React/Next.js clinician dashboard
migrations/       Alembic database migrations
tests/            Unit, integration, E2E tests
```

## Development

```bash
make dev          # Start dev environment (Docker Compose)
make test         # Run all tests
make lint         # Run linters
make migrate      # Run database migrations
make seed         # Seed demo data
make down         # Stop all services
```
