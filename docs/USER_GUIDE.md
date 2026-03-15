# Eminence HealthOS — User Guide

**Version:** 0.1.0
**Product:** Eminence HealthOS — The AI Operating System for Digital Healthcare Platforms
**Audience:** Clinicians, Care Managers, Administrators, Platform Operators

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Clinician Dashboard](#3-clinician-dashboard)
4. [Patient Management](#4-patient-management)
5. [Remote Patient Monitoring (RPM)](#5-remote-patient-monitoring-rpm)
6. [Telehealth](#6-telehealth)
7. [Clinical Decision Support](#7-clinical-decision-support)
8. [Alerts & Notifications](#8-alerts--notifications)
9. [Care Coordination & Operations](#9-care-coordination--operations)
10. [Analytics & Reporting](#10-analytics--reporting)
11. [Pharmacy & Medications](#11-pharmacy--medications)
12. [Lab Results](#12-lab-results)
13. [Medical Imaging](#13-medical-imaging)
14. [Mental Health Module](#14-mental-health-module)
15. [Patient Engagement](#15-patient-engagement)
16. [Compliance & Audit](#16-compliance--audit)
17. [Administration](#17-administration)
18. [Troubleshooting](#18-troubleshooting)
19. [Glossary](#19-glossary)

---

## 1. Introduction

### What Is Eminence HealthOS?

Eminence HealthOS is a unified AI-powered healthcare platform that brings together Remote Patient Monitoring (RPM), Telehealth, Operations Automation, and Population Health Analytics into a single operating system. It uses 30+ specialized AI agents to orchestrate clinical workflows, detect anomalies, generate insights, and automate routine tasks — so clinicians can focus on patient care.

### Key Capabilities

| Capability | Description |
|-----------|-------------|
| **Remote Patient Monitoring** | Continuous vitals ingestion from wearables and home devices with AI-driven anomaly detection |
| **Telehealth** | Virtual consultations with automated note generation, scheduling, and follow-up |
| **AI Clinical Decision Support** | Risk scoring, trend analysis, medication review, and evidence-based recommendations |
| **Care Coordination** | Automated scheduling, referrals, prior authorizations, and task management |
| **Population Health Analytics** | Cohort segmentation, readmission risk prediction, and executive dashboards |
| **Compliance & Security** | HIPAA-compliant, zero-trust architecture with full audit trails |

### Who Should Use This Guide?

- **Clinicians / Providers** — Sections 3–8, 11–14
- **Care Managers** — Sections 4, 5, 8, 9, 15
- **Administrators** — Sections 16, 17
- **Platform Operators** — Sections 2, 17, 18

---

## 2. Getting Started

### System Requirements

| Component | Requirement |
|-----------|------------|
| **Browser** | Chrome 90+, Firefox 90+, Safari 15+, Edge 90+ |
| **Screen** | Minimum 1280×720, recommended 1920×1080+ |
| **Network** | Broadband internet; WebSocket support for real-time data |
| **Camera/Mic** | Required for telehealth video consultations |

### Logging In

1. Navigate to your organization's HealthOS URL (e.g., `https://your-org.healthos.io`)
2. Enter your credentials (username / email and password)
3. Complete multi-factor authentication (MFA) if enabled by your organization
4. You will be directed to your role-specific dashboard

### First-Time Setup

Upon first login, complete these steps:

1. **Review your profile** — Verify your name, role, credentials, and contact information
2. **Set notification preferences** — Configure how you want to receive alerts (in-app, email, SMS)
3. **Review assigned patients** — If you are a clinician, check your assigned patient panel
4. **Tour the dashboard** — Use the guided tour (click the "?" icon in the top navigation bar)

### Navigation Overview

```
┌─────────────────────────────────────────────────┐
│  Top Bar: Search | Notifications | Profile       │
├──────────┬──────────────────────────────────────┤
│          │                                        │
│  Side    │         Main Content Area              │
│  Nav     │                                        │
│          │  - Dashboard widgets                   │
│  - Home  │  - Patient records                     │
│  - Patients│  - Vitals charts                     │
│  - RPM   │  - Telehealth sessions                 │
│  - Telehealth│  - Reports & analytics             │
│  - Alerts│                                        │
│  - Analytics│                                     │
│  - Schedule│                                      │
│  - Admin │                                        │
│          │                                        │
└──────────┴──────────────────────────────────────┘
```

---

## 3. Clinician Dashboard

The dashboard is your home screen. It provides an at-a-glance summary of your workday.

### Dashboard Widgets

| Widget | Description |
|--------|-------------|
| **Active Alerts** | Unresolved critical, high, and medium alerts requiring attention |
| **Today's Schedule** | Upcoming telehealth visits and in-person appointments |
| **Patient Panel Summary** | Total active patients, risk distribution, and engagement metrics |
| **RPM Vitals Feed** | Real-time vitals streaming from connected patients |
| **Pending Tasks** | Care coordination tasks assigned to you |
| **Recent AI Insights** | Latest AI-generated observations and recommendations |

### Customizing Your Dashboard

1. Click the **gear icon** on the dashboard
2. Drag and drop widgets to rearrange them
3. Toggle widgets on/off based on your workflow preferences
4. Click **Save Layout** to persist your arrangement

---

## 4. Patient Management

### Viewing Patient Records

1. Navigate to **Patients** in the sidebar
2. Use filters to search by name, MRN, condition, risk level, or care team
3. Click a patient row to open their full record

### Patient Record Layout

| Tab | Content |
|-----|---------|
| **Overview** | Demographics, diagnoses, allergies, care team, risk score |
| **Vitals** | Historical vitals charts, trends, and anomaly markers |
| **Encounters** | Visit history — telehealth, in-person, phone, messaging |
| **Medications** | Active prescriptions, adherence tracking, interaction alerts |
| **Labs** | Lab orders and results with trend visualization |
| **Imaging** | Radiology images and AI-assisted reports |
| **Care Plans** | Active care plans, goals, interventions, and progress |
| **Documents** | Clinical notes, consent forms, referral letters |
| **Timeline** | Chronological event history across all clinical data |

### Adding a New Patient

1. Click **+ New Patient** in the patient list
2. Enter required demographics (name, DOB, gender, contact info)
3. Assign a primary provider and care team
4. Add diagnoses, allergies, and medications
5. Enroll in relevant programs (RPM, chronic care management, etc.)
6. Save — the patient is now active in the system

### FHIR Integration

HealthOS uses FHIR R4 for healthcare data interoperability. Patient records can be:
- Imported from external EHR systems via FHIR APIs
- Exported as FHIR bundles for external consumption
- Synchronized in real-time with connected EHR endpoints

---

## 5. Remote Patient Monitoring (RPM)

### Overview

The RPM module enables continuous monitoring of patient vitals from connected wearables and home medical devices. AI agents analyze incoming data in real-time to detect anomalies, identify trends, and trigger alerts.

### Supported Vital Signs

| Vital | Devices | Normal Range (Adult) |
|-------|---------|---------------------|
| Heart Rate | Smartwatches, pulse oximeters | 60–100 bpm |
| Blood Pressure | Bluetooth BP cuffs | <120/80 mmHg |
| Blood Oxygen (SpO2) | Pulse oximeters | 95–100% |
| Blood Glucose | Continuous glucose monitors | 70–140 mg/dL |
| Body Temperature | Smart thermometers | 97.8–99.1°F |
| Weight | Smart scales | Patient-specific |
| Respiratory Rate | Wearable sensors | 12–20 breaths/min |
| Sleep Metrics | Smartwatches, sleep trackers | Patient-specific |

### Monitoring Dashboard

The RPM dashboard shows:
- **Real-time vitals feed** — Live readings as they arrive
- **Patient tiles** — Each patient's current vital status (normal, warning, critical)
- **Trend charts** — Visualize vitals over time (1 day, 7 days, 30 days, 90 days)
- **Anomaly markers** — AI-flagged unusual readings highlighted on charts
- **Adherence tracking** — Which patients are/aren't submitting readings

### Setting Thresholds

1. Navigate to a patient's RPM profile
2. Click **Threshold Settings**
3. Set personalized high/low thresholds for each vital sign
4. Choose escalation behavior: auto-alert, nurse review, or clinician notification
5. Save — the AI agents will use these thresholds in real-time

### AI-Powered Anomaly Detection

HealthOS agents go beyond simple threshold checks:
- **Pattern detection** — Identifies unusual patterns even when within normal range
- **Trend analysis** — Detects gradual worsening over days/weeks
- **Multi-vital correlation** — Correlates changes across multiple vitals (e.g., rising HR + dropping SpO2)
- **Contextual awareness** — Considers patient history, medications, and comorbidities

---

## 6. Telehealth

### Starting a Video Consultation

1. Navigate to **Telehealth** or click a scheduled visit
2. Review the **AI-generated visit summary** — patient history, recent vitals, active concerns
3. Click **Start Video** to launch the telehealth session
4. The session opens in a full-screen video interface with:
   - Video/audio controls
   - Patient summary sidebar
   - Real-time vitals (if RPM-connected)
   - Shared screen capability
   - Chat/messaging

### During the Visit

- **Ambient AI Documentation** — If enabled, the Ambient AI module listens to the conversation and generates clinical notes in real-time
- **Quick Actions** — Order labs, prescribe medications, create referrals from within the visit
- **AI Suggestions** — The system may surface relevant clinical decision support during the visit

### After the Visit

1. **Review AI-generated notes** — Edit and approve the clinical documentation
2. **Create follow-up tasks** — Schedule follow-ups, order tests, adjust care plans
3. **Sign and finalize** — Electronically sign the encounter note
4. The Follow-Up Plan Agent automatically creates monitoring schedules and reminders

### Scheduling Telehealth Visits

1. Navigate to **Schedule**
2. Click **+ New Visit** or use the patient's record to schedule
3. Select visit type (initial, follow-up, urgent)
4. Choose date/time from available slots
5. Add visit reason and any pre-visit instructions
6. The patient receives an automated invitation with join instructions

---

## 7. Clinical Decision Support

### AI-Powered Risk Scoring

Each patient receives continuous risk assessments:

| Score | Description | Action |
|-------|-------------|--------|
| **Low (0–30)** | Stable, routine monitoring | Standard care plan |
| **Medium (31–60)** | Emerging risk patterns | Enhanced monitoring, proactive outreach |
| **High (61–80)** | Significant deterioration risk | Urgent clinician review, care escalation |
| **Critical (81–100)** | Immediate attention required | Automatic alert to care team |

### How Risk Scores Are Calculated

Risk scores combine multiple factors:
- Current vital sign trends and anomalies
- Historical health patterns
- Medication adherence data
- Social determinants of health
- Comorbidity burden
- Recent hospitalizations or ER visits

### Digital Twin

The Digital Twin module creates a virtual representation of each patient, integrating all available health data to:
- Simulate treatment outcomes before implementation
- Predict disease progression trajectories
- Identify optimal intervention timing
- Visualize physiological state in a unified model

---

## 8. Alerts & Notifications

### Alert Severity Levels

| Level | Color | Description | Response Time |
|-------|-------|-------------|---------------|
| **Critical** | Red | Immediate patient safety concern | < 15 minutes |
| **High** | Orange | Significant clinical concern | < 1 hour |
| **Medium** | Yellow | Notable change requiring review | < 4 hours |
| **Low** | Blue | Informational, no immediate action | Next business day |

### Managing Alerts

1. Navigate to **Alerts** in the sidebar
2. View alerts filtered by severity, patient, date, or status
3. Click an alert to see full details, including:
   - The triggering data point
   - AI reasoning (why the alert was generated)
   - Patient context (recent vitals, medications, history)
   - Recommended actions
4. **Acknowledge** — Mark as seen, take action, or dismiss with reason

### Alert Routing

Alerts are intelligently routed by the Escalation Routing Agent:
- Critical vitals alerts → On-call clinician
- Medication interaction alerts → Prescribing provider
- Adherence concerns → Care manager
- Administrative issues → Operations team

### Notification Preferences

Configure in **Profile > Notification Settings**:
- **In-app** — Always on (badge + sound)
- **Email** — Configurable per severity level
- **SMS** — Configurable per severity level (critical/high recommended)
- **Quiet hours** — Suppress non-critical notifications during off hours

---

## 9. Care Coordination & Operations

### Task Management

The Task Orchestration Agent creates and tracks cross-functional work items:

1. Navigate to **Tasks** in the sidebar
2. View tasks assigned to you, your team, or all teams
3. Filter by priority, due date, patient, or task type
4. Update task status: Open → In Progress → Completed

### Scheduling

- **Smart scheduling** — The Scheduling Agent considers provider availability, patient preferences, visit type requirements, and room/resource availability
- **Automated reminders** — Patients receive reminders 24 hours and 1 hour before appointments
- **Rescheduling** — Drag-and-drop rescheduling with automatic patient notification

### Prior Authorization

The Prior Authorization Agent automates insurance authorization workflows:
1. Submits authorization requests with supporting clinical documentation
2. Tracks authorization status in real-time
3. Alerts the care team when authorization is approved, denied, or requires additional information
4. Maintains an audit trail of all authorization interactions

### Referral Management

1. Create referrals from a patient's record
2. The Referral Coordination Agent:
   - Packages relevant clinical records
   - Sends to the receiving provider/facility
   - Tracks referral status (sent, received, scheduled, completed)
   - Reports back on outcomes

---

## 10. Analytics & Reporting

### Population Health Dashboard

| Metric | Description |
|--------|-------------|
| **Risk Distribution** | Breakdown of patient panel by risk level |
| **Care Gap Analysis** | Patients missing screenings, vaccinations, or follow-ups |
| **Readmission Risk** | Patients with elevated 30-day readmission probability |
| **Utilization Trends** | ER visits, hospitalizations, telehealth vs. in-person |
| **Cost Analysis** | Per-patient and per-cohort cost drivers |

### Generating Reports

1. Navigate to **Analytics**
2. Select report type: Clinical, Operational, Financial, or Quality
3. Set date range, patient cohort, and filters
4. Click **Generate** — the AI assembles the report with visualizations
5. Export as PDF, CSV, or share via link

### Executive Insights

The Executive Insight Agent produces automated summaries for leadership:
- Weekly clinical performance summaries
- Monthly operational KPI reports
- Quarterly population health trend analysis
- Ad-hoc deep dives on specific metrics

---

## 11. Pharmacy & Medications

### Medication Management

- View active prescriptions for any patient
- Check drug-drug and drug-allergy interactions (AI-powered)
- Track medication adherence from patient-reported data and pharmacy fills
- Receive alerts for non-adherence patterns

### E-Prescribing

1. Open a patient record → **Medications** tab
2. Click **+ New Prescription**
3. Search for medication, select dosage, frequency, and quantity
4. The system checks for interactions and coverage
5. Submit electronically to the patient's pharmacy

---

## 12. Lab Results

### Viewing Lab Results

1. Navigate to a patient's **Labs** tab
2. View results in table format or trend charts
3. Abnormal values are highlighted automatically
4. AI provides contextual interpretation alongside results

### Ordering Labs

1. Click **+ Order Lab** from a patient's record
2. Search and select lab tests
3. Choose lab facility and urgency
4. Submit — the order is sent electronically

---

## 13. Medical Imaging

### Viewing Images

- Access DICOM images directly within the patient record
- Built-in viewer supports common modalities (X-ray, CT, MRI, Ultrasound)
- AI-assisted findings are overlaid on images when available

### AI-Assisted Radiology

The Imaging module provides:
- Automated preliminary reads for common findings
- Comparison with prior images
- Structured reporting templates
- Priority flagging for critical findings

---

## 14. Mental Health Module

### Behavioral Health Tools

- **PHQ-9 / GAD-7 Assessments** — Standardized screening questionnaires with scoring
- **Mood Tracking** — Patient-reported mood and wellness data over time
- **Treatment Plans** — Specialized mental health care planning templates
- **Crisis Detection** — AI monitoring for concerning patterns in patient data

### Teletherapy

- Conduct virtual therapy sessions via the Telehealth module
- Specialized documentation templates for mental health encounters
- Secure messaging between therapist and patient between sessions

---

## 15. Patient Engagement

### Patient Portal

Patients access their own portal to:
- View upcoming appointments and join telehealth visits
- Submit vitals readings from connected devices
- Complete health questionnaires and assessments
- Message their care team securely
- View lab results and medications
- Access educational content personalized to their conditions

### Automated Outreach

The Patient Communication Agent handles:
- Appointment reminders
- Medication reminders
- Health education content delivery
- Post-visit follow-up messages
- Wellness check-ins
- Survey and feedback collection

---

## 16. Compliance & Audit

### HIPAA Compliance

HealthOS is built for HIPAA compliance:
- **Encryption at rest** — AES-256-GCM for all PHI/PII fields
- **Encryption in transit** — TLS 1.3 for all network communication
- **Access controls** — Role-based access control (RBAC) with 22 granular permissions
- **Audit trails** — Every data access and modification is logged
- **PHI de-identification** — Automated PHI filtering and masking

### Audit Logs

1. Navigate to **Admin > Audit Logs**
2. Search by user, action type, patient, date range
3. Export logs for compliance reporting
4. The Audit/Trace Agent records full decision chains for all AI actions

### Role-Based Access Control (RBAC)

| Role | Access Level |
|------|-------------|
| **Super Admin** | Full platform access, tenant management |
| **Admin** | Organization-level settings, user management |
| **Physician** | Full clinical access to assigned patients |
| **Nurse** | Clinical access with some restrictions |
| **Care Manager** | Care coordination and population health |
| **Read-Only** | View-only access to permitted data |

---

## 17. Administration

### User Management

1. Navigate to **Admin > Users**
2. Add, edit, or deactivate user accounts
3. Assign roles and permissions
4. Configure MFA requirements
5. Set up care teams and provider groups

### Organization Settings

- **General** — Organization name, logo, contact information
- **Security** — Password policies, session timeouts, IP allowlists
- **Integrations** — Configure EHR, pharmacy, lab, and device integrations
- **Notifications** — Organization-wide notification policies
- **Billing** — View platform usage and subscription details

### Multi-Tenant Management

For platform operators managing multiple organizations:
- Each tenant has fully isolated data and configuration
- Tenant-level customization of workflows, branding, and modules
- Cross-tenant analytics available only to platform administrators

---

## 18. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|---------|
| **Cannot log in** | Verify credentials, check MFA device, contact admin for account lockout |
| **Video not working** | Check browser permissions for camera/mic, verify broadband connection |
| **Vitals not syncing** | Verify device Bluetooth/Wi-Fi, check device battery, re-pair if necessary |
| **Missing patient data** | Check FHIR integration status, verify patient consent, contact admin |
| **Slow performance** | Clear browser cache, check network speed, try a different browser |
| **Alert not received** | Review notification settings, check quiet hours configuration |

### Getting Help

- **In-app help** — Click the "?" icon for contextual help articles
- **Support ticket** — Navigate to **Help > Submit a Ticket**
- **Email** — support@eminencetech.com
- **Phone** — Contact your organization's HealthOS administrator

---

## 19. Glossary

| Term | Definition |
|------|-----------|
| **Agent** | An AI component that performs a specific healthcare task autonomously |
| **Anomaly Detection** | AI identification of unusual patterns in patient data |
| **Care Plan** | A structured plan of clinical goals, interventions, and outcomes for a patient |
| **FHIR** | Fast Healthcare Interoperability Resources — a standard for exchanging healthcare data |
| **HIPAA** | Health Insurance Portability and Accountability Act — US healthcare privacy law |
| **MRN** | Medical Record Number — a unique patient identifier |
| **PHI** | Protected Health Information — any health data that can identify a patient |
| **RBAC** | Role-Based Access Control — permission system based on user roles |
| **RPM** | Remote Patient Monitoring — continuous monitoring via connected devices |
| **Risk Score** | An AI-generated numerical assessment of patient deterioration probability |
| **Telehealth** | Healthcare delivery via video, audio, or messaging technology |
| **Digital Twin** | A virtual model of a patient integrating all available health data |
| **Ambient AI** | AI that listens to clinical conversations and generates documentation |

---

*Eminence HealthOS v0.1.0 — Eminence Tech Solutions*
*For technical documentation, see: [Architecture Guide](ARCHITECTURE_GUIDE.md) | [API Endpoints](API_ENDPOINTS.md) | [Deployment Runbook](DEPLOYMENT.md)*
