# Eminence HealthOS -- API Endpoints Reference

Base URL: `/api/v1`

All endpoints require authentication via Bearer token (`require_auth`) unless otherwise noted. Tenant isolation is enforced via the `X-Tenant-ID` header (resolved by `TenantMiddleware`). Responses default to `application/json` (ORJSONResponse).

---

## Table of Contents

1. [Patients](#1-patients)
2. [Agents](#2-agents)
3. [Alerts](#3-alerts)
4. [Dashboard](#4-dashboard)
5. [FHIR R4 Interoperability](#5-fhir-r4-interoperability)
6. [Remote Patient Monitoring (RPM)](#6-remote-patient-monitoring-rpm)
7. [Telehealth](#7-telehealth)
8. [Operations](#8-operations)
9. [Analytics](#9-analytics)
10. [Compliance & Governance](#10-compliance--governance)
11. [Digital Twin](#11-digital-twin)
12. [Imaging & Radiology](#12-imaging--radiology)
13. [Labs](#13-labs)
14. [Pharmacy](#14-pharmacy)
15. [Revenue Cycle Management (RCM)](#15-revenue-cycle-management-rcm)
16. [Mental Health](#16-mental-health)
17. [Patient Engagement & SDOH](#17-patient-engagement--sdoh)
18. [Ambient AI Documentation](#18-ambient-ai-documentation)
19. [Research & Genomics](#19-research--genomics)
20. [AI Marketplace](#20-ai-marketplace)

---

## 1. Patients

Prefix: `/api/v1/patients`

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/patients` | List patients with pagination, search, and risk-level filtering | `require_auth` | Query: `offset`, `limit`, `search`, `risk_level` | `PaginatedResponse[PatientSummary]` |
| `POST` | `/api/v1/patients` | Create a new patient (FHIR R4 compatible) | `require_auth` | Body: `PatientCreate` | `PatientResponse` (201) |
| `GET` | `/api/v1/patients/{patient_id}` | Get a single patient by UUID | `require_auth` | Path: `patient_id` (UUID) | `PatientResponse` |
| `PATCH` | `/api/v1/patients/{patient_id}` | Partial update of a patient record | `require_auth` | Path: `patient_id`; Body: `PatientUpdate` | `PatientResponse` |
| `DELETE` | `/api/v1/patients/{patient_id}` | Soft-delete a patient | `require_auth` | Path: `patient_id` (UUID) | 204 No Content |

---

## 2. Agents

Prefix: `/api/v1/agents`

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/agents/decisions` | List agent decisions with filtering | `require_auth` | Query: `agent_name`, `patient_id`, `trace_id`, `requires_hitl`, `offset`, `limit` | `PaginatedResponse[AgentDecisionResponse]` |
| `GET` | `/api/v1/agents/decisions/{decision_id}` | Get a specific agent decision | `require_auth` | Path: `decision_id` (UUID) | `AgentDecisionResponse` |
| `GET` | `/api/v1/agents/interactions` | List inter-agent interactions | `require_auth` | Query: `trace_id`, `sender_agent`, `offset`, `limit` | `PaginatedResponse[AgentInteractionResponse]` |
| `GET` | `/api/v1/agents/status` | Aggregate status for all agents | `require_auth` | -- | `list[AgentStatusResponse]` |
| `GET` | `/api/v1/agents/model-cards/{agent_name}` | Retrieve the model card for a specific agent | `require_auth` | Path: `agent_name` (str) | Model card JSON |

---

## 3. Alerts

Prefix: `/api/v1/alerts`

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/alerts` | List clinical alerts with filtering | `require_auth` | Query: `patient_id`, `severity`, `status`, `category`, `offset`, `limit` | `PaginatedResponse[AlertSummary]` |
| `GET` | `/api/v1/alerts/{alert_id}` | Get a single alert | `require_auth` | Path: `alert_id` (UUID) | `AlertResponse` |
| `POST` | `/api/v1/alerts/{alert_id}/acknowledge` | Acknowledge an active alert | `require_auth` | Path: `alert_id`; Body: `AlertAcknowledge` | `AlertResponse` |
| `POST` | `/api/v1/alerts/{alert_id}/resolve` | Resolve an alert with notes | `require_auth` | Path: `alert_id`; Body: `AlertResolve` | `AlertResponse` |
| `GET` | `/api/v1/alerts/active/count` | Get counts of active alerts grouped by severity | `require_auth` | -- | `{ total, by_severity }` |

---

## 4. Dashboard

Prefix: `/api/v1/dashboard`

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/dashboard/overview` | High-level dashboard: patient counts, alerts, agent activity, HITL pending | `require_auth` | -- | `{ patients, alerts, agents }` |
| `GET` | `/api/v1/dashboard/patients/at-risk` | Highest-risk patients for watchlist | `require_auth` | Query: `limit` (1-50) | Array of patient risk summaries |
| `GET` | `/api/v1/dashboard/alerts/recent` | Recent alert feed | `require_auth` | Query: `limit` (1-100) | Array of alert summaries |
| `GET` | `/api/v1/dashboard/agents/performance` | Agent performance metrics (confidence, tokens, cost, HITL rate) | `require_auth` | -- | Array of per-agent performance objects |

---

## 5. FHIR R4 Interoperability

Prefix: `/api/v1/fhir`

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/fhir/Patient/{patient_id}` | Get patient as FHIR R4 Patient resource | `require_auth` | Path: `patient_id` (UUID) | FHIR R4 Patient JSON |
| `GET` | `/api/v1/fhir/Patient/{patient_id}/Observation` | Get observations as FHIR R4 Bundle (searchset) | `require_auth` | Path: `patient_id` (UUID) | FHIR R4 Bundle |
| `GET` | `/api/v1/fhir/Observation/{observation_id}` | Get a single FHIR R4 Observation | `require_auth` | Path: `observation_id` (UUID) | FHIR R4 Observation JSON |
| `POST` | `/api/v1/fhir/Bundle` | Ingest a FHIR R4 Bundle | `require_auth` | Body: FHIR Bundle JSON (`resourceType: "Bundle"`) | Ingestion result |

---

## 6. Remote Patient Monitoring (RPM)

Prefix: `/api/v1/rpm`

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/rpm/ingest` | Ingest device vitals and run the full RPM agent pipeline | `VITALS_WRITE` | Query: `patient_id`; Body: `vitals` (array) | `PipelineResultResponse` |
| `GET` | `/api/v1/rpm/dashboard/summary` | Aggregate RPM dashboard summary (active patients, critical alerts, adherence) | `VITALS_READ` | -- | `{ active_patients, critical_alerts, devices_online, avg_adherence }` |
| `GET` | `/api/v1/rpm/dashboard/{patient_id}` | Patient-specific RPM dashboard (latest vitals, risk, alerts, trends) | `VITALS_READ` | Path: `patient_id` (UUID) | Patient RPM dashboard JSON |

---

## 7. Telehealth

Prefix: `/api/v1/telehealth`

### Sessions

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/telehealth/sessions` | Create a new telehealth session | `ENCOUNTERS_WRITE` | Body: `SessionCreate` | `SessionResponse` |
| `GET` | `/api/v1/telehealth/sessions` | List recent telehealth sessions (queue view) | `ENCOUNTERS_READ` | -- | `{ sessions }` |
| `GET` | `/api/v1/telehealth/sessions/{session_id}` | Get session status | `ENCOUNTERS_READ` | Path: `session_id` | Session JSON |

### Pre-Visit & Clinical

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/telehealth/symptom-check` | Pre-visit symptom assessment | `require_auth` | Body: `SymptomCheckRequest` | `SymptomCheckResponse` |
| `POST` | `/api/v1/telehealth/sessions/{session_id}/prepare` | Generate pre-visit summary | `ENCOUNTERS_READ` | Path: `session_id` | Visit preparation JSON |
| `POST` | `/api/v1/telehealth/sessions/{session_id}/note` | Generate SOAP clinical note | `ENCOUNTERS_WRITE` | Path: `session_id`; Body: encounter data | Clinical note JSON |
| `POST` | `/api/v1/telehealth/sessions/{session_id}/follow-up` | Generate follow-up care plan | `CARE_PLANS_WRITE` | Path: `session_id`; Body: conditions, symptoms, meds | Follow-up plan JSON |
| `POST` | `/api/v1/telehealth/medication-review` | Review medications for interactions | `ENCOUNTERS_READ` | Body: medications, conditions | Review result JSON |
| `POST` | `/api/v1/telehealth/schedule` | Schedule a telehealth appointment | `ENCOUNTERS_WRITE` | Body: patient_id, visit_type, urgency, preferences | Scheduling result JSON |

### Video

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/telehealth/sessions/{session_id}/video/start` | Allocate video room and return provider credentials | `ENCOUNTERS_WRITE` | Path: `session_id` | `{ room_url, token, expires_at }` |
| `GET` | `/api/v1/telehealth/sessions/{session_id}/video/token` | Generate video token for a participant | `ENCOUNTERS_READ` | Path: `session_id`; Query: `role` | `{ token, room_name, expires_at }` |
| `POST` | `/api/v1/telehealth/sessions/{session_id}/video/end` | End video session and clean up room | `ENCOUNTERS_WRITE` | Path: `session_id` | `{ status, room_cleaned_up }` |

### HITL Clinical Notes

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/telehealth/sessions/{session_id}/notes` | List all clinical notes for a session | `ENCOUNTERS_READ` | Path: `session_id` | `{ notes }` |
| `PUT` | `/api/v1/telehealth/sessions/{session_id}/note` | Amend a clinical note (provider edits) | `ENCOUNTERS_WRITE` | Body: `AmendNoteRequest` (note_id, amendments) | Amended note JSON |
| `POST` | `/api/v1/telehealth/sessions/{session_id}/note/sign` | Sign and finalize a clinical note | `ENCOUNTERS_WRITE` | Body: `SignNoteRequest` (note_id, amendments) | Signed note JSON |

---

## 8. Operations

Prefix: `/api/v1/operations`

### Prior Authorization

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/prior-auth/evaluate` | Evaluate whether a procedure requires prior auth | `require_auth` | Body: `{ patient_id, ... }` | Evaluation result |
| `POST` | `/api/v1/operations/prior-auth/submit` | Submit a prior authorization request | `require_auth` | Body: `{ patient_id, ... }` | Submission result |
| `POST` | `/api/v1/operations/prior-auth/status` | Check status of a prior authorization | `require_auth` | Body: `{ auth_id, ... }` | Status result |

### Insurance Verification

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/insurance/verify` | Verify patient insurance eligibility | `require_auth` | Body: `{ patient_id, ... }` | Eligibility result |
| `POST` | `/api/v1/operations/insurance/benefits` | Check insurance benefits for a service type | `require_auth` | Body: `{ patient_id, ... }` | Benefits result |
| `POST` | `/api/v1/operations/insurance/estimate` | Estimate patient out-of-pocket costs | `require_auth` | Body: `{ patient_id, ... }` | Cost estimate |

### Referral Coordination

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/referrals/create` | Create a new referral | `require_auth` | Body: `{ patient_id, ... }` | Referral result |
| `POST` | `/api/v1/operations/referrals/match-specialist` | Find matching specialists for a referral | `require_auth` | Body: referral criteria | Specialist match list |
| `POST` | `/api/v1/operations/referrals/track` | Track status of a referral | `require_auth` | Body: `{ referral_id, ... }` | Tracking result |

### Task Orchestration

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/tasks/create` | Create a new operational task | `require_auth` | Body: `{ patient_id, ... }` | Task result |
| `POST` | `/api/v1/operations/tasks/workflow` | Create a multi-step workflow | `require_auth` | Body: `{ patient_id, steps, ... }` | Workflow result |
| `POST` | `/api/v1/operations/tasks/sla` | Check SLA compliance across tasks | `require_role("admin")` | Body: SLA parameters | SLA report |
| `POST` | `/api/v1/operations/tasks/queue` | Get current task queue | `require_auth` | Body: filter criteria | Task queue |

### Billing

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/billing/validate` | Validate encounter for billing readiness | `require_auth` | Body: `{ patient_id, ... }` | Validation result |
| `POST` | `/api/v1/operations/billing/check-coding` | Check CPT/ICD-10 coding accuracy | `require_auth` | Body: coding data | Coding check result |
| `POST` | `/api/v1/operations/billing/prepare-claim` | Prepare a claim for submission | `require_auth` | Body: `{ patient_id, ... }` | Prepared claim |
| `POST` | `/api/v1/operations/billing/audit` | Run billing audit across recent encounters | `require_role("admin")` | Body: audit parameters | Audit report |

### Workflow Engine

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/workflows/create` | Create a workflow from a template | `require_auth` | Body: `{ workflow_type, patient_id, priority, steps }` | Workflow summary |
| `GET` | `/api/v1/operations/workflows/templates` | List available workflow templates | `require_auth` | -- | `{ templates }` |
| `GET` | `/api/v1/operations/workflows/{workflow_id}` | Get workflow status and progress | `require_auth` | Path: `workflow_id` | Workflow summary |
| `GET` | `/api/v1/operations/workflows` | List all workflows for the organization | `require_auth` | -- | `{ workflows }` |
| `POST` | `/api/v1/operations/workflows/{workflow_id}/steps/{step_id}/complete` | Mark a workflow step as completed | `require_auth` | Path: `workflow_id`, `step_id`; Body: `{ output }` | Updated workflow summary |
| `POST` | `/api/v1/operations/workflows/sla-violations` | Check for SLA violations across active workflows | `require_role("admin")` | -- | `{ violations }` |

### Payer Integration

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/operations/payers` | List registered payer connectors | `require_auth` | -- | `{ payers }` |
| `POST` | `/api/v1/operations/payers/{payer_id}/eligibility` | Check eligibility via payer connector | `require_auth` | Path: `payer_id`; Body: `EligibilityRequest` | Eligibility response |
| `POST` | `/api/v1/operations/payers/{payer_id}/submit-claim` | Submit a claim via payer connector | `require_auth` | Path: `payer_id`; Body: `ClaimSubmission` | Claim response |
| `POST` | `/api/v1/operations/payers/{payer_id}/claim-status` | Check claim status via payer connector | `require_auth` | Path: `payer_id`; Body: `{ claim_id }` | Claim status |

### Operations Analytics

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/analytics/summary` | Generate operations summary report | `require_role("admin")` | Body: report parameters | Summary report |
| `POST` | `/api/v1/operations/analytics/bottlenecks` | Identify operational bottlenecks | `require_role("admin")` | Body: analysis criteria | Bottleneck analysis |
| `POST` | `/api/v1/operations/analytics/kpis` | Generate KPI report | `require_role("admin")` | Body: KPI parameters | KPI report |
| `POST` | `/api/v1/operations/analytics/trends` | Analyze operational trends | `require_role("admin")` | Body: trend parameters | Trend analysis |

### Legacy / Scheduling

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/operations/schedule/suggest` | Get AI-suggested appointment slots | `require_auth` | Body: `{ patient_id, ... }` | Slot suggestions |
| `POST` | `/api/v1/operations/compliance/check` | Run compliance audit check | `require_role("admin")` | Body: check criteria | Compliance result |
| `POST` | `/api/v1/operations/resources/optimize` | Run resource optimization analysis | `require_role("admin")` | Body: resource data | Optimization result |

---

## 9. Analytics

Prefix: `/api/v1/analytics`

All analytics endpoints include HIPAA audit logging. Endpoints returning patient-level data additionally log PHI access records.

### Population Health

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/analytics/population-health` | Run population health analysis | `require_auth` | Body: `{ action, ... }` | Analysis result |
| `POST` | `/api/v1/analytics/population-health/risk-stratification` | Stratify patient population by risk level | `require_auth` | Body: stratification params | Risk stratification (PHI logged) |
| `GET` | `/api/v1/analytics/population-health/kpis` | Get population health KPI summary | `require_auth` | -- | KPI summary |
| `POST` | `/api/v1/analytics/population-health/quality-metrics` | Generate HEDIS-style quality metrics | `require_auth` | Body: metric parameters | Quality metrics |

### Outcome Tracking

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/analytics/outcomes` | Track clinical outcomes for a patient | `require_auth` | Body: `{ patient_id, action, ... }` | Outcome data (PHI logged) |
| `POST` | `/api/v1/analytics/outcomes/adherence` | Check care plan adherence for a patient | `require_auth` | Body: `{ patient_id, ... }` | Adherence data (PHI logged) |
| `POST` | `/api/v1/analytics/outcomes/effectiveness` | Assess treatment effectiveness across patients | `require_auth` | Body: effectiveness params | Effectiveness report (PHI logged) |

### Cost Analysis

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/analytics/costs` | Run cost analysis and ROI calculations | `require_auth` | Body: `{ action, ... }` | Cost analysis |
| `POST` | `/api/v1/analytics/costs/rpm-roi` | Calculate RPM program ROI | `require_role("admin")` | Body: ROI parameters | ROI result |
| `POST` | `/api/v1/analytics/costs/forecast` | Project savings over multiple years | `require_role("admin")` | Body: forecast parameters | Savings forecast |

### Cohort Segmentation

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/analytics/cohorts` | Create a patient cohort from criteria or template | `require_auth` | Body: `{ action, criteria, ... }` | Cohort result (access logged) |
| `GET` | `/api/v1/analytics/cohorts/templates` | List available cohort templates | `require_auth` | -- | Template list |
| `POST` | `/api/v1/analytics/cohorts/compare` | Compare two cohorts on key metrics | `require_auth` | Body: `{ cohort_a_id, cohort_b_id, ... }` | Comparison result (access logged) |

### Readmission Risk

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/analytics/readmission-risk` | Predict 30-day readmission risk for a patient | `require_auth` | Body: `{ patient_id, ... }` | Risk prediction (PHI logged) |
| `POST` | `/api/v1/analytics/readmission-risk/batch` | Predict readmission risk for multiple patients | `require_auth` | Body: `{ patient_ids, ... }` | Batch predictions (PHI logged) |
| `POST` | `/api/v1/analytics/readmission-risk/explain` | Explain a readmission risk prediction | `require_auth` | Body: `{ patient_id, ... }` | Explanation (PHI logged) |

### Cost/Risk Insight

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/analytics/cost-risk/drivers` | Analyze cost drivers across the population | `require_role("admin")` | Body: analysis params | Cost driver report |
| `POST` | `/api/v1/analytics/cost-risk/correlation` | Analyze risk-cost correlations | `require_role("admin")` | Body: correlation params | Correlation analysis |
| `POST` | `/api/v1/analytics/cost-risk/intervention` | Model the financial impact of an intervention | `require_role("admin")` | Body: intervention params | Impact analysis |
| `POST` | `/api/v1/analytics/cost-risk/opportunities` | Scan for cost reduction opportunities | `require_role("admin")` | Body: scan params | Opportunity list |

### Executive Intelligence

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/analytics/executive/summary` | Generate executive summary | `require_role("admin")` | -- | Executive summary |
| `POST` | `/api/v1/analytics/executive/scorecard` | Generate KPI scorecard | `require_role("admin")` | Body: scorecard params | KPI scorecard |
| `POST` | `/api/v1/analytics/executive/brief` | Generate strategic briefing | `require_role("admin")` | Body: brief params | Strategic brief |
| `POST` | `/api/v1/analytics/executive/department` | Generate department-specific report | `require_role("admin")` | Body: `{ department, ... }` | Department report |
| `GET` | `/api/v1/analytics/executive/trends` | Generate executive trend digest | `require_role("admin")` | -- | Trend digest |

---

## 10. Compliance & Governance

Prefix: `/api/v1/compliance`

### HIPAA Compliance

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/compliance/hipaa/scan` | Run a HIPAA compliance scan across platform operations | `require_auth` | Body: scan parameters | Scan result |
| `GET` | `/api/v1/compliance/hipaa/status` | Get current HIPAA compliance status and scores | `require_auth` | -- | Compliance status |
| `POST` | `/api/v1/compliance/hipaa/audit-log` | Query the HIPAA audit log for PHI access events | `require_auth` | Body: query filters | Audit log entries |

### AI Governance

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/compliance/ai-governance/models` | List all registered AI models with governance status | `require_auth` | -- | Model registry |
| `POST` | `/api/v1/compliance/ai-governance/audit` | Audit a specific AI model for drift, bias, and performance | `require_auth` | Body: `{ model_id, ... }` | Audit report |
| `POST` | `/api/v1/compliance/ai-governance/drift-check` | Check a model for data drift using PSI | `require_auth` | Body: `{ model_id, ... }` | Drift check result |

### Consent Management

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/compliance/consent/capture` | Capture patient consent for a specific purpose | `require_auth` | Body: `{ patient_id, purpose, ... }` | Consent record |
| `POST` | `/api/v1/compliance/consent/revoke` | Revoke patient consent | `require_auth` | Body: `{ patient_id, purpose, ... }` | Revocation result |
| `POST` | `/api/v1/compliance/consent/status` | Get consent status for a patient across all purposes | `require_auth` | Body: `{ patient_id }` | Consent status |
| `GET` | `/api/v1/compliance/consent/audit-trail` | Get the consent audit trail for compliance reporting | `require_auth` | -- | Audit trail |

### Regulatory Reporting

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/compliance/reports/generate` | Generate a compliance report (HIPAA, SOC2, HITRUST, etc.) | `require_auth` | Body: `{ framework, ... }` | Compliance report |
| `POST` | `/api/v1/compliance/reports/gap-analysis` | Run a gap analysis for a compliance framework | `require_auth` | Body: `{ framework, ... }` | Gap analysis |
| `GET` | `/api/v1/compliance/frameworks` | List all compliance frameworks and their status | `require_auth` | -- | Framework list |

---

## 11. Digital Twin

Prefix: `/api/v1/digital-twin`

### Patient Digital Twin

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/digital-twin/twin/build` | Build a patient digital twin from clinical data | `require_auth` | Body: `{ patient_id, ... }` | Twin result |
| `POST` | `/api/v1/digital-twin/twin/update` | Update an existing digital twin with new observations | `require_auth` | Body: `{ patient_id, ... }` | Updated twin |
| `GET` | `/api/v1/digital-twin/twin/state` | Get current digital twin state snapshot | `require_auth` | -- | Twin state |
| `GET` | `/api/v1/digital-twin/twin/timeline` | Get projected health timeline | `require_auth` | -- | Health timeline |

### What-If Scenarios

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/digital-twin/scenario/medication` | Simulate the effect of a medication change on vitals | `require_auth` | Body: `{ patient_id, medication, ... }` | Simulation result |
| `POST` | `/api/v1/digital-twin/scenario/lifestyle` | Simulate the impact of lifestyle changes on health metrics | `require_auth` | Body: `{ patient_id, changes, ... }` | Simulation result |
| `POST` | `/api/v1/digital-twin/scenario/treatment-stop` | Simulate projected deterioration from stopping treatment | `require_auth` | Body: `{ patient_id, treatment, ... }` | Deterioration projection |
| `POST` | `/api/v1/digital-twin/scenario/compare` | Compare multiple what-if scenarios side by side | `require_auth` | Body: `{ patient_id, scenarios, ... }` | Comparison result |

### Predictive Trajectory

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/digital-twin/trajectory/forecast` | Forecast health trajectory over 30/60/90 days | `require_auth` | Body: `{ patient_id, horizon, ... }` | Trajectory forecast |
| `GET` | `/api/v1/digital-twin/trajectory/trends` | Get trend analysis for patient health metrics | `require_auth` | -- | Trend analysis |
| `POST` | `/api/v1/digital-twin/trajectory/deterioration` | Assess risk of clinical deterioration events | `require_auth` | Body: `{ patient_id, ... }` | Deterioration risk |

### Treatment Optimization

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/digital-twin/optimize/plan` | Optimize care plan and generate alternative strategies | `require_auth` | Body: `{ patient_id, ... }` | Optimized plan |
| `POST` | `/api/v1/digital-twin/optimize/interventions` | Rank interventions by efficacy, cost, and adherence | `require_auth` | Body: `{ patient_id, ... }` | Ranked interventions |
| `POST` | `/api/v1/digital-twin/optimize/cost-effectiveness` | Compare treatment options by QALY-based cost-effectiveness | `require_auth` | Body: treatment options | Cost-effectiveness analysis |

---

## 12. Imaging & Radiology

Prefix: `/api/v1/imaging`

### Imaging Ingestion

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/imaging/studies/ingest` | Ingest a DICOM imaging study | `require_auth` | Body: `{ patient_id, ... }` | Ingestion result |
| `GET` | `/api/v1/imaging/studies/{patient_id}` | Query imaging studies for a patient | `require_auth` | Path: `patient_id` | Study list |

### Image Analysis

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/imaging/analysis/analyze` | Run AI analysis on an imaging study | `require_auth` | Body: `{ patient_id, study_id, ... }` | Analysis result |
| `POST` | `/api/v1/imaging/analysis/compare-priors` | Compare current study to prior imaging | `require_auth` | Body: `{ study_id, prior_study_id, ... }` | Comparison result |

### Radiology Reports

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/imaging/reports/generate` | Generate a preliminary radiology report | `require_auth` | Body: `{ patient_id, study_id, ... }` | Report draft |
| `POST` | `/api/v1/imaging/reports/addendum` | Add an addendum to a radiology report | `require_auth` | Body: `{ report_id, ... }` | Updated report |

### Imaging Workflow

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/imaging/workflow/assign` | Assign a study to a radiologist worklist | `require_auth` | Body: `{ study_id, radiologist_id, ... }` | Assignment result |
| `GET` | `/api/v1/imaging/workflow/worklist` | Get radiology worklist summary | `require_auth` | -- | Worklist summary |
| `GET` | `/api/v1/imaging/workflow/sla-check` | Check SLA compliance for radiology reads | `require_auth` | -- | SLA status |

### Critical Finding Alerts

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/imaging/critical/evaluate` | Evaluate imaging findings for critical results | `require_auth` | Body: `{ patient_id, findings, ... }` | Evaluation result |
| `POST` | `/api/v1/imaging/critical/escalate` | Escalate a critical imaging finding | `require_auth` | Body: `{ finding_id, ... }` | Escalation result |
| `GET` | `/api/v1/imaging/critical/log` | Get critical finding alert log (ACR compliance) | `require_auth` | -- | Alert log |

---

## 13. Labs

Prefix: `/api/v1/labs`

### Lab Orders

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/labs/orders/create` | Create a new lab order | `require_auth` | Body: `{ patient_id, tests, ... }` | Order result |
| `POST` | `/api/v1/labs/orders/cancel` | Cancel a lab order | `require_auth` | Body: `{ lab_order_id, ... }` | Cancellation result |
| `GET` | `/api/v1/labs/orders/{order_id}/status` | Get lab order status | `require_auth` | Path: `order_id` | Order status |
| `POST` | `/api/v1/labs/orders/suggest-panels` | Suggest lab panels based on conditions and medications | `require_auth` | Body: `{ patient_id, conditions, ... }` | Suggested panels |

### Lab Results

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/labs/results/ingest` | Ingest lab results from external systems | `require_auth` | Body: `{ patient_id, results, ... }` | Ingestion result |
| `POST` | `/api/v1/labs/results/flag-abnormals` | Flag abnormal lab values | `require_auth` | Body: `{ results, ... }` | Flagged abnormals |
| `GET` | `/api/v1/labs/results/{patient_id}` | Get latest lab results for a patient | `require_auth` | Path: `patient_id` | Results list |
| `POST` | `/api/v1/labs/results/compare` | Compare current results to prior results | `require_auth` | Body: `{ patient_id, ... }` | Comparison result |

### Lab Trends

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/labs/trends/analyze` | Analyze lab value trends over time | `require_auth` | Body: `{ patient_id, test_codes, ... }` | Trend analysis |
| `POST` | `/api/v1/labs/trends/project` | Project lab value trajectory | `require_auth` | Body: trend parameters | Trajectory projection |
| `GET` | `/api/v1/labs/trends/summary/{patient_id}` | Get trend summary for a patient | `require_auth` | Path: `patient_id` | Trend summary |

### Critical Value Alerts

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/labs/critical/evaluate` | Evaluate lab results for critical values | `require_auth` | Body: `{ patient_id, results, ... }` | Evaluation result |
| `POST` | `/api/v1/labs/critical/escalate` | Escalate a critical value alert | `require_auth` | Body: `{ alert_id, ... }` | Escalation result |
| `POST` | `/api/v1/labs/critical/acknowledge` | Acknowledge a critical value alert | `require_auth` | Body: `{ alert_id, ... }` | Acknowledgment result |
| `GET` | `/api/v1/labs/critical/log` | Get critical value alert log (CLIA compliance) | `require_auth` | -- | Alert log |

---

## 14. Pharmacy

Prefix: `/api/v1/pharmacy`

### Prescriptions

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/pharmacy/prescriptions/create` | Create a new e-prescription | `require_auth` | Body: `{ patient_id, medication, ... }` | Prescription result |
| `POST` | `/api/v1/pharmacy/prescriptions/transmit` | Sign and transmit a prescription to pharmacy | `require_auth` | Body: `{ patient_id, prescription_id, ... }` | Transmission result |
| `GET` | `/api/v1/pharmacy/prescriptions/history/{patient_id}` | Get prescription history for a patient | `require_auth` | Path: `patient_id` | Prescription history |

### Drug Interactions

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/pharmacy/interactions/check` | Check drug-drug interactions | `require_auth` | Body: `{ patient_id, medications, ... }` | Interaction check |
| `POST` | `/api/v1/pharmacy/interactions/safety-check` | Full medication safety check (interactions, allergies, contraindications) | `require_auth` | Body: `{ patient_id, medications, ... }` | Safety report |

### Formulary

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/pharmacy/formulary/check` | Check formulary coverage for a medication | `require_auth` | Body: `{ medication, plan_id, ... }` | Coverage result |
| `POST` | `/api/v1/pharmacy/formulary/alternatives` | Suggest formulary-preferred alternatives | `require_auth` | Body: `{ medication, ... }` | Alternatives list |
| `POST` | `/api/v1/pharmacy/formulary/cost-estimate` | Estimate patient cost for a medication | `require_auth` | Body: `{ medication, ... }` | Cost estimate |

### Pharmacy Routing

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/pharmacy/routing/find-pharmacy` | Find nearby pharmacies in network | `require_auth` | Body: `{ zip_code, ... }` | Pharmacy list |
| `POST` | `/api/v1/pharmacy/routing/transmit` | Transmit prescription to selected pharmacy | `require_auth` | Body: `{ prescription_id, pharmacy_id, ... }` | Transmission result |

### Refill Automation

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/pharmacy/refills/check` | Check refill eligibility for a patient's medications | `require_auth` | Body: `{ patient_id, ... }` | Refill eligibility |
| `POST` | `/api/v1/pharmacy/refills/initiate` | Initiate a prescription refill | `require_auth` | Body: `{ patient_id, prescription_id, ... }` | Refill result |

### Medication Adherence

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/pharmacy/adherence/calculate` | Calculate medication adherence metrics (PDC/MPR) | `require_auth` | Body: `{ patient_id, ... }` | Adherence metrics |
| `POST` | `/api/v1/pharmacy/adherence/report` | Generate medication adherence report | `require_auth` | Body: `{ patient_id, ... }` | Adherence report |
| `POST` | `/api/v1/pharmacy/adherence/interventions` | Identify patients needing adherence interventions | `require_auth` | Body: filter criteria | Intervention triggers |

---

## 15. Revenue Cycle Management (RCM)

Prefix: `/api/v1/rcm`

### Charge Capture

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/rcm/charges/capture` | Capture billable charges from an encounter | `require_auth` | Body: `{ patient_id, encounter_id, ... }` | Charge capture result |
| `POST` | `/api/v1/rcm/charges/estimate` | Estimate reimbursement for a set of codes | `require_auth` | Body: `{ codes, ... }` | Reimbursement estimate |

### Claims Optimization

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/rcm/claims/optimize` | Scrub and optimize a claim before submission | `require_auth` | Body: claim data | Optimized claim |
| `GET` | `/api/v1/rcm/claims/clean-rate` | Get clean claim rate metrics | `require_auth` | -- | Clean rate metrics |

### Denial Management

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/rcm/denials/analyze` | Analyze a denied claim and recommend appeal strategy | `require_auth` | Body: `{ claim_id, ... }` | Denial analysis |
| `POST` | `/api/v1/rcm/denials/appeal` | Generate an appeal letter for a denied claim | `require_auth` | Body: `{ claim_id, ... }` | Appeal letter |
| `GET` | `/api/v1/rcm/denials/trends` | Get denial trend analysis | `require_auth` | -- | Denial trends |

### Revenue Integrity

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/rcm/integrity/scan` | Pre-bill chart scan for missed diagnoses and under-coding | `require_auth` | Body: `{ patient_id, ... }` | Scan result |
| `POST` | `/api/v1/rcm/integrity/hcc-gaps` | HCC coding gap analysis for risk adjustment | `require_auth` | Body: `{ patient_id, ... }` | HCC gap report |
| `GET` | `/api/v1/rcm/integrity/leakage` | Revenue leakage report | `require_auth` | -- | Leakage report |

### Payment Posting

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/rcm/payments/post` | Post a payment against a claim | `require_auth` | Body: `{ claim_id, amount, ... }` | Payment result |
| `POST` | `/api/v1/rcm/payments/reconcile` | Reconcile an ERA/835 against claims | `require_auth` | Body: ERA data | Reconciliation result |
| `GET` | `/api/v1/rcm/payments/ar-aging` | Accounts receivable aging report | `require_auth` | -- | AR aging report |
| `GET` | `/api/v1/rcm/payments/collections` | Collection performance summary | `require_auth` | -- | Collections summary |

---

## 16. Mental Health

Prefix: `/api/v1/mental-health`

### Screening

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/mental-health/screening/phq9` | Score PHQ-9 depression screening | `require_auth` | Body: `{ patient_id, responses, ... }` | PHQ-9 result |
| `POST` | `/api/v1/mental-health/screening/gad7` | Score GAD-7 anxiety screening | `require_auth` | Body: `{ patient_id, responses, ... }` | GAD-7 result |
| `POST` | `/api/v1/mental-health/screening/audit-c` | Score AUDIT-C alcohol misuse screening | `require_auth` | Body: `{ patient_id, responses, ... }` | AUDIT-C result |
| `POST` | `/api/v1/mental-health/screening/comprehensive` | Run all screening instruments at once | `require_auth` | Body: `{ patient_id, responses, ... }` | Comprehensive result |
| `GET` | `/api/v1/mental-health/screening/history/{patient_id}` | Retrieve screening history with trends | `require_auth` | Path: `patient_id` | Screening history |

### Behavioral Health Workflow

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/mental-health/workflow/referral` | Create a behavioral health referral from screening results | `require_auth` | Body: `{ patient_id, ... }` | Referral result |
| `POST` | `/api/v1/mental-health/workflow/schedule` | Schedule a therapy session with availability matching | `require_auth` | Body: `{ patient_id, ... }` | Scheduling result |
| `POST` | `/api/v1/mental-health/workflow/follow-up` | Generate follow-up assessment for treatment adherence | `require_auth` | Body: `{ patient_id, ... }` | Follow-up result |
| `POST` | `/api/v1/mental-health/workflow/treatment-plan` | Create a structured behavioral health treatment plan | `require_auth` | Body: `{ patient_id, ... }` | Treatment plan |

### Crisis Detection

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/mental-health/crisis/assess` | Assess crisis risk from scores, flags, and social factors | `require_auth` | Body: `{ patient_id, ... }` | Crisis risk assessment |
| `POST` | `/api/v1/mental-health/crisis/screen-text` | Scan free-text for crisis keywords and indicators | `require_auth` | Body: `{ patient_id, text, ... }` | Text screening result |
| `POST` | `/api/v1/mental-health/crisis/safety-plan` | Generate a personalized safety plan template | `require_auth` | Body: `{ patient_id, ... }` | Safety plan |
| `POST` | `/api/v1/mental-health/crisis/escalate` | Trigger escalation protocol based on risk level | `require_auth` | Body: `{ patient_id, ... }` | Escalation result |

### Therapeutic Engagement

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/mental-health/engagement/mood-check` | Submit or retrieve a structured mood check-in | `require_auth` | Body: `{ patient_id, mood, ... }` | Mood check result |
| `POST` | `/api/v1/mental-health/engagement/cbt-exercise` | Select and deliver an appropriate CBT exercise | `require_auth` | Body: `{ patient_id, symptoms, ... }` | CBT exercise |
| `POST` | `/api/v1/mental-health/engagement/mindfulness` | Get a contextual mindfulness exercise | `require_auth` | Body: `{ patient_id, stress_level, ... }` | Mindfulness exercise |
| `GET` | `/api/v1/mental-health/engagement/progress/{patient_id}` | Aggregate progress summary (mood, exercises, screening) | `require_auth` | Path: `patient_id` | Progress summary |

---

## 17. Patient Engagement & SDOH

Prefix: `/api/v1/patient-engagement`

### Health Literacy

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/patient-engagement/literacy/adapt` | Adapt clinical content to patient reading level | `require_auth` | Body: `{ patient_id, content, ... }` | Adapted content |
| `POST` | `/api/v1/patient-engagement/literacy/assess` | Assess readability of clinical content | `require_auth` | Body: `{ content, ... }` | Readability assessment |

### Multilingual Communication

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/patient-engagement/translate` | Translate clinical content to target language | `require_auth` | Body: `{ content, target_language, ... }` | Translated content |
| `GET` | `/api/v1/patient-engagement/translate/languages` | Get list of supported languages | `require_auth` | -- | Language list |

### Conversational Triage

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/patient-engagement/triage/assess` | Triage patient symptoms | `require_auth` | Body: `{ patient_id, symptoms, ... }` | Triage result |
| `POST` | `/api/v1/patient-engagement/triage/recommendation` | Get triage recommendation | `require_auth` | Body: `{ symptoms, ... }` | Recommendation |

### Care Navigation

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/patient-engagement/navigation/create-journey` | Create a care navigation journey | `require_auth` | Body: `{ patient_id, ... }` | Journey plan |
| `POST` | `/api/v1/patient-engagement/navigation/next-step` | Get next step in care journey | `require_auth` | Body: `{ journey_id, ... }` | Next step |

### SDOH Screening

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/patient-engagement/sdoh/screen` | Screen patient for social determinants of health | `require_auth` | Body: `{ patient_id, responses, ... }` | SDOH screening result |
| `GET` | `/api/v1/patient-engagement/sdoh/questions` | Get SDOH screening questions | `require_auth` | -- | Question set |

### Community Resources

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/patient-engagement/resources/find` | Find community resources matching patient needs | `require_auth` | Body: `{ patient_id, needs, ... }` | Resource list |
| `POST` | `/api/v1/patient-engagement/resources/referral` | Create a referral to a community resource | `require_auth` | Body: `{ patient_id, resource_id, ... }` | Referral result |

### Motivational Engagement

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/patient-engagement/engagement/nudge` | Send a behavioral nudge to a patient | `require_auth` | Body: `{ patient_id, ... }` | Nudge result |
| `POST` | `/api/v1/patient-engagement/engagement/score` | Calculate patient engagement score | `require_auth` | Body: `{ patient_id, ... }` | Engagement score |
| `GET` | `/api/v1/patient-engagement/engagement/report` | Get engagement analytics report | `require_auth` | -- | Engagement report |

---

## 18. Ambient AI Documentation

Prefix: `/api/v1/ambient-ai`

### Ambient Listening

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/ambient-ai/session/start` | Start an ambient recording session for an encounter | `require_auth` | Body: `{ patient_id, encounter_id, ... }` | Session started |
| `POST` | `/api/v1/ambient-ai/transcribe` | Transcribe audio data from an encounter | `require_auth` | Body: `{ patient_id, audio_data, ... }` | Transcription result |
| `POST` | `/api/v1/ambient-ai/session/end` | End a recording session | `require_auth` | Body: `{ session_id, ... }` | Session ended |

### Speaker Diarization

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/ambient-ai/diarize` | Identify and label speakers in transcript segments | `require_auth` | Body: `{ transcript, ... }` | Diarized transcript |

### SOAP Note Generation

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/ambient-ai/soap/generate` | Generate a complete SOAP note from diarized transcript | `require_auth` | Body: `{ patient_id, transcript, ... }` | SOAP note |
| `POST` | `/api/v1/ambient-ai/soap/validate` | Validate a SOAP note for completeness | `require_auth` | Body: `{ note, ... }` | Validation result |

### Auto-Coding

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/ambient-ai/coding/encounter` | Generate ICD-10, CPT, and E&M codes for an encounter | `require_auth` | Body: `{ patient_id, note, ... }` | Suggested codes |
| `POST` | `/api/v1/ambient-ai/coding/validate` | Validate proposed billing codes | `require_auth` | Body: `{ codes, ... }` | Validation result |

### Provider Attestation

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/ambient-ai/attestation/submit` | Submit AI-generated documentation for provider review | `require_auth` | Body: `{ patient_id, note_id, ... }` | Submission result |
| `POST` | `/api/v1/ambient-ai/attestation/approve` | Provider approves and digitally signs documentation | `require_auth` | Body: `{ note_id, ... }` | Approval result |

---

## 19. Research & Genomics

Prefix: `/api/v1/research-genomics`

### Clinical Trial Matching

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/research-genomics/trials/match` | Match a patient to eligible clinical trials | `require_auth` | Body: `{ patient_id, ... }` | Trial matches |
| `POST` | `/api/v1/research-genomics/trials/eligibility` | Check patient eligibility for a specific trial | `require_auth` | Body: `{ patient_id, trial_id, ... }` | Eligibility result |
| `GET` | `/api/v1/research-genomics/trials/enrollment` | Get enrollment status for all active trials | `require_auth` | -- | Enrollment status |

### De-Identification

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/research-genomics/deidentify/dataset` | De-identify a dataset using HIPAA Safe Harbor | `require_auth` | Body: `{ records, method, ... }` | De-identified dataset |
| `POST` | `/api/v1/research-genomics/deidentify/verify` | Verify that a dataset is properly de-identified | `require_auth` | Body: `{ records, ... }` | Verification result |
| `POST` | `/api/v1/research-genomics/deidentify/scan` | Scan data for PHI before export | `require_auth` | Body: `{ records, ... }` | PHI scan result |
| `POST` | `/api/v1/research-genomics/deidentify/export` | Export a de-identified dataset for research use | `require_auth` | Body: `{ dataset_id, format, ... }` | Export result |

### Research Cohort

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/research-genomics/cohort/build` | Build a research cohort from clinical criteria | `require_auth` | Body: `{ criteria, ... }` | Cohort result |
| `POST` | `/api/v1/research-genomics/cohort/characteristics` | Analyze cohort demographic and clinical characteristics | `require_auth` | Body: `{ cohort_id, ... }` | Characteristics report |
| `POST` | `/api/v1/research-genomics/cohort/compare` | Compare two cohorts for balance assessment | `require_auth` | Body: `{ cohort_a, cohort_b, ... }` | Comparison result |
| `GET` | `/api/v1/research-genomics/cohort/templates` | List available cohort templates | `require_auth` | -- | Template list |

### Pharmacogenomics (PGx)

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/research-genomics/pgx/check` | Check drug-gene interactions for a medication | `require_auth` | Body: `{ patient_id, medication, ... }` | PGx interaction check |
| `POST` | `/api/v1/research-genomics/pgx/profile` | Get pharmacogenomic profile for a patient | `require_auth` | Body: `{ patient_id, ... }` | PGx profile |
| `POST` | `/api/v1/research-genomics/pgx/dose` | Get PGx-guided dose recommendation | `require_auth` | Body: `{ medication, genotype, ... }` | Dose recommendation |
| `GET` | `/api/v1/research-genomics/pgx/panel` | Get pharmacogenomic panel summary | `require_auth` | -- | Panel summary |

### Genetic Risk

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `POST` | `/api/v1/research-genomics/genetic/prs` | Calculate polygenic risk scores for a patient | `require_auth` | Body: `{ patient_id, ... }` | PRS result |
| `POST` | `/api/v1/research-genomics/genetic/monogenic` | Screen for high-impact monogenic variants | `require_auth` | Body: `{ patient_id, ... }` | Monogenic screen result |
| `POST` | `/api/v1/research-genomics/genetic/integrated-risk` | Calculate integrated clinical-genomic risk score | `require_auth` | Body: `{ patient_id, ... }` | Integrated risk score |
| `POST` | `/api/v1/research-genomics/genetic/report` | Generate comprehensive genetic risk report | `require_auth` | Body: `{ patient_id, ... }` | Genetic risk report |

---

## 20. AI Marketplace

Prefix: `/api/v1/marketplace`

### Agent Registry

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/marketplace/agents` | List all available agents in the marketplace | `require_auth` | Query: `category`, `tier`, `search` | Agent listing |
| `GET` | `/api/v1/marketplace/agents/{agent_id}` | Get details for a specific marketplace agent | `require_auth` | Path: `agent_id` | Agent details |
| `POST` | `/api/v1/marketplace/agents/publish` | Publish a new agent to the marketplace | `require_auth` | Body: agent metadata | Publication result |
| `POST` | `/api/v1/marketplace/agents/{agent_id}/install` | Install a marketplace agent to the current tenant | `require_auth` | Path: `agent_id`; Body: config | Installation result |
| `POST` | `/api/v1/marketplace/agents/{agent_id}/scan` | Run a security scan on a marketplace agent | `require_auth` | Path: `agent_id`; Body: `{ source_code }` | Security scan result |

### Analytics

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| `GET` | `/api/v1/marketplace/analytics` | Get aggregate marketplace analytics | `require_auth` | -- | Marketplace analytics |
| `GET` | `/api/v1/marketplace/analytics/{agent_id}` | Get usage analytics for a specific agent | `require_auth` | Path: `agent_id` | Agent analytics |

---

## Authentication & Middleware

All requests pass through the following middleware stack (executed in order):

1. **TracingMiddleware** -- Assigns a trace ID to each request for observability.
2. **TenantMiddleware** -- Resolves and enforces tenant isolation via `X-Tenant-ID`.
3. **RateLimitMiddleware** -- Rate limiting (enabled in production).
4. **SecurityHeadersMiddleware** -- Adds security response headers.
5. **CORSMiddleware** -- Cross-origin resource sharing.

### Auth Levels

| Level | Description |
|-------|-------------|
| `require_auth` | Bearer token authentication required. Any authenticated user. |
| `require_role("admin")` | Bearer token + admin role required. |
| `Permission.*` (RBAC) | Fine-grained permission checks (e.g., `VITALS_READ`, `ENCOUNTERS_WRITE`, `CARE_PLANS_WRITE`). Used in RPM and Telehealth modules. |

### Common Response Patterns

- **Paginated lists**: `{ items: [...], total: int, offset: int, limit: int }`
- **Agent pipeline results**: `{ trace_id, trigger_event, executed_agents, requires_hitl, ... }`
- **Error responses**: `{ detail: "error message" }` with appropriate HTTP status code (400, 404, 500)
- **Soft deletes**: Return 204 No Content; records are flagged `is_deleted = True`
