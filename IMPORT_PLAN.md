# InhealthUSA → Eminence HealthOS Import Plan

## Executive Summary

InhealthUSA is a production-grade Django EHR with mature RBAC, detailed clinical models, IoT device APIs, and billing/insurance systems. Eminence HealthOS is a modern FastAPI/SQLAlchemy platform with advanced AI agents, multi-tenant architecture, and a rich Next.js frontend — but its backend uses simplified/JSONB-blob models and lacks real RBAC, a proper Django admin, and production IoT ingestion. This plan imports InhealthUSA's battle-tested backend functionality into HealthOS's architecture.

---

## Gap Analysis: What InhealthUSA Has That HealthOS Is Missing

### 1. RBAC System (HIGH PRIORITY)

**InhealthUSA has:**
- `UserProfile` model with 5 distinct roles: `patient`, `doctor`, `nurse`, `office_admin`, `admin`
- Dedicated profile models for each role: `Provider` (doctor), `Nurse`, `OfficeAdministrator`
- Full `permissions.py` with decorators: `@require_role()`, `@require_patient_access`, `@require_patient_edit`, `@require_vital_edit`, `@require_provider_access`, `@require_provider_edit`
- Granular permission checks: `can_view_patient()`, `can_edit_patient()`, `can_view_provider()`, `can_edit_provider()`, `can_edit_vitals()`
- Role-specific dashboards and views for each role type
- Account lockout after failed login attempts

**HealthOS currently has:**
- Single `User` model with a `role` string field
- JWT auth with basic token flow
- No permission decorators or granular access control
- Frontend pages not gated by role

### 2. EHR Clinical Models (HIGH PRIORITY)

**InhealthUSA has fully normalized models, HealthOS stores most as JSONB blobs:**

| Clinical Entity | InhealthUSA | HealthOS |
|---|---|---|
| **Diagnosis** | Full model: ICD-10/ICD-11 codes, type (Primary/Secondary/Admitting/Discharge), status, diagnosed_by FK | Stored as `conditions: JSONB[]` on Patient |
| **Prescription** | Full model: medication, dosage, frequency, route, refills, quantity, status, provider FK, encounter FK | Stored as `medications: JSONB[]` on Patient |
| **Allergy** | Full model: allergen, type, severity, reaction, onset_date, is_active | **Missing entirely** |
| **Medical History** | Full model: condition, diagnosis_date, resolution_date, status, treatment_notes | **Missing entirely** |
| **Social History** | Full model: smoking, alcohol, drug use, occupation, marital status, living situation, exercise, diet | **Missing entirely** |
| **Family History** | Full model: relationship, condition, age_at_diagnosis, is_alive, cause_of_death | **Missing entirely** |
| **Lab Tests** | Full model: test_name, code, ordered/collected/result dates, value, unit, reference_range, abnormal_flag | **Missing entirely** (frontend has a `/labs` page but no backend model) |
| **Vital Signs** | Normalized model with BP sys/dia, HR, temp (with units), resp rate, O2 sat, weight (with units), height, BMI, glucose, encounter FK, recorded_by FK | Simplified `Vital` with `value: JSONB`, `vital_type: String` |
| **Hospital** | Full model: name, address, city, state, zip, phone, email, website | **Missing** |
| **Department** | Full model: name, hospital FK, location, phone, head_of_department | **Missing** |
| **Provider (Doctor)** | Full model: specialty (13 choices), NPI, license_number, hospital FK, department FK | Users have `role` field only |
| **Nurse** | Full model: specialty (9 choices), license_number, hospital FK, department FK | **Missing** |
| **Office Administrator** | Full model: position, employee_id, hospital FK | **Missing** |

### 3. IoT Device API & Data Ingestion (HIGH PRIORITY)

**InhealthUSA has a complete REST API for IoT devices:**

- **Device API Key authentication** (`DeviceAPIKey` model with hashed keys, prefix-based lookup, expiration, rate limiting, per-key permissions)
- **Device Data Reading** model (generic JSON data store with reading types: vital_signs, glucose, ECG, activity, sleep)
- **Device Activity Log** (full audit trail: IP, user-agent, endpoint, method, status code, response time)
- **Device Alert Rules** (configurable threshold-based alerts per device/patient with conditions: gt, lt, eq, gte, lte)
- **REST API endpoints:**
  - `POST /api/v1/device/auth` — device authentication
  - `GET /api/v1/device/info` — device info
  - `PUT /api/v1/device/status` — update device status
  - `POST /api/v1/device/vitals` — submit vital signs
  - `POST /api/v1/device/vitals/bulk` — bulk submit (up to 100 readings)
  - `POST /api/v1/device/glucose` — blood glucose data
- **Serializers with medical validation:**
  - `VitalSignsDataSerializer` — validates BP (50-300/30-200), HR (20-300), temp (90-110°F), resp (5-60), O2 (50-100), validates both BP values provided together
  - `BulkVitalSignsSerializer` — validates chronological order, max 100 readings
  - `GlucoseDataSerializer` — glucose (0-600 mg/dL), meal context
  - `ECGDataSerializer` — duration, sample rate, voltage array, rhythm
  - `ActivityDataSerializer` — steps, distance, calories, active minutes, floors
  - `SleepDataSerializer` — sleep phases (deep/light/REM/awake), quality score
- **IoT Data Processor** (`iot_data_processor.py`) for processing raw readings into clinical records

**HealthOS currently has:**
- `Vital` model with generic `device_id: String` field
- Frontend RPM page but no real device API
- No device authentication, no device management, no bulk ingestion

### 4. Billing & Insurance (MEDIUM PRIORITY)

**InhealthUSA has:**
- `Billing` model: invoice_number, amounts (total, paid, due), status tracking
- `BillingItem` model: service codes, line items with auto-calculated totals
- `Payment` model: payment methods, transaction IDs, status
- `InsuranceInformation` model: policy details, copay, deductible, primary/secondary
- Role-based billing views (admin can create/edit, patients can view)

**HealthOS has:**
- `BillingClaim` model (SQLAlchemy) — more claims-focused but no invoice/payment tracking
- `InsuranceVerification` model — verification-focused but no policy management
- Frontend `/rcm` page with demo data

### 5. Messaging & Notifications (MEDIUM PRIORITY)

**InhealthUSA has:**
- `Message` model: sender/recipient FKs, subject, body, read status, threading (parent_message)
- `Notification` model: typed notifications (appointment, lab_result, prescription, message, alert, system)
- `NotificationPreferences` model: per-channel (email/SMS/WhatsApp) per-severity preferences, quiet hours, digest mode
- `VitalSignAlertResponse` model: two-stage alert system (ask patient → escalate to provider)
- Role-specific inboxes (patient inbox, doctor inbox)
- Twilio integration for SMS/WhatsApp

**HealthOS has:**
- Frontend `/messaging` page with demo data
- Frontend `/alerts` page with demo data
- `Alert` model in SQLAlchemy but no messaging model

### 6. Enterprise Authentication (MEDIUM PRIORITY)

**InhealthUSA has:**
- `AuthenticationConfig` model supporting: Local, LDAP, OAuth2, OpenID Connect, Azure AD, CAC, SAML, SSO
- CAC middleware (`cac_middleware.py`) for military/government PKI authentication
- Session security middleware (idle timeout, concurrent session control)
- MFA via TOTP with backup codes
- Email verification flow
- Account lockout mechanism
- Auth backends (`auth_backends.py`) and adapters (`auth_adapters.py`)
- Password validators (`password_validators.py`)

**HealthOS has:**
- JWT-based auth with Keycloak config (but not implemented)
- `mfa_enabled` / `mfa_secret` fields on User model but no implementation

### 7. AI Treatment Plans (LOW PRIORITY — HealthOS already has advanced AI)

**InhealthUSA has:**
- `AIProposedTreatmentPlan` model: AI-generated plans with doctor review workflow
- `DoctorTreatmentPlan` model: doctor-created plans, patient visibility controls
- Treatment plan detail/list views with role-based access

**HealthOS has:**
- More advanced AI agent system (orchestrator, multiple specialized agents)
- Clinical decision support module
- But lacks the structured treatment plan model with approval workflow

---

## Implementation Plan

### Phase 1: RBAC & Role-Specific Access Control
**Files to create/modify:**

1. **Create `healthos_platform/rbac/` package:**
   - `models.py` — Add to SQLAlchemy models: `ProviderProfile`, `NurseProfile`, `OfficeAdminProfile` with specialty, NPI, license, hospital/department FKs
   - `permissions.py` — FastAPI dependency-based permission system: `require_role()`, `require_patient_access()`, `require_provider_access()`, `require_vital_edit()`
   - `middleware.py` — Role injection middleware, account lockout check

2. **Enhance `User` model:**
   - Add: `failed_login_attempts`, `account_locked_until`, `last_password_change`, `email_verified`, `auth_provider`, `external_id`

3. **Create role-specific API routes:**
   - `/api/v1/admin/dashboard` — system stats for admin
   - `/api/v1/provider/dashboard` — provider-specific data
   - `/api/v1/nurse/dashboard` — nurse-specific workflows
   - `/api/v1/office-admin/dashboard` — admin management functions

4. **Frontend: Role-based routing/gating in layout.tsx**

### Phase 2: EHR Clinical Models
**Migrate InhealthUSA's normalized models to SQLAlchemy:**

1. **Create models (in `healthos_platform/models.py`):**
   - `Hospital` — org hierarchy
   - `Department` — hospital departments
   - `ProviderProfile` — doctor details (specialty, NPI, license)
   - `NurseProfile` — nurse details
   - `Diagnosis` — ICD-10/11, type, status, diagnosed_by
   - `Prescription` — medication, dosage, frequency, route, refills, provider FK
   - `Allergy` — allergen, type, severity, reaction
   - `MedicalHistory` — condition, dates, status, treatment notes
   - `SocialHistory` — smoking, alcohol, occupation, marital status, etc.
   - `FamilyHistory` — relationship, condition, age at diagnosis
   - `LabTest` — test details, results, reference ranges, abnormal flags

2. **Create Alembic migration** for all new tables

3. **Create API endpoints:**
   - Full CRUD for each clinical model
   - Filtered by org_id (multi-tenant)
   - Permission-gated by role

4. **Wire up existing frontend pages:**
   - `/labs` → real LabTest API
   - `/patients/[id]` → real clinical data tabs (allergies, history, prescriptions, etc.)

### Phase 3: IoT Device API & Data Ingestion
**Port InhealthUSA's IoT system to FastAPI:**

1. **Create models:**
   - `Device` — device_unique_id, type, manufacturer, model, firmware, status, battery, patient FK
   - `DeviceAPIKey` — hashed key, prefix, permissions (can_write_vitals, can_read_patient), rate limiting, expiration
   - `DeviceDataReading` — generic readings (vital_signs, glucose, ECG, activity, sleep), processing status
   - `DeviceActivityLog` — full audit (IP, user-agent, endpoint, method, status_code, response_time_ms)
   - `DeviceAlertRule` — configurable threshold alerts per device/patient

2. **Create IoT API routes (`/api/v1/device/`):**
   - `POST /auth` — device API key authentication
   - `GET /info` — device information
   - `PUT /status` — device status update
   - `POST /vitals` — single vital signs submission with medical validation
   - `POST /vitals/bulk` — bulk submission (up to 100 readings, chronological validation)
   - `POST /glucose` — blood glucose with meal context
   - `POST /ecg` — ECG waveform data
   - `POST /activity` — activity/steps data
   - `POST /sleep` — sleep phase data

3. **Create Pydantic schemas** (ported from InhealthUSA serializers) with medical range validation

4. **Create IoT data processor** — converts raw device readings into clinical Vital records

5. **Wire to frontend `/rpm` page** with real device data

### Phase 4: Messaging, Notifications & Alert System

1. **Create models:**
   - `Message` — threaded messaging between users
   - `Notification` — typed notifications with read status
   - `NotificationPreference` — per-channel, per-severity preferences
   - `VitalSignAlertResponse` — two-stage alert (patient response → provider escalation)

2. **Create API routes:**
   - `/api/v1/messages/` — inbox, sent, compose, thread
   - `/api/v1/notifications/` — list, mark read, preferences
   - `/api/v1/alerts/respond/<token>` — patient alert response

3. **Wire to frontend `/messaging` and `/alerts` pages**

### Phase 5: Billing & Insurance Enhancement

1. **Create models:**
   - `Billing` — invoices with line items
   - `BillingItem` — service codes, quantities, auto-calculated totals
   - `Payment` — payment tracking with methods and transaction IDs
   - Enhance existing `InsuranceVerification` → full `InsuranceInformation` with policy details

2. **Create API routes with role-based access:**
   - Admin: full CRUD on billing, payments, insurance
   - Provider: view billing, create billing items
   - Patient: view own billing and payment history

3. **Wire to frontend `/rcm` page**

### Phase 6: Enterprise Auth Enhancements

1. **Create `AuthenticationConfig` model** — configurable auth methods
2. **Add session security middleware** — idle timeout, concurrent session control
3. **Implement MFA flow** — TOTP setup, verification, backup codes
4. **Add email verification** — token-based email verification
5. **Add password validation** — strength requirements, history tracking

---

## Priority Order

| Phase | Priority | Effort | Impact |
|---|---|---|---|
| Phase 1: RBAC | 🔴 Critical | Large | Foundational — everything else depends on roles |
| Phase 2: EHR Models | 🔴 Critical | Large | Core clinical value — replaces JSONB blobs with real schema |
| Phase 3: IoT Device API | 🔴 Critical | Medium | Differentiator — production IoT ingestion pipeline |
| Phase 4: Messaging/Alerts | 🟡 High | Medium | User engagement — real messaging replaces demo data |
| Phase 5: Billing/Insurance | 🟡 High | Medium | Revenue cycle — enhances existing billing models |
| Phase 6: Enterprise Auth | 🟢 Medium | Small | Enterprise readiness — CAC, SAML, LDAP, SSO |

---

## What NOT to Import (HealthOS Already Has Better)

- **AI/ML agents** — HealthOS has a full orchestrator, specialized agents (clinical, research, genomics), agent audit logging
- **Frontend UI** — HealthOS's Next.js frontend is far more advanced than InhealthUSA's Django templates
- **Multi-tenancy** — HealthOS has org-level multi-tenancy; InhealthUSA is single-tenant
- **FHIR/HL7 interoperability** — HealthOS already has FHIR connector, HL7v2 connector, EHR sync service
- **Population analytics** — HealthOS has Cohort, PopulationMetric models
- **Workflow engine** — HealthOS has WorkflowTask, OperationalWorkflow
- **Prior authorization** — HealthOS already has PriorAuthorization model
- **Referrals** — HealthOS already has Referral model
