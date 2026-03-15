# Zero Trust Security Architecture — Eminence HealthOS

This document describes the Zero Trust security architecture implemented across
the HealthOS platform. Every request is authenticated, authorized, and audited
regardless of network location.

## Core Principle

**"Never trust, always verify."** No component — internal or external — is
implicitly trusted. Every access decision is made based on identity, context,
and policy at every layer.

---

## 1. Identity & Authentication

**Implementation:** `healthos_platform/security/auth.py`

- All API access requires a valid JWT bearer token
- Tokens carry `sub` (user ID), `org_id` (tenant), `role`, and a unique `jti`
- Access tokens are short-lived (`jwt_access_token_expire_minutes`)
- Refresh tokens use separate expiry (`jwt_refresh_token_expire_days`)
- Passwords are hashed with bcrypt via `passlib`
- Every token includes issue time (`iat`) for revocation checks

**No anonymous access is permitted to any data endpoint.**

---

## 2. Authorization (RBAC)

**Implementation:** `healthos_platform/security/rbac.py`

Six roles with least-privilege permission sets:

| Role | Scope |
|------|-------|
| `admin` | Full platform access |
| `clinician` | Patient data, vitals, alerts, encounters, care plans, analytics |
| `care_manager` | Similar to clinician without write access to some resources |
| `nurse` | Vitals, alerts, encounters (read-heavy) |
| `patient` | Own vitals, alerts, encounters, care plans (read-only) |
| `system` | Internal agent-to-agent operations |

22 granular permissions enforce access at the API endpoint level. Role checks
run on every request via FastAPI dependency injection
(`healthos_platform/api/middleware/tenant.py`).

---

## 3. Multi-Tenant Isolation

**Implementation:** `healthos_platform/security/tenant_isolation.py`

### Request-Level Isolation
- `TenantScope` is set via `ContextVar` at the start of every request
- All downstream code accesses data only through `get_tenant_scope()`
- Cross-tenant access raises `TenantIsolationError`

### Data-Level Isolation
- Every database query is filtered by `tenant_id` via `TenantQueryFilter`
- Record-level access is validated before return (`validate_record_access`)
- Kafka topics are namespaced per tenant
- Redis keys are prefixed with `{org_id}:`

### Agent-Level Isolation
- `TenantAwareAgent` mixin ensures all agent outputs are tagged with tenant context
- Agent data access goes through tenant validation before processing
- Cross-tenant data leakage is blocked at the query layer

---

## 4. Network Security

**Implementation:** `infrastructure/helm/healthos/templates/networkpolicy.yaml`

Kubernetes NetworkPolicy enforces:

- **Ingress:** Only the dashboard and ingress controller can reach the API
- **Egress:** API pods can only reach:
  - PostgreSQL (port 5432)
  - Redis (port 6379)
  - Kafka (port 9092)
  - Qdrant (vector DB)
  - Neo4j (graph DB)
  - External HTTPS (port 443, for LLM APIs) — private IP ranges excluded
  - DNS (port 53)
- **Default deny:** All other traffic is blocked

No pod-to-pod communication is allowed outside of explicitly defined policies.

---

## 5. Input Validation & Injection Prevention

**Implementation:** `healthos_platform/security/input_sanitizer.py`

Every API input is scanned for:

| Threat | Detection Method |
|--------|-----------------|
| SQL injection | Pattern matching for UNION, SELECT, DROP, OR 1=1, etc. |
| XSS | Detection of `<script>`, `javascript:`, `on*=` handlers |
| Path traversal | Detection of `../`, `..\\`, `%2e%2e` |
| Oversized inputs | Max string length (10,000), max nesting depth (10) |

Detected threats are logged and blocked before reaching application logic.

---

## 6. PHI/PII Protection

**Implementation:** `healthos_platform/security/phi_filter.py`

Five-level data classification with enforcement:

| Level | Classification | Examples |
|-------|---------------|----------|
| 5 — CRITICAL | Highest sensitivity PHI | SSN, genetic data |
| 4 — SENSITIVE | Clinical PHI | Diagnoses, medications, lab results |
| 3 — STANDARD | Administrative PHI | Appointments, billing, contact info |
| 2 — DE-IDENTIFIED | Safe Harbor compliant | Aggregated/anonymized data |
| 1 — PUBLIC | Non-sensitive | General health education |

Enforcement points:
- PHI is scanned and redacted before reaching LLM providers
- SSN, phone, email, MRN, DOB, address, ZIP, and IP patterns are detected
- Redaction markers (`[REDACTED-TYPE]`) replace sensitive values
- Dictionary and nested data structures are recursively scanned

---

## 7. Audit Trail

**Implementation:** `healthos_platform/api/middleware/audit.py`, `observability/core/audit.py`

### API-Level Auditing
- Every request is logged with: request ID, method, path, user ID, duration, client IP, status
- Failed authentication attempts are logged separately
- `X-Request-ID` header is returned for end-to-end tracing

### Agent-Level Auditing
- SHA-256 hash-chained audit records (tamper-proof)
- 28 healthcare-specific event types tracked (HITL decisions, PHI access,
  agent runs, safety flags, guardrail violations, emergency alerts)
- Every audit record references the preceding record's hash

---

## 8. LLM-Specific Controls

**Implementation:** `healthos_platform/ml/llm/router.py`

- PHI is filtered before any data reaches external LLM providers
- Local Ollama provider available for PHI-safe operations (no data leaves the network)
- Provider fallback chains ensure availability without bypassing controls
- Per-tenant provider configuration allows compliance-specific routing
- Token usage and cost are tracked for anomaly detection

---

## 9. Monitoring & Alerting

**Implementation:** `observability/metrics/collector.py`, `infrastructure/prometheus/alert_rules.yml`

Zero Trust violations trigger alerts:
- Guardrail violations (prompt injection, restricted topics)
- PHI exposure detections
- High agent error rates (potential compromise indicator)
- Cross-tenant access attempts (logged by `TenantIsolationError`)
- HITL decision backlogs (safety-critical decisions pending)

---

## 10. Security Scanning (CI/CD)

**Implementation:** `.github/workflows/ci.yml`, `.bandit.yml`

Automated security checks on every push and PR:
- **Bandit** — Python static security analysis (hardcoded secrets, injection,
  deserialization, subprocess calls)
- **pip-audit** — Dependency vulnerability scanning
- High-severity findings block the CI pipeline
- Reports are archived as build artifacts

---

## Architecture Diagram

```
                    ┌──────────────────────────────────────────┐
                    │              Internet                     │
                    └─────────────────┬────────────────────────┘
                                      │ HTTPS only
                              ┌───────▼───────┐
                              │ Ingress / TLS  │
                              │  Termination   │
                              └───────┬────────┘
                                      │
                    ┌─────────────────▼──────────────────────┐
                    │         API Gateway Layer               │
                    │  ┌─────────────────────────────────┐   │
                    │  │ 1. Audit Middleware (log all)    │   │
                    │  │ 2. JWT Validation                │   │
                    │  │ 3. Tenant Context Extraction     │   │
                    │  │ 4. RBAC Permission Check         │   │
                    │  │ 5. Input Sanitization            │   │
                    │  │ 6. Rate Limiting                 │   │
                    │  └─────────────────────────────────┘   │
                    └─────────────────┬──────────────────────┘
                                      │ Authenticated + Authorized
                    ┌─────────────────▼──────────────────────┐
                    │         Application Layer               │
                    │  ┌──────────────────────────────────┐  │
                    │  │ Tenant-Scoped Agent Execution     │  │
                    │  │ PHI Filter → LLM Router           │  │
                    │  │ Decision Audit (hash-chained)     │  │
                    │  └──────────────────────────────────┘  │
                    └─────────────────┬──────────────────────┘
                                      │ Tenant-filtered queries
                    ┌─────────────────▼──────────────────────┐
                    │         Data Layer (NetworkPolicy)      │
                    │  PostgreSQL │ Redis │ Kafka │ Qdrant    │
                    │  (Row-level tenant isolation on all)    │
                    └────────────────────────────────────────┘
```

Every arrow in this diagram represents a verification point. No layer trusts
the layer above it — each independently validates identity, authorization,
and tenant scope.
