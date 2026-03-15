# Deployment Runbook -- Eminence HealthOS

| Field | Value |
|-------|-------|
| **Platform** | Eminence HealthOS |
| **Version** | 0.1.0 |
| **Stack** | Python 3.12 / FastAPI / Next.js 15 / PostgreSQL 16 / Redis 7 / Kafka 3.9 / Qdrant / Neo4j / Keycloak / Temporal |
| **Orchestration** | Docker Compose (local), Helm 3 + Kubernetes (staging/production) |

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Local Development](#3-local-development)
4. [Database Setup and Migrations](#4-database-setup-and-migrations)
5. [Docker Build Process](#5-docker-build-process)
6. [Kubernetes / Helm Deployment](#6-kubernetes--helm-deployment)
7. [CI/CD Pipeline Overview](#7-cicd-pipeline-overview)
8. [Monitoring and Health Checks](#8-monitoring-and-health-checks)
9. [Rollback Procedures](#9-rollback-procedures)
10. [Troubleshooting Common Issues](#10-troubleshooting-common-issues)
11. [Security Checklist](#11-security-checklist)

---

## 1. Prerequisites

### Required Tools

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Docker | 24+ | Container builds and local services |
| Docker Compose | v2+ | Local multi-service orchestration |
| Python | 3.12 | API runtime and migration tooling |
| Node.js | 22 | Dashboard build (Next.js 15) |
| kubectl | 1.28+ | Kubernetes cluster management |
| Helm | 3.x | Kubernetes package deployment |
| Git | 2.x | Source control |

### Access Requirements

- **Source repository**: Clone access to `https://github.com/eminence-tech/healthos`
- **Container registry**: Push/pull access to the registry hosting `healthos/api` and `healthos/dashboard` images
- **Kubernetes cluster**: `kubectl` configured with a valid kubeconfig for the target cluster
- **Secrets manager**: Access to Vault, AWS Secrets Manager, or equivalent for production credentials (see `values-production.yaml`)

### API Keys and Credentials

| Credential | Required | Notes |
|------------|----------|-------|
| `ANTHROPIC_API_KEY` | Yes (for AI features) | Primary LLM provider |
| `OPENAI_API_KEY` | Optional | Alternative LLM provider |
| `DAILY_API_KEY` + `DAILY_DOMAIN` | Optional | Telehealth video via Daily.co |
| `QDRANT_API_KEY` | Optional | Only if Qdrant instance requires auth |
| Database passwords | Yes | Must differ from defaults in production |
| `JWT_SECRET_KEY` / `SECRET_KEY` | Yes | Must be strong, unique, production-grade values |

---

## 2. Environment Setup

### Creating the `.env` File

```bash
cp .env.example .env
```

Edit `.env` and populate each section. The full variable reference follows.

### Environment Variable Reference

#### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `eminence-healthos` | Application identifier |
| `APP_ENV` | `development` | Environment: `development`, `test`, `production` |
| `APP_DEBUG` | `true` | Enable debug mode (set `false` in production) |
| `APP_HOST` | `0.0.0.0` | Bind address |
| `APP_PORT` | `8000` | API listen port |
| `SECRET_KEY` | `change-me-in-production` | Application secret key |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |

#### PostgreSQL

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://healthos:healthos@postgres:5432/healthos` | Async database connection string |
| `DATABASE_POOL_SIZE` | `20` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Max overflow connections |

#### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `REDIS_CACHE_TTL` | `300` | Default cache TTL in seconds |

#### Kafka

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address |
| `KAFKA_CONSUMER_GROUP` | `healthos-agents` | Consumer group ID |
| `KAFKA_VITALS_TOPIC` | `vitals.ingested` | Topic for vitals data |
| `KAFKA_ALERTS_TOPIC` | `alerts.generated` | Topic for generated alerts |
| `KAFKA_AGENT_EVENTS_TOPIC` | `agent.events` | Topic for agent events |

#### LLM Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key |
| `OPENAI_API_KEY` | (empty) | OpenAI API key |
| `OLLAMA_BASE_URL` | `http://localhost:12434` | Ollama local endpoint |
| `LLM_DEFAULT_PROVIDER` | `anthropic` | `anthropic`, `openai`, or `ollama` |
| `LLM_DEFAULT_MODEL` | `claude-sonnet-4-20250514` | Default model identifier |

#### Vector Database (Qdrant)

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant HTTP endpoint |
| `QDRANT_API_KEY` | (empty) | Qdrant API key (if required) |

#### Neo4j Knowledge Graph

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j Bolt protocol URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `healthos` | Neo4j password |

#### Authentication (JWT)

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

#### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OpenTelemetry collector gRPC endpoint |
| `PROMETHEUS_PORT` | `9090` | Prometheus scrape port |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `json` | Log format: `json` or `text` |

#### Object Storage (MinIO/S3)

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT` | `http://localhost:9000` | S3-compatible endpoint |
| `S3_ACCESS_KEY` | `minioadmin` | Access key |
| `S3_SECRET_KEY` | `minioadmin` | Secret key |
| `S3_BUCKET` | `healthos-artifacts` | Default bucket name |

#### Telehealth (Daily.co)

| Variable | Default | Description |
|----------|---------|-------------|
| `DAILY_API_KEY` | (empty) | Daily.co API key |
| `DAILY_DOMAIN` | (empty) | Daily.co domain |

---

## 3. Local Development

### Starting All Services

The full stack is defined in `docker-compose.yml` with development overrides in `docker-compose.dev.yml`.

```bash
# Start the full stack with development overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Start in detached mode
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

### Services and Ports

| Service | Container Port | Host Port | URL |
|---------|---------------|-----------|-----|
| API (FastAPI) | 8000 | 4090 | `http://localhost:4090` |
| Dashboard (Next.js) | 3000 | 3052 | `http://localhost:3052` |
| PostgreSQL (pgvector) | 5432 | 5439 | `postgresql://localhost:5439` |
| Redis | 6379 | 6279 | `redis://localhost:6279` |
| Kafka (KRaft) | 9092 | 9094 | `localhost:9094` |
| Qdrant | 6333 | 6333 | `http://localhost:6333` |
| Neo4j Browser | 7474 | 7575 | `http://localhost:7575` |
| Neo4j Bolt | 7687 | 7678 | `bolt://localhost:7678` |
| Keycloak | 8080 | 8180 | `http://localhost:8180` |
| Prometheus | 9090 | 9091 | `http://localhost:9091` |
| Grafana | 3000 | 3101 (prod) / 3001 (dev) | `http://localhost:3101` |
| Temporal Server | 7233 | 7233 | `localhost:7233` |
| Temporal UI | 8080 | 8233 | `http://localhost:8233` |
| Jaeger UI (dev only) | 16686 | 16686 | `http://localhost:16686` |

### Development-Specific Behavior

The `docker-compose.dev.yml` overlay applies these overrides:

- **API hot-reload**: Source is mounted via volume (`.:/app`), and uvicorn runs with `--reload`.
- **Debug mode**: `DEBUG=true` and `ENVIRONMENT=development` are set.
- **Jaeger tracing**: A Jaeger all-in-one container is added, accepting OTLP on ports 4317 (gRPC) and 4318 (HTTP).

### Stopping Services

```bash
# Stop and remove containers (preserves volumes)
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Stop and remove containers AND volumes (full reset)
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### Running the API Without Docker

```bash
# Install Python dependencies
pip install -e ".[dev]"

# Start PostgreSQL and Redis via Docker (required backing services)
docker compose up postgres redis -d

# Run the API
uvicorn healthos_platform.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Database Setup and Migrations

### Alembic Configuration

Migrations live in the `migrations/` directory as defined in `alembic.ini`. The default connection string in `alembic.ini` points to `localhost:5439` (the host-mapped PostgreSQL port from Docker Compose):

```
sqlalchemy.url = postgresql+asyncpg://healthos:healthos@localhost:5439/healthos
```

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Check current migration version
alembic current

# View migration history
alembic history --verbose

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe the change"

# Downgrade by one revision
alembic downgrade -1

# Downgrade to a specific revision
alembic downgrade <revision_id>
```

### Running Migrations Inside Docker

```bash
# Execute inside the running API container
docker compose exec api alembic upgrade head
```

### Initial Database Setup

The `scripts/init_db.sql` file is automatically executed when the PostgreSQL container starts for the first time (mounted to `/docker-entrypoint-initdb.d/01-init.sql`). This handles initial schema objects like extensions (e.g., pgvector).

### Pre-Deployment Migration Checklist

1. Test the migration against a copy of production data.
2. Verify both `upgrade` and `downgrade` paths work.
3. For destructive migrations (column drops, table drops), back up affected tables first.
4. Run `alembic check` to ensure models and migrations are in sync.

---

## 5. Docker Build Process

### Production Dockerfiles

Two production-grade multi-stage Dockerfiles are located in `deploy/docker/`:

#### API Image (`deploy/docker/Dockerfile.api`)

- **Base**: `python:3.12-slim` (multi-stage)
- **Stage 1 (builder)**: Installs build tools, CPU-only PyTorch, copies source (`healthos_platform/`, `modules/`, `observability/`, `scripts/`, `services/`, `shared/`, `alembic/`, `alembic.ini`), runs `pip install -e .`
- **Stage 2 (runtime)**: Minimal image with `curl` for health checks, creates non-root `healthos` user, runs uvicorn with 4 workers, uvloop, httptools, and no access log
- **Health check**: `curl -f http://localhost:8000/health` every 30s
- **Exposed port**: 8000

```bash
docker build -f deploy/docker/Dockerfile.api -t healthos/api:latest .
```

#### Dashboard Image (`deploy/docker/Dockerfile.dashboard`)

- **Base**: `node:22-alpine` (three-stage)
- **Stage 1 (deps)**: Installs dependencies via npm/yarn/pnpm (auto-detected)
- **Stage 2 (builder)**: Builds the Next.js application with telemetry disabled
- **Stage 3 (runner)**: Minimal runtime with standalone output, creates non-root `healthos` user
- **Health check**: `wget --spider http://localhost:3000/` every 30s
- **Exposed port**: 3000

```bash
docker build -f deploy/docker/Dockerfile.dashboard -t healthos/dashboard:latest ./frontend
```

### Root Dockerfile

The root `Dockerfile` is a simpler two-stage build used by Docker Compose for local development and the Temporal worker. It does not include the non-root user or health check directives that the production Dockerfiles provide.

### Tagging and Pushing

```bash
# Tag with version
export IMAGE_TAG="0.1.0"
docker tag healthos/api:latest healthos/api:${IMAGE_TAG}
docker tag healthos/dashboard:latest healthos/dashboard:${IMAGE_TAG}

# Push to registry
docker push healthos/api:${IMAGE_TAG}
docker push healthos/dashboard:${IMAGE_TAG}
```

---

## 6. Kubernetes / Helm Deployment

### Helm Chart Structure

```
deploy/helm/healthos/
  Chart.yaml              # Chart metadata (v0.1.0, appVersion 0.1.0)
  values.yaml             # Default values (dev-oriented)
  values-production.yaml  # Production overrides
```

### Using the Deploy Script

The automated deploy script (`deploy/scripts/deploy.sh`) handles the full lifecycle:

```bash
# Deploy to dev (default)
./deploy/scripts/deploy.sh dev

# Deploy to production
./deploy/scripts/deploy.sh production

# Deploy without rebuilding images
./deploy/scripts/deploy.sh production --skip-build

# Override image tag
IMAGE_TAG=0.1.0 ./deploy/scripts/deploy.sh production
```

The script performs these steps in order:
1. Checks prerequisites (`kubectl`, `helm`, `docker`)
2. Verifies Kubernetes cluster connectivity
3. Resolves the values file and namespace for the target environment
4. Builds API and Dashboard Docker images (unless `--skip-build`)
5. Creates the Kubernetes namespace if it does not exist
6. Runs `helm upgrade --install` with `--wait --timeout 5m`
7. Waits for deployment rollout (300s timeout per deployment)
8. Prints access URLs and pod/service status

### Environment-Specific Configuration

| Setting | Default (`values.yaml`) | Production (`values-production.yaml`) |
|---------|------------------------|--------------------------------------|
| Namespace | `healthos` | `healthos-production` |
| API replicas | 2 | 3 |
| Dashboard replicas | 2 | 3 |
| API CPU request/limit | 250m / 1 | 500m / 2 |
| API memory request/limit | 512Mi / 1Gi | 1Gi / 2Gi |
| Dashboard CPU request/limit | 100m / 500m | 200m / 1 |
| Dashboard memory request/limit | 256Mi / 512Mi | 512Mi / 1Gi |
| HPA min/max replicas (API) | 2 / 10 | 3 / 10 |
| HPA CPU target | 70% | 60% |
| HPA memory target | 80% | 70% |
| Ingress host | `healthos.local` | `healthos.example.com` |
| TLS secret | `healthos-tls` | `healthos-production-tls` |
| Log level | `info` | `warning` |
| Rate limiting | (none) | `100` req/s via nginx annotation |
| TLS issuer | (none) | `letsencrypt-prod` via cert-manager |
| Secrets | Inline placeholders | Injected via external secrets manager |

### Manual Helm Deployment

```bash
# Dev deployment
helm upgrade --install healthos deploy/helm/healthos/ \
  --namespace healthos-dev --create-namespace \
  --set api.image.tag=0.1.0 \
  --set dashboard.image.tag=0.1.0 \
  --wait --timeout 5m

# Production deployment
helm upgrade --install healthos deploy/helm/healthos/ \
  --namespace healthos-production --create-namespace \
  -f deploy/helm/healthos/values-production.yaml \
  --set api.image.tag=0.1.0 \
  --set dashboard.image.tag=0.1.0 \
  --wait --timeout 5m
```

### Verifying the Deployment

```bash
kubectl get pods -n healthos-production -o wide
kubectl get svc -n healthos-production
kubectl get ingress -n healthos-production
kubectl rollout status deployment/healthos-api -n healthos-production
kubectl rollout status deployment/healthos-dashboard -n healthos-production
```

### Ingress Configuration

The Helm chart configures an nginx ingress controller with:
- TLS termination (secret-based)
- Max request body size: 50 MB
- Proxy read timeout: 120 seconds
- Rate limiting at 100 req/s (production only)
- cert-manager integration for automatic Let's Encrypt certificates (production only)

For local testing, add the ingress host to `/etc/hosts`:

```
127.0.0.1 healthos.local
```

---

## 7. CI/CD Pipeline Overview

The GitHub Actions workflow (`.github/workflows/ci.yml`) triggers on:
- **Push** to `main` or `claude/*` branches
- **Pull requests** targeting `main`

### Pipeline Jobs

| Job | Depends On | What It Does |
|-----|-----------|--------------|
| **lint** | -- | Installs `ruff`, runs `ruff check .` and `ruff format --check .` |
| **test** | lint | Spins up PostgreSQL (pgvector:pg16) and Redis (7-alpine) service containers. Installs `.[dev]` dependencies. Runs `pytest tests/ -v --tb=short --cov=healthos_platform --cov=modules` with `APP_ENV=test`. |
| **type-check** | -- | Runs `mypy healthos_platform/ modules/ --ignore-missing-imports` |
| **security-scan** | -- | Runs `bandit` (Python security linter) and `pip-audit` (dependency vulnerability scan). High-severity/high-confidence bandit findings **fail** the build. A `bandit-report.json` artifact is uploaded and retained for 30 days. |

### CI Service Containers

The test job provisions:
- **PostgreSQL**: `pgvector/pgvector:pg16` on port 5432 with database `healthos_test`
- **Redis**: `redis:7-alpine` on port 6279

### Adding Docker Build to CI

The current pipeline does not build Docker images. To add image building and pushing, extend the workflow with a `build` job that depends on `test` and `security-scan`, builds both Dockerfiles, and pushes to your container registry.

---

## 8. Monitoring and Health Checks

### Application Health Endpoints

| Endpoint | Port | Purpose |
|----------|------|---------|
| `/health` | 8000 | API readiness and liveness probe target |
| `/` | 3000 | Dashboard readiness and liveness probe target |

### Docker Health Checks

Both production Dockerfiles include built-in health checks:

- **API**: `curl -f http://localhost:8000/health` -- interval 30s, timeout 5s, start period 15s, 3 retries
- **Dashboard**: `wget --spider http://localhost:3000/` -- interval 30s, timeout 5s, start period 10s, 3 retries

### Kubernetes Probes

Defined in `values.yaml`:

- **Readiness probe** (API): `GET /health:8000` -- initial delay 10s, period 10s, failure threshold 3
- **Liveness probe** (API): `GET /health:8000` -- initial delay 15s, period 20s, failure threshold 3
- **Readiness probe** (Dashboard): `GET /:3000` -- initial delay 10s, period 10s, failure threshold 3
- **Liveness probe** (Dashboard): `GET /:3000` -- initial delay 15s, period 20s, failure threshold 3

### Observability Stack

| Tool | Local Port | Purpose |
|------|-----------|---------|
| **Prometheus** | 9091 | Metrics collection; config at `infrastructure/prometheus/prometheus.yml` |
| **Grafana** | 3101 (prod) / 3001 (dev) | Dashboards and alerting; provisioning at `infrastructure/grafana/provisioning/`, dashboards at `infrastructure/grafana/dashboards/` |
| **Jaeger** (dev only) | 16686 | Distributed tracing UI; OTLP collector on 4317 (gRPC) / 4318 (HTTP) |
| **Temporal UI** | 8233 | Workflow execution visibility |

### Key Metrics to Monitor

- API response latency (p50, p95, p99)
- API error rate (5xx responses)
- Pod CPU and memory utilization vs. HPA thresholds (70% CPU / 80% memory default; 60%/70% production)
- PostgreSQL connection pool utilization (`DATABASE_POOL_SIZE=20`, `DATABASE_MAX_OVERFLOW=10`)
- Kafka consumer lag on `vitals.ingested`, `alerts.generated`, `agent.events` topics
- Redis cache hit rate and memory usage
- Temporal workflow failure rate

### Grafana Default Credentials

- **Username**: `admin`
- **Password**: `healthos` (set via `GF_SECURITY_ADMIN_PASSWORD`)

---

## 9. Rollback Procedures

### Helm Rollback

```bash
# List release history
helm history healthos -n healthos-production

# Roll back to previous revision
helm rollback healthos <REVISION> -n healthos-production --wait --timeout 5m

# Roll back to the immediately preceding release
helm rollback healthos 0 -n healthos-production --wait --timeout 5m
```

### Kubernetes Deployment Rollback

```bash
# View rollout history
kubectl rollout history deployment/healthos-api -n healthos-production

# Undo the last rollout
kubectl rollout undo deployment/healthos-api -n healthos-production
kubectl rollout undo deployment/healthos-dashboard -n healthos-production

# Roll back to a specific revision
kubectl rollout undo deployment/healthos-api -n healthos-production --to-revision=<N>
```

### Database Migration Rollback

```bash
# Downgrade by one revision
alembic downgrade -1

# Downgrade to a specific revision
alembic downgrade <revision_id>

# Check current version
alembic current
```

**Important**: Always roll back the database migration *before* rolling back the application if the new code depends on schema changes. If the old code is compatible with the new schema, roll back the application first.

### Full Environment Teardown

Use the teardown script (`deploy/scripts/teardown.sh`):

```bash
# Teardown dev environment (keeps namespace)
./deploy/scripts/teardown.sh dev

# Teardown production (keeps namespace)
./deploy/scripts/teardown.sh production

# Teardown and delete the namespace
./deploy/scripts/teardown.sh production --delete-namespace
```

The script prompts for confirmation before proceeding. It uninstalls the Helm release and optionally deletes the namespace.

---

## 10. Troubleshooting Common Issues

### Container Fails to Start

**Symptom**: API container exits immediately or enters `CrashLoopBackOff`.

```bash
# Check logs
docker compose logs api
kubectl logs deployment/healthos-api -n healthos-production --tail=100

# Check events
kubectl describe pod -l app=healthos-api -n healthos-production
```

**Common causes**:
- `DATABASE_URL` is unreachable -- verify PostgreSQL is healthy (`pg_isready`).
- Missing `.env` file or unset required environment variables.
- Port conflict on the host (4090, 3052, etc.).

### Database Connection Errors

**Symptom**: `ConnectionRefusedError` or `asyncpg.exceptions` on startup.

- Ensure PostgreSQL is healthy: `docker compose exec postgres pg_isready -U healthos`
- Verify the host in `DATABASE_URL` matches the service name (`postgres` inside Docker, `localhost` outside).
- Check pool exhaustion: reduce `DATABASE_POOL_SIZE` or increase PostgreSQL `max_connections`.

### Kafka Consumer Not Receiving Messages

- Verify Kafka is healthy: `docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list`
- Check consumer group: ensure `KAFKA_CONSUMER_GROUP` is set to `healthos-agents`.
- KRaft mode requires `CLUSTER_ID` to be consistent; do not change it after first boot.

### Keycloak Realm Import Fails

- Ensure `infrastructure/keycloak/healthos-realm.json` exists.
- Keycloak requires the PostgreSQL `keycloak` database; verify it was created by `scripts/init_db.sql`.
- Check Keycloak logs: `docker compose logs keycloak`

### Helm Deployment Timeout

**Symptom**: `helm upgrade --install` times out after 5 minutes.

- Check pod status: `kubectl get pods -n <namespace>`
- Check events: `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
- Common causes: image pull failures (wrong registry, missing pull secrets), insufficient cluster resources, failing readiness probes.

### Alembic Migration Errors

- **"Target database is not up to date"**: Run `alembic upgrade head` before generating new migrations.
- **"Can't locate revision"**: Ensure the `migrations/` directory is present and the `script_location` in `alembic.ini` is correct.
- **Connection refused on localhost:5439**: Ensure PostgreSQL is running and the port mapping is active (Docker Compose maps 5432 to 5439 on the host).

### Temporal Workflows Not Executing

- Verify Temporal server health: `docker compose exec temporal tctl cluster health`
- Ensure the `temporal-worker` container is running and connected.
- Check worker logs: `docker compose logs temporal-worker`
- Verify `TEMPORAL_ADDRESS` is set to `temporal:7233` inside Docker.

---

## 11. Security Checklist

This checklist references findings from `docs/SECURITY_PENTEST_REPORT.md` (assessment date: 2026-03-10 through 2026-03-14, report ID: PENTEST-2026-Q1-001). The platform received an overall risk rating of **LOW-MODERATE**.

### Pre-Deployment Security Checks

- [ ] **Non-root container user**: Production Dockerfiles (`Dockerfile.api`, `Dockerfile.dashboard`) run as the `healthos` user. Verify the root `Dockerfile` is NOT used for production. *(Pentest finding: "Dockerfile runs application as root")*
- [ ] **Secrets not in values files**: All production secrets in `values-production.yaml` are set to `REPLACE_VIA_SECRETS_MANAGER`. Verify they are injected via Vault, AWS Secrets Manager, or equivalent -- never committed to source control.
- [ ] **Change all default passwords**: Replace default credentials for PostgreSQL (`healthos`), Neo4j (`healthos`), Keycloak (`admin/admin`), Grafana (`healthos`), `SECRET_KEY`, and `JWT_SECRET_KEY`.
- [ ] **JWT token revocation**: Implement a token blocklist mechanism. *(Pentest finding: "No token revocation / blocklist mechanism for JWTs")*
- [ ] **CORS middleware**: Verify CORS middleware is configured in the FastAPI application. *(Pentest finding: "No CORS middleware configuration found")*
- [ ] **Command injection protection**: Ensure input sanitizer covers command injection patterns. *(Pentest finding: "Command injection detection absent from input sanitizer")*
- [ ] **CI security gates**: Change `pip-audit` in CI to fail the build on vulnerabilities (remove `|| true`). *(Pentest finding: "pip-audit failures do not block CI")*
- [ ] **TLS everywhere**: Production ingress uses TLS with `letsencrypt-prod` issuer. Verify `healthos-production-tls` secret exists or cert-manager will provision it.
- [ ] **Rate limiting**: Production ingress annotation sets `nginx.ingress.kubernetes.io/rate-limit: "100"`. Verify it is active.
- [ ] **PHI encryption**: Verify AES-256-GCM field-level encryption is enabled for all PHI fields at rest.
- [ ] **RBAC enforcement**: Confirm all 22 permissions across 6 roles are enforced at the API layer.
- [ ] **Multi-tenant isolation**: Verify tenant isolation is enforced at request, query, and agent levels.
- [ ] **Security headers**: Confirm OWASP-compliant security headers are present on all API responses.
- [ ] **Bandit scan clean**: CI must pass the high-severity bandit scan without issues.
- [ ] **Dependency audit**: Run `pip-audit --strict` and resolve all known vulnerabilities before deploying.
- [ ] **Debug mode disabled**: Ensure `APP_DEBUG=false` and `APP_ENV=production` in production.
- [ ] **Log level**: Production log level should be `warning` (not `info` or `debug`) to avoid leaking sensitive data in logs.

### Production Hardening

- [ ] HPA is enabled with appropriate thresholds (60% CPU, 70% memory for production).
- [ ] Resource limits are set on all pods to prevent noisy-neighbor issues.
- [ ] Image pull policy is `IfNotPresent` with specific version tags (not `latest`).
- [ ] Network policies restrict inter-pod communication to required paths only.
- [ ] Pod security standards (restricted) are enforced at the namespace level.
- [ ] Audit logging is enabled for the Kubernetes API server.

### References

- Security assessment: `docs/SECURITY_PENTEST_REPORT.md`
- Zero Trust architecture: `docs/ZERO_TRUST_ARCHITECTURE.md`
- Keycloak realm config: `infrastructure/keycloak/healthos-realm.json`
- Prometheus config: `infrastructure/prometheus/prometheus.yml`
- Grafana provisioning: `infrastructure/grafana/provisioning/`
