"use client";

import React, { useState, useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface AuditEntry {
  id: string;
  timestamp: string;
  eventType: string;
  user: string;
  action: string;
  resource: string;
  ipAddress: string;
  status: "success" | "failure" | "warning";
  duration: number;
  details: {
    requestMethod?: string;
    requestPath?: string;
    requestPayload?: string;
    responseCode?: number;
    responseBody?: string;
    headers?: Record<string, string>;
    userAgent?: string;
    sessionId?: string;
    notes?: string;
  };
}

/* ------------------------------------------------------------------ */
/*  Demo data – 54 realistic entries                                   */
/* ------------------------------------------------------------------ */
const demoAuditEntries: AuditEntry[] = [
  { id: "AUD-001", timestamp: "2026-03-15T08:01:12Z", eventType: "Authentication", user: "dr.smith@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.1.42", status: "success", duration: 210, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 200, userAgent: "Mozilla/5.0 Chrome/124", sessionId: "sess_8a3f2c", notes: "MFA verified via authenticator app" } },
  { id: "AUD-002", timestamp: "2026-03-15T08:02:45Z", eventType: "Data Access", user: "dr.smith@eminence.health", action: "View Patient Record", resource: "Patient #10234 – Jane Doe", ipAddress: "10.0.1.42", status: "success", duration: 145, details: { requestMethod: "GET", requestPath: "/api/v1/patients/10234", responseCode: 200, headers: { "X-Request-Id": "req_f1a2b3" }, notes: "HIPAA audit – provider accessed patient chart" } },
  { id: "AUD-003", timestamp: "2026-03-15T08:05:30Z", eventType: "Clinical", user: "dr.smith@eminence.health", action: "Create Prescription", resource: "Rx #88421 – Amoxicillin 500mg", ipAddress: "10.0.1.42", status: "success", duration: 320, details: { requestMethod: "POST", requestPath: "/api/v1/prescriptions", requestPayload: '{"patientId":10234,"medication":"Amoxicillin","dose":"500mg","frequency":"TID","duration":"10 days"}', responseCode: 201, notes: "New prescription created for Patient #10234" } },
  { id: "AUD-004", timestamp: "2026-03-15T08:10:05Z", eventType: "Authentication", user: "nurse.jones@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.2.18", status: "success", duration: 195, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 200, sessionId: "sess_7b4e1d", notes: "MFA verified via SMS" } },
  { id: "AUD-005", timestamp: "2026-03-15T08:12:33Z", eventType: "Data Access", user: "nurse.jones@eminence.health", action: "View Lab Results", resource: "Lab Order #LB-5521 – CBC Panel", ipAddress: "10.0.2.18", status: "success", duration: 112, details: { requestMethod: "GET", requestPath: "/api/v1/labs/5521", responseCode: 200, notes: "HIPAA audit – nurse viewed lab results" } },
  { id: "AUD-006", timestamp: "2026-03-15T08:15:00Z", eventType: "Authentication", user: "unknown@external.com", action: "Login Attempt", resource: "/auth/login", ipAddress: "203.0.113.55", status: "failure", duration: 85, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 401, notes: "Invalid credentials – account not found" } },
  { id: "AUD-007", timestamp: "2026-03-15T08:15:45Z", eventType: "Authentication", user: "unknown@external.com", action: "Login Attempt", resource: "/auth/login", ipAddress: "203.0.113.55", status: "failure", duration: 78, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 401, notes: "Repeated failed attempt – rate limit warning issued" } },
  { id: "AUD-008", timestamp: "2026-03-15T08:20:10Z", eventType: "API", user: "integration-svc", action: "Sync EHR Records", resource: "/api/v1/ehr/sync", ipAddress: "10.0.5.100", status: "success", duration: 1840, details: { requestMethod: "POST", requestPath: "/api/v1/ehr/sync", requestPayload: '{"source":"epic","batchSize":250}', responseCode: 200, responseBody: '{"synced":248,"skipped":2}', notes: "Scheduled EHR sync from Epic" } },
  { id: "AUD-009", timestamp: "2026-03-15T08:25:02Z", eventType: "Configuration", user: "admin@eminence.health", action: "Update Security Policy", resource: "Policy: Password Requirements", ipAddress: "10.0.1.5", status: "success", duration: 290, details: { requestMethod: "PUT", requestPath: "/api/v1/config/security/password-policy", requestPayload: '{"minLength":12,"requireMFA":true,"maxAge":90}', responseCode: 200, notes: "Password policy updated – minimum length increased to 12" } },
  { id: "AUD-010", timestamp: "2026-03-15T08:30:15Z", eventType: "Data Access", user: "dr.patel@eminence.health", action: "View Patient Record", resource: "Patient #10891 – Robert Chen", ipAddress: "10.0.3.22", status: "success", duration: 130, details: { requestMethod: "GET", requestPath: "/api/v1/patients/10891", responseCode: 200, notes: "HIPAA audit – provider accessed patient chart" } },
  { id: "AUD-011", timestamp: "2026-03-15T08:32:50Z", eventType: "Clinical", user: "dr.patel@eminence.health", action: "Modify Prescription", resource: "Rx #88310 – Metformin 1000mg", ipAddress: "10.0.3.22", status: "success", duration: 275, details: { requestMethod: "PATCH", requestPath: "/api/v1/prescriptions/88310", requestPayload: '{"dose":"1000mg","frequency":"BID","reason":"Dose adjustment per A1C results"}', responseCode: 200, notes: "Prescription dose adjusted" } },
  { id: "AUD-012", timestamp: "2026-03-15T08:35:18Z", eventType: "System", user: "system", action: "Backup Initiated", resource: "Database: eminence_prod", ipAddress: "10.0.10.1", status: "success", duration: 45200, details: { requestMethod: "POST", requestPath: "/internal/backup/start", responseCode: 200, responseBody: '{"backupId":"bk_20260315_0835","sizeGB":142}', notes: "Automated daily backup started" } },
  { id: "AUD-013", timestamp: "2026-03-15T08:40:22Z", eventType: "Data Access", user: "nurse.jones@eminence.health", action: "View Patient Record", resource: "Patient #10567 – Maria Garcia", ipAddress: "10.0.2.18", status: "success", duration: 118, details: { requestMethod: "GET", requestPath: "/api/v1/patients/10567", responseCode: 200, notes: "HIPAA audit – nurse accessed patient chart for vitals entry" } },
  { id: "AUD-014", timestamp: "2026-03-15T08:42:10Z", eventType: "Clinical", user: "nurse.jones@eminence.health", action: "Record Vitals", resource: "Patient #10567 – Vitals Entry", ipAddress: "10.0.2.18", status: "success", duration: 195, details: { requestMethod: "POST", requestPath: "/api/v1/patients/10567/vitals", requestPayload: '{"bp":"120/80","hr":72,"temp":98.6,"spo2":98}', responseCode: 201, notes: "Routine vitals recorded" } },
  { id: "AUD-015", timestamp: "2026-03-15T08:45:00Z", eventType: "API", user: "integration-svc", action: "Fetch Lab Results", resource: "/api/v1/labs/external/quest", ipAddress: "10.0.5.100", status: "success", duration: 2100, details: { requestMethod: "GET", requestPath: "/api/v1/labs/external/quest?pending=true", responseCode: 200, responseBody: '{"fetched":15,"newResults":8}', notes: "Automated lab result retrieval from Quest Diagnostics" } },
  { id: "AUD-016", timestamp: "2026-03-15T08:48:30Z", eventType: "Authentication", user: "dr.williams@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.3.45", status: "success", duration: 205, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 200, sessionId: "sess_9c5f3a", notes: "MFA verified via biometric" } },
  { id: "AUD-017", timestamp: "2026-03-15T08:50:12Z", eventType: "Data Access", user: "dr.williams@eminence.health", action: "Search Patients", resource: "Patient Search – 'diabetes type 2'", ipAddress: "10.0.3.45", status: "success", duration: 340, details: { requestMethod: "GET", requestPath: "/api/v1/patients/search?q=diabetes+type+2", responseCode: 200, responseBody: '{"total":47,"returned":20}', notes: "Clinical search for patient cohort" } },
  { id: "AUD-018", timestamp: "2026-03-15T08:52:55Z", eventType: "Data Access", user: "dr.williams@eminence.health", action: "Export Patient List", resource: "Patient Cohort Export – CSV", ipAddress: "10.0.3.45", status: "warning", duration: 890, details: { requestMethod: "POST", requestPath: "/api/v1/patients/export", requestPayload: '{"format":"csv","filter":"diabetes_type_2","fields":["name","dob","lastVisit"]}', responseCode: 200, notes: "HIPAA audit – bulk data export flagged for review" } },
  { id: "AUD-019", timestamp: "2026-03-15T08:55:40Z", eventType: "Configuration", user: "admin@eminence.health", action: "Add User Role", resource: "Role: Clinical Researcher", ipAddress: "10.0.1.5", status: "success", duration: 180, details: { requestMethod: "POST", requestPath: "/api/v1/config/roles", requestPayload: '{"name":"Clinical Researcher","permissions":["read:patients","read:labs","export:anonymized"]}', responseCode: 201, notes: "New role created for research team" } },
  { id: "AUD-020", timestamp: "2026-03-15T09:00:05Z", eventType: "Authentication", user: "tech.support@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.1.88", status: "success", duration: 198, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 200, sessionId: "sess_2d8e4f", notes: "Support staff login" } },
  { id: "AUD-021", timestamp: "2026-03-15T09:02:30Z", eventType: "System", user: "system", action: "Certificate Renewal", resource: "TLS Cert: *.eminence.health", ipAddress: "10.0.10.1", status: "success", duration: 5400, details: { requestMethod: "POST", requestPath: "/internal/certs/renew", responseCode: 200, notes: "Auto-renewed TLS certificate – expires 2027-03-15" } },
  { id: "AUD-022", timestamp: "2026-03-15T09:05:18Z", eventType: "Data Access", user: "dr.patel@eminence.health", action: "View Lab Results", resource: "Lab Order #LB-5530 – Metabolic Panel", ipAddress: "10.0.3.22", status: "success", duration: 105, details: { requestMethod: "GET", requestPath: "/api/v1/labs/5530", responseCode: 200, notes: "HIPAA audit – provider viewed lab results" } },
  { id: "AUD-023", timestamp: "2026-03-15T09:08:42Z", eventType: "Clinical", user: "dr.patel@eminence.health", action: "Add Clinical Note", resource: "Patient #10891 – Progress Note", ipAddress: "10.0.3.22", status: "success", duration: 410, details: { requestMethod: "POST", requestPath: "/api/v1/patients/10891/notes", requestPayload: '{"type":"progress","text":"Patient reports improved glucose control..."}', responseCode: 201, notes: "Clinical documentation added" } },
  { id: "AUD-024", timestamp: "2026-03-15T09:12:00Z", eventType: "Authentication", user: "dr.smith@eminence.health", action: "Session Refresh", resource: "/auth/refresh", ipAddress: "10.0.1.42", status: "success", duration: 55, details: { requestMethod: "POST", requestPath: "/api/v1/auth/refresh", responseCode: 200, sessionId: "sess_8a3f2c", notes: "Token refreshed" } },
  { id: "AUD-025", timestamp: "2026-03-15T09:15:30Z", eventType: "API", user: "integration-svc", action: "Send HL7 Message", resource: "/api/v1/hl7/outbound", ipAddress: "10.0.5.100", status: "failure", duration: 3050, details: { requestMethod: "POST", requestPath: "/api/v1/hl7/outbound", requestPayload: '{"messageType":"ADT^A08","destination":"regional-hie"}', responseCode: 502, responseBody: '{"error":"Connection refused by remote host"}', notes: "HL7 message delivery failed – regional HIE unreachable" } },
  { id: "AUD-026", timestamp: "2026-03-15T09:18:15Z", eventType: "System", user: "system", action: "Alert Triggered", resource: "Alert: HL7 Outbound Failure", ipAddress: "10.0.10.1", status: "warning", duration: 30, details: { requestMethod: "POST", requestPath: "/internal/alerts/trigger", responseCode: 200, notes: "On-call notification sent for HL7 delivery failure" } },
  { id: "AUD-027", timestamp: "2026-03-15T09:20:45Z", eventType: "Data Access", user: "billing@eminence.health", action: "View Billing Record", resource: "Claim #CLM-44210", ipAddress: "10.0.4.30", status: "success", duration: 160, details: { requestMethod: "GET", requestPath: "/api/v1/billing/claims/44210", responseCode: 200, notes: "Billing staff accessed claim details" } },
  { id: "AUD-028", timestamp: "2026-03-15T09:25:10Z", eventType: "Configuration", user: "admin@eminence.health", action: "Update Notification Settings", resource: "Notification: Email Templates", ipAddress: "10.0.1.5", status: "success", duration: 220, details: { requestMethod: "PUT", requestPath: "/api/v1/config/notifications/email", requestPayload: '{"template":"appointment_reminder","subject":"Your Upcoming Appointment","enabled":true}', responseCode: 200, notes: "Email template updated for appointment reminders" } },
  { id: "AUD-029", timestamp: "2026-03-15T09:28:55Z", eventType: "Authentication", user: "intern.taylor@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.2.55", status: "success", duration: 230, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 200, sessionId: "sess_4f7a1b", notes: "Limited access – intern role" } },
  { id: "AUD-030", timestamp: "2026-03-15T09:30:20Z", eventType: "Data Access", user: "intern.taylor@eminence.health", action: "View Patient Record", resource: "Patient #10345 – Emily Watson", ipAddress: "10.0.2.55", status: "warning", duration: 95, details: { requestMethod: "GET", requestPath: "/api/v1/patients/10345", responseCode: 200, notes: "HIPAA audit – intern access flagged for supervisor review" } },
  { id: "AUD-031", timestamp: "2026-03-15T09:33:40Z", eventType: "Clinical", user: "dr.williams@eminence.health", action: "Order Lab Test", resource: "Lab Order #LB-5545 – Lipid Panel", ipAddress: "10.0.3.45", status: "success", duration: 260, details: { requestMethod: "POST", requestPath: "/api/v1/labs/orders", requestPayload: '{"patientId":10678,"tests":["lipid_panel"],"priority":"routine"}', responseCode: 201, notes: "Routine lab order placed" } },
  { id: "AUD-032", timestamp: "2026-03-15T09:36:15Z", eventType: "API", user: "integration-svc", action: "Insurance Eligibility Check", resource: "/api/v1/insurance/eligibility", ipAddress: "10.0.5.100", status: "success", duration: 1250, details: { requestMethod: "POST", requestPath: "/api/v1/insurance/eligibility", requestPayload: '{"patientId":10234,"payerId":"BCBS","serviceDate":"2026-03-15"}', responseCode: 200, responseBody: '{"eligible":true,"copay":25,"deductibleMet":true}', notes: "Real-time eligibility verification" } },
  { id: "AUD-033", timestamp: "2026-03-15T09:40:00Z", eventType: "System", user: "system", action: "Audit Log Rotation", resource: "Logs: audit_2026_03_14.gz", ipAddress: "10.0.10.1", status: "success", duration: 8200, details: { requestMethod: "POST", requestPath: "/internal/logs/rotate", responseCode: 200, responseBody: '{"compressed":"audit_2026_03_14.gz","sizeMB":340}', notes: "Previous day audit log compressed and archived" } },
  { id: "AUD-034", timestamp: "2026-03-15T09:42:30Z", eventType: "Authentication", user: "dr.chen@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.3.60", status: "failure", duration: 90, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 401, notes: "Expired password – user prompted to reset" } },
  { id: "AUD-035", timestamp: "2026-03-15T09:43:10Z", eventType: "Authentication", user: "dr.chen@eminence.health", action: "Password Reset", resource: "/auth/reset-password", ipAddress: "10.0.3.60", status: "success", duration: 150, details: { requestMethod: "POST", requestPath: "/api/v1/auth/reset-password", responseCode: 200, notes: "Password reset completed successfully" } },
  { id: "AUD-036", timestamp: "2026-03-15T09:44:00Z", eventType: "Authentication", user: "dr.chen@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.3.60", status: "success", duration: 215, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 200, sessionId: "sess_6e2c9d", notes: "Login after password reset" } },
  { id: "AUD-037", timestamp: "2026-03-15T09:48:25Z", eventType: "Data Access", user: "dr.chen@eminence.health", action: "View Patient Record", resource: "Patient #10102 – James Miller", ipAddress: "10.0.3.60", status: "success", duration: 125, details: { requestMethod: "GET", requestPath: "/api/v1/patients/10102", responseCode: 200, notes: "HIPAA audit – provider accessed patient chart" } },
  { id: "AUD-038", timestamp: "2026-03-15T09:50:55Z", eventType: "Clinical", user: "dr.chen@eminence.health", action: "Discontinue Medication", resource: "Rx #87990 – Lisinopril 10mg", ipAddress: "10.0.3.60", status: "success", duration: 185, details: { requestMethod: "PATCH", requestPath: "/api/v1/prescriptions/87990", requestPayload: '{"status":"discontinued","reason":"Adverse reaction – persistent cough"}', responseCode: 200, notes: "Medication discontinued due to side effects" } },
  { id: "AUD-039", timestamp: "2026-03-15T09:55:10Z", eventType: "API", user: "integration-svc", action: "Pharmacy Notification", resource: "/api/v1/pharmacy/notify", ipAddress: "10.0.5.100", status: "success", duration: 780, details: { requestMethod: "POST", requestPath: "/api/v1/pharmacy/notify", requestPayload: '{"rxId":87990,"action":"discontinue","pharmacyId":"CVS-1042"}', responseCode: 200, notes: "Pharmacy notified of medication discontinuation" } },
  { id: "AUD-040", timestamp: "2026-03-15T10:00:00Z", eventType: "System", user: "system", action: "Health Check", resource: "All Services", ipAddress: "10.0.10.1", status: "success", duration: 450, details: { requestMethod: "GET", requestPath: "/internal/health", responseCode: 200, responseBody: '{"services":12,"healthy":12,"degraded":0}', notes: "Scheduled health check – all services operational" } },
  { id: "AUD-041", timestamp: "2026-03-15T10:05:22Z", eventType: "Data Access", user: "dr.smith@eminence.health", action: "View Imaging Report", resource: "Imaging #IMG-2201 – Chest X-Ray", ipAddress: "10.0.1.42", status: "success", duration: 310, details: { requestMethod: "GET", requestPath: "/api/v1/imaging/2201", responseCode: 200, notes: "HIPAA audit – provider viewed radiology report" } },
  { id: "AUD-042", timestamp: "2026-03-15T10:10:45Z", eventType: "Configuration", user: "admin@eminence.health", action: "Enable Feature Flag", resource: "Feature: AI Diagnosis Assist", ipAddress: "10.0.1.5", status: "success", duration: 95, details: { requestMethod: "PUT", requestPath: "/api/v1/config/features/ai-diagnosis-assist", requestPayload: '{"enabled":true,"rolloutPercentage":25}', responseCode: 200, notes: "AI Diagnosis Assist enabled for 25% of users" } },
  { id: "AUD-043", timestamp: "2026-03-15T10:15:30Z", eventType: "Authentication", user: "nurse.brown@eminence.health", action: "Login", resource: "/auth/login", ipAddress: "10.0.2.72", status: "success", duration: 188, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 200, sessionId: "sess_3a9b7e", notes: "Standard nurse login" } },
  { id: "AUD-044", timestamp: "2026-03-15T10:18:10Z", eventType: "Clinical", user: "nurse.brown@eminence.health", action: "Administer Medication", resource: "MAR Entry – Patient #10234", ipAddress: "10.0.2.72", status: "success", duration: 175, details: { requestMethod: "POST", requestPath: "/api/v1/patients/10234/mar", requestPayload: '{"medication":"Amoxicillin 500mg","route":"PO","time":"10:15"}', responseCode: 201, notes: "Medication administration recorded" } },
  { id: "AUD-045", timestamp: "2026-03-15T10:22:00Z", eventType: "API", user: "integration-svc", action: "Appointment Sync", resource: "/api/v1/scheduling/sync", ipAddress: "10.0.5.100", status: "success", duration: 960, details: { requestMethod: "POST", requestPath: "/api/v1/scheduling/sync", responseCode: 200, responseBody: '{"synced":34,"conflicts":2}', notes: "Calendar sync with external scheduling system" } },
  { id: "AUD-046", timestamp: "2026-03-15T10:25:40Z", eventType: "Data Access", user: "billing@eminence.health", action: "Generate Invoice", resource: "Invoice #INV-78432", ipAddress: "10.0.4.30", status: "success", duration: 520, details: { requestMethod: "POST", requestPath: "/api/v1/billing/invoices", requestPayload: '{"patientId":10234,"encounterIds":[45001,45002],"payerId":"BCBS"}', responseCode: 201, notes: "Invoice generated for recent encounters" } },
  { id: "AUD-047", timestamp: "2026-03-15T10:30:15Z", eventType: "Authentication", user: "dr.smith@eminence.health", action: "Logout", resource: "/auth/logout", ipAddress: "10.0.1.42", status: "success", duration: 42, details: { requestMethod: "POST", requestPath: "/api/v1/auth/logout", responseCode: 200, sessionId: "sess_8a3f2c", notes: "User initiated logout" } },
  { id: "AUD-048", timestamp: "2026-03-15T10:32:55Z", eventType: "System", user: "system", action: "Index Optimization", resource: "Database: eminence_prod", ipAddress: "10.0.10.1", status: "success", duration: 12400, details: { requestMethod: "POST", requestPath: "/internal/db/optimize", responseCode: 200, responseBody: '{"tablesOptimized":8,"indexesRebuilt":14}', notes: "Scheduled index optimization completed" } },
  { id: "AUD-049", timestamp: "2026-03-15T10:35:20Z", eventType: "Authentication", user: "unknown@phishing.net", action: "Login Attempt", resource: "/auth/login", ipAddress: "198.51.100.77", status: "failure", duration: 65, details: { requestMethod: "POST", requestPath: "/api/v1/auth/login", responseCode: 401, userAgent: "curl/7.88", notes: "Suspicious login attempt – IP blocked after 3 failures" } },
  { id: "AUD-050", timestamp: "2026-03-15T10:38:10Z", eventType: "Configuration", user: "admin@eminence.health", action: "Update IP Allowlist", resource: "Security: IP Allowlist", ipAddress: "10.0.1.5", status: "success", duration: 130, details: { requestMethod: "PUT", requestPath: "/api/v1/config/security/ip-allowlist", requestPayload: '{"blocked":["198.51.100.77"],"action":"add_to_blocklist"}', responseCode: 200, notes: "Blocked suspicious IP address" } },
  { id: "AUD-051", timestamp: "2026-03-15T10:42:00Z", eventType: "Data Access", user: "dr.williams@eminence.health", action: "View Allergy List", resource: "Patient #10678 – Allergies", ipAddress: "10.0.3.45", status: "success", duration: 88, details: { requestMethod: "GET", requestPath: "/api/v1/patients/10678/allergies", responseCode: 200, notes: "HIPAA audit – allergy review before prescribing" } },
  { id: "AUD-052", timestamp: "2026-03-15T10:45:30Z", eventType: "Clinical", user: "dr.williams@eminence.health", action: "Create Referral", resource: "Referral #REF-3321 – Cardiology", ipAddress: "10.0.3.45", status: "success", duration: 340, details: { requestMethod: "POST", requestPath: "/api/v1/referrals", requestPayload: '{"patientId":10678,"specialty":"cardiology","reason":"Abnormal lipid panel","urgency":"routine"}', responseCode: 201, notes: "Cardiology referral placed" } },
  { id: "AUD-053", timestamp: "2026-03-15T10:50:15Z", eventType: "API", user: "integration-svc", action: "FHIR Resource Fetch", resource: "/api/v1/fhir/Patient", ipAddress: "10.0.5.100", status: "success", duration: 680, details: { requestMethod: "GET", requestPath: "/api/v1/fhir/Patient?_count=50", responseCode: 200, responseBody: '{"resourceType":"Bundle","total":50}', notes: "FHIR API access – compliant with R4 spec" } },
  { id: "AUD-054", timestamp: "2026-03-15T10:55:00Z", eventType: "Authentication", user: "nurse.jones@eminence.health", action: "Logout", resource: "/auth/logout", ipAddress: "10.0.2.18", status: "success", duration: 38, details: { requestMethod: "POST", requestPath: "/api/v1/auth/logout", responseCode: 200, sessionId: "sess_7b4e1d", notes: "End of shift logout" } },
  {
    id: "AUD-055",
    timestamp: "2026-03-15T11:02:30Z",
    eventType: "Data Access",
    user: "dr.chen@eminence.health",
    action: "View Medication History",
    resource: "Patient #10102 – Full Medication History",
    ipAddress: "10.0.3.60",
    status: "success",
    duration: 245,
    details: {
      requestMethod: "GET",
      requestPath: "/api/v1/patients/10102/medications?history=full",
      responseCode: 200,
      responseBody: '{"active":3,"discontinued":7,"total":10}',
      notes: "HIPAA audit – full medication history reviewed before prescribing",
    },
  },
  {
    id: "AUD-056",
    timestamp: "2026-03-15T11:08:15Z",
    eventType: "Clinical",
    user: "dr.chen@eminence.health",
    action: "Create Prescription",
    resource: "Rx #88450 – Losartan 50mg",
    ipAddress: "10.0.3.60",
    status: "success",
    duration: 298,
    details: {
      requestMethod: "POST",
      requestPath: "/api/v1/prescriptions",
      requestPayload: '{"patientId":10102,"medication":"Losartan","dose":"50mg","frequency":"QD","reason":"Replacement for discontinued Lisinopril"}',
      responseCode: 201,
      notes: "Alternative medication prescribed after Lisinopril discontinuation",
    },
  },
  {
    id: "AUD-057",
    timestamp: "2026-03-15T11:12:45Z",
    eventType: "API",
    user: "integration-svc",
    action: "Drug Interaction Check",
    resource: "/api/v1/clinical/drug-interactions",
    ipAddress: "10.0.5.100",
    status: "warning",
    duration: 430,
    details: {
      requestMethod: "POST",
      requestPath: "/api/v1/clinical/drug-interactions",
      requestPayload: '{"medications":["Losartan","Metformin","Aspirin"]}',
      responseCode: 200,
      responseBody: '{"interactions":1,"severity":"low","detail":"Monitor potassium levels with Losartan"}',
      notes: "Low-severity interaction detected – informational alert sent to provider",
    },
  },
  {
    id: "AUD-058",
    timestamp: "2026-03-15T11:18:20Z",
    eventType: "Authentication",
    user: "pharmacist.lee@eminence.health",
    action: "Login",
    resource: "/auth/login",
    ipAddress: "10.0.4.15",
    status: "success",
    duration: 202,
    details: {
      requestMethod: "POST",
      requestPath: "/api/v1/auth/login",
      responseCode: 200,
      sessionId: "sess_5b1d8c",
      userAgent: "Mozilla/5.0 Firefox/125",
      notes: "Pharmacist login – prescription verification queue",
    },
  },
  {
    id: "AUD-059",
    timestamp: "2026-03-15T11:22:00Z",
    eventType: "Clinical",
    user: "pharmacist.lee@eminence.health",
    action: "Verify Prescription",
    resource: "Rx #88450 – Losartan 50mg",
    ipAddress: "10.0.4.15",
    status: "success",
    duration: 155,
    details: {
      requestMethod: "PATCH",
      requestPath: "/api/v1/prescriptions/88450/verify",
      requestPayload: '{"verified":true,"pharmacistNotes":"Dosage appropriate, no contraindications"}',
      responseCode: 200,
      notes: "Prescription verified by pharmacist",
    },
  },
  {
    id: "AUD-060",
    timestamp: "2026-03-15T11:25:35Z",
    eventType: "System",
    user: "system",
    action: "Queue Processing",
    resource: "Message Queue: prescription-notifications",
    ipAddress: "10.0.10.1",
    status: "success",
    duration: 1200,
    details: {
      requestMethod: "POST",
      requestPath: "/internal/queues/prescription-notifications/process",
      responseCode: 200,
      responseBody: '{"processed":12,"failed":0,"pending":3}',
      notes: "Batch notification processing for verified prescriptions",
    },
  },
  {
    id: "AUD-061",
    timestamp: "2026-03-15T11:30:10Z",
    eventType: "Data Access",
    user: "dr.williams@eminence.health",
    action: "View Discharge Summary",
    resource: "Patient #10445 – Discharge Summary",
    ipAddress: "10.0.3.45",
    status: "success",
    duration: 178,
    details: {
      requestMethod: "GET",
      requestPath: "/api/v1/patients/10445/encounters/latest/discharge",
      responseCode: 200,
      notes: "HIPAA audit – provider reviewed discharge documentation",
    },
  },
  {
    id: "AUD-062",
    timestamp: "2026-03-15T11:35:50Z",
    eventType: "Configuration",
    user: "admin@eminence.health",
    action: "Update Audit Retention Policy",
    resource: "Policy: Audit Log Retention",
    ipAddress: "10.0.1.5",
    status: "success",
    duration: 110,
    details: {
      requestMethod: "PUT",
      requestPath: "/api/v1/config/audit/retention",
      requestPayload: '{"retentionDays":2555,"archiveEnabled":true,"compressionLevel":"high"}',
      responseCode: 200,
      notes: "Retention extended to 7 years per HIPAA compliance requirements",
    },
  },
  {
    id: "AUD-063",
    timestamp: "2026-03-15T11:40:25Z",
    eventType: "Authentication",
    user: "unknown@brute.io",
    action: "Login Attempt",
    resource: "/auth/login",
    ipAddress: "192.0.2.44",
    status: "failure",
    duration: 72,
    details: {
      requestMethod: "POST",
      requestPath: "/api/v1/auth/login",
      responseCode: 401,
      userAgent: "python-requests/2.31",
      notes: "Automated brute-force attempt detected – IP added to threat list",
    },
  },
  {
    id: "AUD-064",
    timestamp: "2026-03-15T11:40:26Z",
    eventType: "System",
    user: "system",
    action: "Threat Detection Alert",
    resource: "Security: Threat Intelligence",
    ipAddress: "10.0.10.1",
    status: "warning",
    duration: 45,
    details: {
      requestMethod: "POST",
      requestPath: "/internal/security/threats/alert",
      responseCode: 200,
      responseBody: '{"threatLevel":"medium","source":"192.0.2.44","action":"auto-blocked"}',
      notes: "Automated threat response – IP blocked and security team notified",
    },
  },
  {
    id: "AUD-065",
    timestamp: "2026-03-15T11:45:00Z",
    eventType: "API",
    user: "integration-svc",
    action: "Patient Portal Sync",
    resource: "/api/v1/portal/sync",
    ipAddress: "10.0.5.100",
    status: "success",
    duration: 1890,
    details: {
      requestMethod: "POST",
      requestPath: "/api/v1/portal/sync",
      requestPayload: '{"scope":"appointments,results,messages","window":"24h"}',
      responseCode: 200,
      responseBody: '{"appointmentsSynced":28,"resultsSynced":15,"messagesSynced":42}',
      notes: "Patient portal data synchronization completed",
    },
  },
  {
    id: "AUD-066",
    timestamp: "2026-03-15T11:50:30Z",
    eventType: "Data Access",
    user: "nurse.brown@eminence.health",
    action: "View Care Plan",
    resource: "Patient #10234 – Care Plan",
    ipAddress: "10.0.2.72",
    status: "success",
    duration: 135,
    details: {
      requestMethod: "GET",
      requestPath: "/api/v1/patients/10234/care-plan",
      responseCode: 200,
      notes: "HIPAA audit – nurse reviewed care plan for medication administration",
    },
  },
  {
    id: "AUD-067",
    timestamp: "2026-03-15T11:55:15Z",
    eventType: "Clinical",
    user: "dr.patel@eminence.health",
    action: "Sign Clinical Note",
    resource: "Patient #10891 – Progress Note (Signed)",
    ipAddress: "10.0.3.22",
    status: "success",
    duration: 92,
    details: {
      requestMethod: "PATCH",
      requestPath: "/api/v1/patients/10891/notes/latest/sign",
      requestPayload: '{"signature":"digital","attestation":true}',
      responseCode: 200,
      notes: "Clinical note digitally signed and locked for editing",
    },
  },
  {
    id: "AUD-068",
    timestamp: "2026-03-15T12:00:00Z",
    eventType: "System",
    user: "system",
    action: "Scheduled Maintenance Window",
    resource: "Maintenance: Read-Only Mode",
    ipAddress: "10.0.10.1",
    status: "warning",
    duration: 15,
    details: {
      requestMethod: "POST",
      requestPath: "/internal/maintenance/schedule",
      responseCode: 200,
      responseBody: '{"window":"2026-03-16T02:00:00Z/2026-03-16T04:00:00Z","mode":"read-only"}',
      notes: "Maintenance window scheduled for database migration – users notified",
    },
  },
];

/* ------------------------------------------------------------------ */
/*  Chart data                                                         */
/* ------------------------------------------------------------------ */
const activityTrendData = [
  { day: "Mar 9", events: 312, failures: 8, warnings: 15 },
  { day: "Mar 10", events: 458, failures: 12, warnings: 22 },
  { day: "Mar 11", events: 389, failures: 5, warnings: 18 },
  { day: "Mar 12", events: 421, failures: 9, warnings: 20 },
  { day: "Mar 13", events: 510, failures: 14, warnings: 28 },
  { day: "Mar 14", events: 475, failures: 11, warnings: 24 },
  { day: "Mar 15", events: 348, failures: 6, warnings: 16 },
];

const categoryData = [
  { name: "Authentication", value: 14, color: "#6366f1" },
  { name: "Data Access", value: 12, color: "#06b6d4" },
  { name: "Configuration", value: 5, color: "#f59e0b" },
  { name: "Clinical", value: 9, color: "#10b981" },
  { name: "API", value: 7, color: "#8b5cf6" },
  { name: "System", value: 7, color: "#ef4444" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function formatTimestamp(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDuration(ms: number) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function statusBadge(status: AuditEntry["status"]) {
  const map = {
    success: "badge-success",
    failure: "badge-danger",
    warning: "badge-warning",
  };
  return map[status] ?? "badge-info";
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function AuditLogPage() {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterEventType, setFilterEventType] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");
  const [filterUser, setFilterUser] = useState("All");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  /* Derived unique users for filter */
  const uniqueUsers = useMemo(() => {
    const set = new Set(demoAuditEntries.map((e) => e.user));
    return ["All", ...Array.from(set).sort()];
  }, []);

  /* Filtering */
  const filteredEntries = useMemo(() => {
    return demoAuditEntries.filter((entry) => {
      if (filterEventType !== "All" && entry.eventType !== filterEventType) return false;
      if (filterStatus !== "All" && entry.status !== filterStatus.toLowerCase()) return false;
      if (filterUser !== "All" && entry.user !== filterUser) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = `${entry.action} ${entry.resource} ${entry.user} ${entry.ipAddress} ${entry.eventType}`.toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      if (dateFrom) {
        const from = new Date(dateFrom);
        if (new Date(entry.timestamp) < from) return false;
      }
      if (dateTo) {
        const to = new Date(dateTo);
        to.setHours(23, 59, 59);
        if (new Date(entry.timestamp) > to) return false;
      }
      return true;
    });
  }, [filterEventType, filterStatus, filterUser, searchQuery, dateFrom, dateTo]);

  /* KPIs */
  const totalEvents = demoAuditEntries.length;
  const failedActions = demoAuditEntries.filter((e) => e.status === "failure").length;
  const uniqueUserCount = new Set(demoAuditEntries.map((e) => e.user)).size;
  const avgResponse = Math.round(demoAuditEntries.reduce((s, e) => s + e.duration, 0) / totalEvents);

  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;
  const totalPages = Math.ceil(filteredEntries.length / pageSize);
  const paginatedEntries = filteredEntries.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  /* Critical / warning events for sidebar */
  const criticalEvents = useMemo(() => {
    return demoAuditEntries
      .filter((e) => e.status === "failure" || e.status === "warning")
      .slice(0, 6);
  }, []);

  const handleExport = () => {
    alert("Export initiated — generating PDF audit report...");
  };

  const handleClearFilters = () => {
    setSearchQuery("");
    setFilterEventType("All");
    setFilterStatus("All");
    setFilterUser("All");
    setDateFrom("");
    setDateTo("");
    setCurrentPage(1);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6 space-y-6">
      {/* ---- Header ---- */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Audit Log</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Centralized system activity monitoring</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Live indicator */}
          <span className="inline-flex items-center gap-2 text-sm font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1.5 rounded-full">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
            </span>
            Live
          </span>
          <button onClick={handleExport} className="btn-secondary text-sm px-4 py-2 rounded-lg">
            Export PDF
          </button>
        </div>
      </div>

      {/* ---- KPI Cards ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Events (24h)", value: totalEvents.toLocaleString(), sub: "+12% vs yesterday", color: "text-indigo-600 dark:text-indigo-400" },
          { label: "Failed Actions", value: failedActions.toString(), sub: "Requires attention", color: "text-red-600 dark:text-red-400" },
          { label: "Unique Users", value: uniqueUserCount.toString(), sub: "Active in last 24h", color: "text-cyan-600 dark:text-cyan-400" },
          { label: "Avg Response Time", value: `${avgResponse}ms`, sub: "Within SLA", color: "text-emerald-600 dark:text-emerald-400" },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover p-5">
            <p className="text-sm text-gray-500 dark:text-gray-400">{kpi.label}</p>
            <p className={`text-2xl font-bold mt-1 ${kpi.color}`}>{kpi.value}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* ---- Charts ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Area chart */}
        <div className="card p-5 lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Activity Trend (7-day)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activityTrendData}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
                <Tooltip contentStyle={{ borderRadius: "0.5rem", fontSize: "0.875rem" }} />
                <Area type="monotone" dataKey="events" stroke="#6366f1" fill="url(#areaGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie chart */}
        <div className="card p-5">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Category Breakdown</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={categoryData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" paddingAngle={3}>
                  {categoryData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: "0.5rem", fontSize: "0.875rem" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
            {categoryData.map((c) => (
              <div key={c.name} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: c.color }} />
                {c.name} ({c.value})
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ---- Filters ---- */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Search</label>
            <input
              type="text"
              placeholder="Search actions, resources, users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input w-full text-sm px-3 py-2 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Event Type</label>
            <select value={filterEventType} onChange={(e) => setFilterEventType(e.target.value)} className="select text-sm px-3 py-2 rounded-lg">
              {["All", "Authentication", "Data Access", "Configuration", "Clinical", "API", "System"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Status</label>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="select text-sm px-3 py-2 rounded-lg">
              {["All", "Success", "Failure", "Warning"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">User</label>
            <select value={filterUser} onChange={(e) => setFilterUser(e.target.value)} className="select text-sm px-3 py-2 rounded-lg">
              {uniqueUsers.map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">From</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input text-sm px-3 py-2 rounded-lg" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">To</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input text-sm px-3 py-2 rounded-lg" />
          </div>
        </div>
      </div>

      {/* ---- Table ---- */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="table-header text-left">
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">Event Type</th>
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Resource</th>
                <th className="px-4 py-3 font-medium">IP Address</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Duration</th>
              </tr>
            </thead>
            <tbody>
              {filteredEntries.map((entry) => (
                <React.Fragment key={entry.id}>
                  <tr
                    className="table-row cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    onClick={() => setExpandedRow(expandedRow === entry.id ? null : entry.id)}
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-gray-600 dark:text-gray-300">{formatTimestamp(entry.timestamp)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="badge-info text-xs px-2 py-0.5 rounded-full">{entry.eventType}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-700 dark:text-gray-300 font-mono text-xs">{entry.user}</td>
                    <td className="px-4 py-3 text-gray-800 dark:text-gray-200">{entry.action}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400 max-w-[200px] truncate">{entry.resource}</td>
                    <td className="px-4 py-3 whitespace-nowrap font-mono text-xs text-gray-500 dark:text-gray-400">{entry.ipAddress}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`${statusBadge(entry.status)} text-xs px-2 py-0.5 rounded-full capitalize`}>{entry.status}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400">{formatDuration(entry.duration)}</td>
                  </tr>

                  {/* Expanded details */}
                  {expandedRow === entry.id && (
                    <tr className="bg-gray-50 dark:bg-gray-900/50">
                      <td colSpan={8} className="px-6 py-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="space-y-2">
                            <h4 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">Request Details</h4>
                            {entry.details.requestMethod && (
                              <p className="text-gray-600 dark:text-gray-400">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Method:</span> {entry.details.requestMethod}
                              </p>
                            )}
                            {entry.details.requestPath && (
                              <p className="text-gray-600 dark:text-gray-400">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Path:</span>{" "}
                                <code className="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded">{entry.details.requestPath}</code>
                              </p>
                            )}
                            {entry.details.requestPayload && (
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">Payload:</span>
                                <pre className="mt-1 bg-gray-200 dark:bg-gray-800 p-2 rounded overflow-x-auto text-[11px] leading-relaxed">
                                  {JSON.stringify(JSON.parse(entry.details.requestPayload), null, 2)}
                                </pre>
                              </div>
                            )}
                            {entry.details.userAgent && (
                              <p className="text-gray-600 dark:text-gray-400">
                                <span className="font-medium text-gray-700 dark:text-gray-300">User-Agent:</span> {entry.details.userAgent}
                              </p>
                            )}
                          </div>
                          <div className="space-y-2">
                            <h4 className="font-semibold text-gray-800 dark:text-gray-200 text-sm">Response Details</h4>
                            {entry.details.responseCode !== undefined && (
                              <p className="text-gray-600 dark:text-gray-400">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Status Code:</span>{" "}
                                <span className={entry.details.responseCode < 400 ? "text-emerald-600" : "text-red-600"}>
                                  {entry.details.responseCode}
                                </span>
                              </p>
                            )}
                            {entry.details.responseBody && (
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">Response Body:</span>
                                <pre className="mt-1 bg-gray-200 dark:bg-gray-800 p-2 rounded overflow-x-auto text-[11px] leading-relaxed">
                                  {JSON.stringify(JSON.parse(entry.details.responseBody), null, 2)}
                                </pre>
                              </div>
                            )}
                            {entry.details.sessionId && (
                              <p className="text-gray-600 dark:text-gray-400">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Session ID:</span>{" "}
                                <code className="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded">{entry.details.sessionId}</code>
                              </p>
                            )}
                            {entry.details.headers && (
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">Headers:</span>
                                <pre className="mt-1 bg-gray-200 dark:bg-gray-800 p-2 rounded overflow-x-auto text-[11px] leading-relaxed">
                                  {JSON.stringify(entry.details.headers, null, 2)}
                                </pre>
                              </div>
                            )}
                            {entry.details.notes && (
                              <p className="text-gray-600 dark:text-gray-400">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Notes:</span> {entry.details.notes}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-3">
                          <span>Event ID: <code className="font-mono">{entry.id}</code></span>
                          <span>Full Timestamp: {entry.timestamp}</span>
                          <span>Duration: {formatDuration(entry.duration)}</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {filteredEntries.length === 0 && (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500">
            <p className="text-lg font-medium">No audit entries match your filters</p>
            <p className="text-sm mt-1">Try adjusting your search criteria</p>
          </div>
        )}

        {/* Table footer */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <span>Showing {filteredEntries.length} of {totalEvents} entries</span>
          <span>Click any row to expand details</span>
        </div>
      </div>
    </div>
  );
}
