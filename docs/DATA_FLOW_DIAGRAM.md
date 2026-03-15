# Eminence HealthOS — Data Flow Diagrams

**Version:** 0.1.0
**Audience:** Engineering Team, Solution Architects, Compliance Officers

---

## Table of Contents

1. [System Context (Level 0)](#1-system-context-level-0)
2. [Platform Data Flow (Level 1)](#2-platform-data-flow-level-1)
3. [RPM Vitals Pipeline](#3-rpm-vitals-pipeline)
4. [Telehealth Session Flow](#4-telehealth-session-flow)
5. [Agent Orchestration Flow](#5-agent-orchestration-flow)
6. [Alert Generation & Routing](#6-alert-generation--routing)
7. [FHIR Integration Flow](#7-fhir-integration-flow)
8. [Authentication & Authorization Flow](#8-authentication--authorization-flow)
9. [Analytics Pipeline](#9-analytics-pipeline)
10. [PHI Data Protection Flow](#10-phi-data-protection-flow)
11. [Event Streaming Architecture](#11-event-streaming-architecture)

---

## 1. System Context (Level 0)

High-level view of HealthOS and its external interactions.

```
                    ┌──────────────┐
                    │  Clinicians  │
                    │  & Care Team │
                    └──────┬───────┘
                           │ Browser / Mobile
                           │
    ┌──────────┐    ┌──────▼───────┐    ┌──────────────┐
    │ Patients │───→│              │←──→│ External EHR │
    │ & Devices│    │  EMINENCE    │    │ Systems      │
    └──────────┘    │  HEALTHOS    │    └──────────────┘
                    │              │
    ┌──────────┐    │  Platform    │    ┌──────────────┐
    │ Wearables│───→│              │←──→│ Pharmacies   │
    │ & IoT    │    │              │    └──────────────┘
    └──────────┘    │              │
                    │              │    ┌──────────────┐
    ┌──────────┐    │              │←──→│ Laboratories │
    │ Payers / │←──→│              │    └──────────────┘
    │ Insurance│    └──────────────┘
    └──────────┘
```

### External Data Sources

| Source | Protocol | Data Type | Direction |
|--------|----------|----------|-----------|
| Wearables & IoT Devices | REST/MQTT/BLE | Vitals (HR, BP, SpO2, glucose, temp) | Inbound |
| External EHR Systems | FHIR R4 / HL7 | Patient records, encounters, medications | Bidirectional |
| Pharmacies | NCPDP / FHIR | Prescriptions, dispensing data | Bidirectional |
| Laboratories | HL7 / FHIR | Lab orders, results | Bidirectional |
| Payers / Insurance | X12 / FHIR | Eligibility, claims, prior auth | Bidirectional |
| Patients | HTTPS (Portal/App) | Self-reported data, questionnaires | Inbound |
| Clinicians | HTTPS (Dashboard) | Clinical decisions, orders, notes | Bidirectional |

---

## 2. Platform Data Flow (Level 1)

Internal data flow between HealthOS subsystems.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EMINENCE HEALTHOS                                  │
│                                                                              │
│  ┌──────────┐    ┌────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │ Ingestion│───→│ Event Bus  │───→│    Agent     │───→│   Action       │  │
│  │ Layer    │    │ (Kafka)    │    │ Orchestration│    │   Layer        │  │
│  │          │    │            │    │              │    │                │  │
│  │ • REST   │    │ Topics:    │    │ • Classify   │    │ • Alerts       │  │
│  │ • FHIR   │    │ • vitals   │    │ • Route      │    │ • Notifications│  │
│  │ • IoT    │    │ • alerts   │    │ • Execute    │    │ • Orders       │  │
│  │ • WS     │    │ • agents   │    │ • Audit      │    │ • Notes        │  │
│  └──────────┘    └────────────┘    └──────────────┘    └────────────────┘  │
│       │                                   │                    │            │
│       ▼                                   ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        DATA LAYER                                    │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌───────┐  ┌────────┐  ┌───────┐  ┌───────┐        │   │
│  │  │PostgreSQL│  │ Redis │  │ Qdrant │  │ Neo4j │  │ MinIO │        │   │
│  │  │(pgvector)│  │       │  │        │  │       │  │ (S3)  │        │   │
│  │  │          │  │       │  │        │  │       │  │       │        │   │
│  │  │• Patients│  │• Cache│  │• Embeds│  │• Drug │  │• DICOM│        │   │
│  │  │• Vitals  │  │• Sess.│  │• RAG   │  │• Care │  │• Docs │        │   │
│  │  │• Enc.    │  │• RT   │  │• Search│  │• Path │  │• Audit│        │   │
│  │  │• Meds    │  │• Pub/ │  │        │  │• Onto │  │• Model│        │   │
│  │  │• Labs    │  │  Sub  │  │        │  │       │  │       │        │   │
│  │  └──────────┘  └───────┘  └────────┘  └───────┘  └───────┘        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PRESENTATION LAYER                                │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐           │   │
│  │  │ Clinician    │  │ Patient       │  │ Admin          │           │   │
│  │  │ Dashboard    │  │ Portal        │  │ Console        │           │   │
│  │  │ (Next.js)    │  │ (Web/Mobile)  │  │ (React)        │           │   │
│  │  └──────────────┘  └───────────────┘  └────────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. RPM Vitals Pipeline

End-to-end flow from device reading to clinician alert.

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌───────────────┐
│ Wearable │────→│ API      │────→│ Device       │────→│ Vitals        │
│ / Device │     │ Endpoint │     │ Ingestion    │     │ Normalization │
│          │ BLE │ /api/v1/ │REST │ Agent        │     │ Agent         │
│          │WiFi │ rpm/     │     │              │     │               │
└──────────┘     │ vitals   │     │ • Validate   │     │ • Standardize │
                 └──────────┘     │ • Deduplicate│     │ • Unit convert│
                                  │ • Timestamp  │     │ • Schema map  │
                                  └──────┬───────┘     └───────┬───────┘
                                         │                     │
                                    ┌────▼─────────────────────▼────┐
                                    │         Kafka                  │
                                    │    Topic: vitals.ingested      │
                                    └────┬──────────────────────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          │              │              │
                    ┌─────▼─────┐  ┌────▼─────┐  ┌────▼──────┐
                    │ Anomaly   │  │ Trend    │  │ Adherence │
                    │ Detection │  │ Analysis │  │ Monitor   │
                    │ Agent     │  │ Agent    │  │ Agent     │
                    │           │  │          │  │           │
                    │ • Thresh. │  │ • 7/30/  │  │ • Missed  │
                    │ • Pattern │  │   90 day │  │   readings│
                    │ • Multi-  │  │ • Slope  │  │ • Pattern │
                    │   vital   │  │ • Predict│  │   changes │
                    └─────┬─────┘  └────┬─────┘  └─────┬─────┘
                          │             │              │
                    ┌─────▼─────────────▼──────────────▼─────┐
                    │              Risk Scoring Agent          │
                    │                                          │
                    │  • Combine anomaly + trend + adherence   │
                    │  • Generate composite risk score (0-100) │
                    │  • Factor in comorbidities & history     │
                    └────────────────┬─────────────────────────┘
                                     │
                              ┌──────▼──────┐
                              │ Policy/     │
                              │ Rules Agent │
                              │             │
                              │ • Check     │
                              │   escalation│
                              │   rules     │
                              │ • Apply     │
                              │   org policy│
                              └──────┬──────┘
                                     │
                         ┌───────────┼──────────┐
                         │           │          │
                   ┌─────▼────┐ ┌───▼────┐ ┌───▼──────┐
                   │ Generate │ │ Store  │ │ Notify   │
                   │ Alert    │ │ in DB  │ │ Clinician│
                   │          │ │        │ │          │
                   │ Kafka:   │ │Postgres│ │ WebSocket│
                   │ alerts.  │ │ alerts │ │ Email    │
                   │ generated│ │ table  │ │ SMS      │
                   └──────────┘ └────────┘ └──────────┘
```

### Data Transformation

| Stage | Input | Output | Storage |
|-------|-------|--------|---------|
| Device → API | Raw device payload (vendor-specific) | Validated reading | — |
| Ingestion Agent | Validated reading | Timestamped, deduplicated record | Kafka |
| Normalization Agent | Raw vitals | Standardized schema (units, ranges) | PostgreSQL |
| Anomaly Detection | Normalized vitals + history | Anomaly flags + confidence | Redis (cache) |
| Risk Scoring | Anomalies + trends + adherence | Risk score (0–100) | PostgreSQL |
| Alert Generation | Risk score + policy rules | Clinical alert | PostgreSQL, Kafka |

---

## 4. Telehealth Session Flow

```
┌───────────┐                              ┌───────────┐
│ Clinician │                              │ Patient   │
└─────┬─────┘                              └─────┬─────┘
      │                                          │
      │  1. Open scheduled visit                 │
      ▼                                          │
┌─────────────┐                                  │
│ Visit Prep  │  • Fetch patient record          │
│ Agent       │  • Recent vitals summary         │
│             │  • Active concerns               │
│             │  • Medication review              │
└──────┬──────┘                                  │
       │                                          │
       ▼                                          │
┌─────────────┐    Daily.co / WebRTC    ┌────────▼───────┐
│ Video       │◄───────────────────────→│ Video          │
│ Session     │                         │ Session        │
│ (Clinician) │                         │ (Patient)      │
└──────┬──────┘                         └────────────────┘
       │
       │  2. During visit
       ▼
┌─────────────┐
│ Ambient AI  │  • Real-time transcription
│ Module      │  • Extract clinical entities
│             │  • Draft SOAP note
└──────┬──────┘
       │
       │  3. Post-visit
       ▼
┌─────────────┐    ┌──────────────┐    ┌───────────────┐
│ Clinical    │───→│ Follow-Up    │───→│ Task          │
│ Note Agent  │    │ Plan Agent   │    │ Orchestration │
│             │    │              │    │ Agent         │
│ • SOAP note │    │ • Care plan  │    │ • Schedule    │
│ • ICD codes │    │ • Monitoring │    │   follow-up   │
│ • CPT codes │    │   cadence    │    │ • Order labs  │
│             │    │ • Education  │    │ • Referrals   │
└─────────────┘    └──────────────┘    └───────────────┘
       │
       ▼
┌─────────────┐
│ Billing     │  • Encounter documentation
│ Readiness   │  • CPT code validation
│ Agent       │  • Claims preparation
└─────────────┘
```

---

## 5. Agent Orchestration Flow

```
                    ┌─────────────────┐
                    │  EVENT SOURCE   │
                    │                  │
                    │ • API Request    │
                    │ • Kafka Event    │
                    │ • Scheduled Task │
                    │ • Manual Trigger │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    MASTER       │
                    │  ORCHESTRATOR   │
                    │                  │
                    │ 1. Parse event   │
                    │ 2. Classify type │
                    │ 3. Build agent   │
                    │    execution     │
                    │    graph (DAG)   │
                    │ 4. Resolve deps  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ CONTEXT ASSEMBLY│
                    │                  │
                    │ • Patient data   │
                    │ • History        │
                    │ • Active plans   │
                    │ • Medications    │
                    │ • Prior results  │
                    │ • Org policies   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  AGENT GRAPH    │
                    │  EXECUTION      │
                    │                  │
                    │  A1 ──→ A2      │
                    │   │      │      │
                    │   ▼      ▼      │
                    │  A3 ──→ A4      │
                    │          │      │
                    │          ▼      │
                    │         A5      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────┐ ┌──────▼──────┐
     │ QUALITY CHECK  │ │ HITL   │ │ AUDIT LOG   │
     │                │ │ GATE   │ │             │
     │ • Confidence   │ │        │ │ • Who       │
     │   score        │ │ • Low  │ │ • What      │
     │ • Completeness │ │   conf?│ │ • When      │
     │ • Consistency  │ │ • Gov. │ │ • Why       │
     │                │ │   rule?│ │ • Inputs    │
     │                │ │ • Route│ │ • Outputs   │
     │                │ │   to   │ │ • Decisions │
     │                │ │   human│ │             │
     └────────────────┘ └────────┘ └─────────────┘
```

---

## 6. Alert Generation & Routing

```
┌──────────────────┐    ┌──────────────────┐
│ Anomaly Detection│    │ Medication       │
│ Agent            │    │ Review Agent     │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │ ALERT       │
              │ GENERATOR   │
              │             │
              │ Severity:   │
              │ • Critical  │
              │ • High      │
              │ • Medium    │
              │ • Low       │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │ ESCALATION  │
              │ ROUTING     │
              │ AGENT       │
              └──────┬──────┘
                     │
        ┌────────────┼────────────┬─────────────┐
        │            │            │             │
  ┌─────▼─────┐ ┌───▼─────┐ ┌───▼──────┐ ┌───▼──────┐
  │ On-Call   │ │ Care    │ │ Nurse    │ │ Admin    │
  │ Clinician │ │ Manager │ │ Station  │ │ Team     │
  │           │ │         │ │          │ │          │
  │ Critical  │ │ Adherence│ │ High    │ │ System   │
  │ Vitals    │ │ Concerns│ │ Vitals  │ │ Issues   │
  └───────────┘ └─────────┘ └──────────┘ └──────────┘

Notification Channels:
  • In-App (WebSocket push)
  • Email (SMTP)
  • SMS (Twilio/equivalent)
  • Pager (for critical alerts)
```

---

## 7. FHIR Integration Flow

```
┌─────────────┐                         ┌─────────────┐
│ External    │                         │ HealthOS    │
│ EHR System  │                         │ FHIR Server │
└──────┬──────┘                         └──────┬──────┘
       │                                       │
       │  1. FHIR R4 Request                   │
       │  GET /Patient?name=Smith              │
       │──────────────────────────────────────→│
       │                                       │
       │  2. Response: FHIR Bundle             │
       │←──────────────────────────────────────│
       │                                       │
       │  3. Create/Update Patient             │
       │  POST /Patient (FHIR Resource)        │
       │──────────────────────────────────────→│
       │                                       │
       │                              ┌────────▼────────┐
       │                              │ FHIR Mapping    │
       │                              │ Engine          │
       │                              │                  │
       │                              │ FHIR Resource   │
       │                              │    ↕             │
       │                              │ Internal Model  │
       │                              └────────┬────────┘
       │                                       │
       │                              ┌────────▼────────┐
       │                              │ Data Store      │
       │                              │ (PostgreSQL)    │
       │                              └─────────────────┘


Supported FHIR Operations:
  • Patient      — CRUD, $match, $everything
  • Observation  — CRUD, search by patient/date/code
  • Encounter    — CRUD, search
  • MedicationRequest — CRUD
  • DiagnosticReport — CRUD
  • AllergyIntolerance — CRUD
  • CarePlan     — CRUD
  • Bundle       — Transaction bundles
```

---

## 8. Authentication & Authorization Flow

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Client   │────→│ Keycloak │────→│ JWT Token    │────→│ HealthOS │
│ (Browser)│     │ (IdP)    │     │ Issued       │     │ API      │
└──────────┘     └──────────┘     └──────────────┘     └─────┬────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │ Auth Middleware  │
                                                    │                  │
                                                    │ 1. Validate JWT  │
                                                    │ 2. Extract user  │
                                                    │ 3. Resolve tenant│
                                                    │ 4. Check RBAC    │
                                                    │ 5. Set context   │
                                                    └────────┬────────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │ RBAC Engine     │
                                                    │                  │
                                                    │ Role → Perms    │
                                                    │                  │
                                                    │ Super Admin: *   │
                                                    │ Admin: manage    │
                                                    │ Physician: rw    │
                                                    │ Nurse: rw (lim)  │
                                                    │ Care Mgr: coord  │
                                                    │ Read-Only: r     │
                                                    └────────┬────────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │ Route Handler   │
                                                    │ (authorized)    │
                                                    └─────────────────┘
```

---

## 9. Analytics Pipeline

```
┌───────────────────────────────────────────────────────────┐
│                   DATA SOURCES                             │
│                                                            │
│  Vitals │ Encounters │ Labs │ Meds │ Claims │ Outcomes    │
└────────────────────────┬──────────────────────────────────┘
                         │
                ┌────────▼────────┐
                │ Feature Store   │
                │                  │
                │ • Patient feats  │
                │ • Temporal feats  │
                │ • Aggregate feats │
                └────────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────▼─────┐  ┌────▼─────┐  ┌────▼──────────┐
    │ Cohort    │  │Readmit   │  │ Population    │
    │ Segment.  │  │Risk      │  │ Health Agent  │
    │ Agent     │  │Agent     │  │               │
    │           │  │          │  │ • Care gaps   │
    │ • Chronic │  │ • 30-day │  │ • High-risk   │
    │ • Risk    │  │   prob.  │  │   groups      │
    │ • Demo    │  │ • Factor │  │ • Outreach    │
    │           │  │   weights│  │   targets     │
    └─────┬─────┘  └────┬─────┘  └────┬──────────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
              ┌──────────▼──────────┐
              │ Executive Insight   │
              │ Agent               │
              │                      │
              │ • KPI dashboards    │
              │ • Trend reports     │
              │ • Cost analysis     │
              │ • Quality metrics   │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ Analytics Dashboard │
              │ (Next.js + Recharts)│
              └─────────────────────┘
```

---

## 10. PHI Data Protection Flow

```
┌──────────┐
│ Incoming │
│ Data     │
└────┬─────┘
     │
┌────▼──────────┐
│ INPUT         │
│ SANITIZER     │
│               │
│ • XSS filter  │
│ • SQL inj.    │
│ • Cmd inj.    │
└────┬──────────┘
     │
┌────▼──────────┐     ┌───────────────────┐
│ PHI           │────→│ PHI CLASSIFICATION│
│ DETECTOR      │     │                    │
│               │     │ Level 1: Public    │
│ • Name/DOB    │     │ Level 2: Internal  │
│ • SSN/MRN     │     │ Level 3: Confid.   │
│ • Address     │     │ Level 4: PHI       │
│ • Phone/Email │     │ Level 5: Restr.PHI │
│ • Medical IDs │     └───────────────────┘
└────┬──────────┘
     │
┌────▼──────────┐
│ ENCRYPTION    │
│ ENGINE        │
│               │
│ • AES-256-GCM │
│ • Per-field    │
│ • Key rotation │
└────┬──────────┘
     │
┌────▼──────────┐
│ STORAGE       │
│ (PostgreSQL)  │
│               │
│ • Encrypted   │
│   at rest     │
│ • Row-level   │
│   security    │
│ • Tenant      │
│   isolation   │
└────┬──────────┘
     │
┌────▼──────────┐
│ ACCESS        │
│ CONTROL       │
│               │
│ • RBAC check  │
│ • Audit log   │
│ • PHI masking │
│   in logs     │
│ • Decrypt for │
│   authorized  │
│   users only  │
└───────────────┘
```

---

## 11. Event Streaming Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KAFKA CLUSTER (KRaft)                          │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ vitals.ingested │  │ alerts.generated │  │ agent.events   │  │
│  │                  │  │                   │  │                │  │
│  │ Producers:      │  │ Producers:        │  │ Producers:     │  │
│  │ • Ingestion Agt │  │ • Anomaly Det.   │  │ • All agents   │  │
│  │ • Normalization │  │ • Risk Scoring   │  │                │  │
│  │                  │  │ • Med Review     │  │ Consumers:     │  │
│  │ Consumers:      │  │                   │  │ • Audit Agent  │  │
│  │ • Anomaly Det.  │  │ Consumers:        │  │ • Metrics      │  │
│  │ • Trend Analysis│  │ • Alert Router   │  │ • Orchestrator │  │
│  │ • Adherence Mon.│  │ • Dashboard (WS) │  │ • Dashboard    │  │
│  │ • PostgreSQL    │  │ • Notification   │  │                │  │
│  └─────────────────┘  └──────────────────┘  └────────────────┘  │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ patient.updated  │  │ workflow.events  │                     │
│  │                   │  │                   │                     │
│  │ Producers:       │  │ Producers:        │                     │
│  │ • CRUD ops       │  │ • Temporal wkflw  │                     │
│  │ • FHIR imports   │  │ • Prior auth      │                     │
│  │                   │  │ • Referrals       │                     │
│  │ Consumers:       │  │                   │                     │
│  │ • Cache inval.   │  │ Consumers:        │                     │
│  │ • Notification   │  │ • Dashboard       │                     │
│  │ • Analytics      │  │ • Analytics       │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                   │
│  Consumer Group: healthos-agents                                  │
│  Partitioning: by patient_id (co-located processing)             │
│  Retention: 7 days (configurable)                                │
└─────────────────────────────────────────────────────────────────┘
```

---

*Eminence HealthOS v0.1.0 — Eminence Tech Solutions*
*See also: [Architecture Guide](ARCHITECTURE_GUIDE.md) | [API Endpoints](API_ENDPOINTS.md)*
