"use client";

import { useState, useEffect, useCallback } from "react";
import {
  runHIPAAScan,
  fetchHIPAAStatus,
  fetchAIGovernanceModels,
  auditAIModel,
  captureConsent,
  revokeConsent,
  fetchConsentAuditTrail,
  fetchComplianceFrameworks,
  generateComplianceReport,
  runGapAnalysis,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface ScanResult {
  summary: { total_controls: number; passed: number; failed: number; compliance_rate: number };
  findings: { control_id: string; title: string; severity: string; status: string; description: string; remediation: string }[];
  scan_timestamp: string;
}

interface HIPAACategory {
  id: string;
  name: string;
  status: "compliant" | "warning" | "non-compliant";
  description: string;
  remediation: string;
}

interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  user: string;
  resource: string;
  outcome: string;
}

interface AIModel {
  name: string;
  type: string;
  status: "compliant" | "review-needed" | "non-compliant";
  lastAudit: string;
  fairnessScore: number;
  biasIndicators: { metric: string; value: number; threshold: number; pass: boolean }[];
}

interface DriftResult {
  modelName: string;
  featureDrift: number;
  predictionDrift: number;
  dataQuality: number;
  status: string;
}

interface ConsentRecord {
  id: string;
  patient: string;
  consentType: string;
  scope: string;
  status: "active" | "revoked" | "expired";
  dateGranted: string;
  dateRevoked: string | null;
}

interface ConsentEvent {
  id: string;
  timestamp: string;
  patient: string;
  action: string;
  consentType: string;
  actor: string;
}

interface Framework {
  key: string;
  name: string;
  score: number;
  controls: number;
  passing: number;
  failing: number;
  pending: number;
  lastAudit: string;
  nextReview: string;
  status: string;
}

interface GapItem {
  id: string;
  severity: "critical" | "high" | "medium" | "low";
  framework: string;
  description: string;
  recommendedAction: string;
  deadline: string;
}

// ── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_HIPAA_CATEGORIES: HIPAACategory[] = [
  { id: "access-controls", name: "Access Controls", status: "compliant", description: "Role-based access controls enforced across all PHI systems. Multi-factor authentication active for 100% of clinical users.", remediation: "No action required. Continue monitoring access patterns." },
  { id: "encryption", name: "Encryption Standards", status: "compliant", description: "AES-256 encryption at rest, TLS 1.3 in transit. All ePHI encrypted across databases, backups, and file storage.", remediation: "No action required. Certificate renewal scheduled for Q3." },
  { id: "audit-trails", name: "Audit Trails", status: "warning", description: "Audit logging covers 96% of PHI access points. 3 legacy endpoints pending integration with central audit system.", remediation: "Integrate remaining legacy endpoints with centralized audit logging per 45 CFR 164.312(b). Target completion: 30 days." },
  { id: "breach-detection", name: "Breach Detection", status: "compliant", description: "Real-time anomaly detection active. Average incident response time: 4.2 minutes. No breaches detected in past 180 days.", remediation: "No action required. Continue monitoring and quarterly pen testing." },
  { id: "data-integrity", name: "Data Integrity", status: "compliant", description: "Checksums validated on all ePHI transactions. Data integrity verification running on automated schedule.", remediation: "No action required. Integrity checks passing consistently." },
  { id: "transmission-security", name: "Transmission Security", status: "warning", description: "TLS 1.3 enforced on 98% of channels. Two internal microservice connections still using TLS 1.2.", remediation: "Upgrade remaining microservice connections to TLS 1.3. Coordinate with DevOps for certificate rotation." },
];

const DEMO_AUDIT_LOG: AuditLogEntry[] = [
  { id: "1", timestamp: "2026-03-15 14:32:00", action: "PHI Access Audit", user: "System", resource: "All PHI endpoints", outcome: "Passed" },
  { id: "2", timestamp: "2026-03-15 13:15:00", action: "Access Control Review", user: "admin@healthos.io", resource: "Clinical Dashboard", outcome: "Passed" },
  { id: "3", timestamp: "2026-03-15 11:48:00", action: "Encryption Verification", user: "System", resource: "Database Cluster", outcome: "Passed" },
  { id: "4", timestamp: "2026-03-15 10:02:00", action: "HIPAA Scan Completed", user: "System", resource: "Full System", outcome: "94% Compliance" },
  { id: "5", timestamp: "2026-03-15 09:30:00", action: "Breach Detection Scan", user: "HIPAA Monitor", resource: "Network Perimeter", outcome: "No Incidents" },
  { id: "6", timestamp: "2026-03-15 08:15:00", action: "User Permission Change", user: "admin@healthos.io", resource: "User #4521", outcome: "Approved" },
  { id: "7", timestamp: "2026-03-14 23:00:00", action: "Nightly Backup Verification", user: "System", resource: "All Databases", outcome: "Passed" },
  { id: "8", timestamp: "2026-03-14 18:45:00", action: "Failed Login Attempt", user: "unknown", resource: "Admin Portal", outcome: "Blocked" },
];

const DEMO_AI_MODELS: AIModel[] = [
  { name: "Risk Scoring v2.3", type: "XGBoost", status: "compliant", lastAudit: "2026-03-10", fairnessScore: 0.94, biasIndicators: [{ metric: "Demographic Parity", value: 0.03, threshold: 0.1, pass: true }, { metric: "Equalized Odds", value: 0.05, threshold: 0.1, pass: true }] },
  { name: "Readmission Predictor v1.8", type: "Gradient Boost", status: "compliant", lastAudit: "2026-03-08", fairnessScore: 0.91, biasIndicators: [{ metric: "Demographic Parity", value: 0.06, threshold: 0.1, pass: true }, { metric: "Equalized Odds", value: 0.08, threshold: 0.1, pass: true }] },
  { name: "Anomaly Detection v3.1", type: "Isolation Forest", status: "compliant", lastAudit: "2026-03-12", fairnessScore: 0.96, biasIndicators: [{ metric: "Demographic Parity", value: 0.02, threshold: 0.1, pass: true }, { metric: "Equalized Odds", value: 0.03, threshold: 0.1, pass: true }] },
  { name: "NLP Extraction v2.0", type: "Transformer", status: "review-needed", lastAudit: "2026-02-20", fairnessScore: 0.78, biasIndicators: [{ metric: "Demographic Parity", value: 0.12, threshold: 0.1, pass: false }, { metric: "Equalized Odds", value: 0.09, threshold: 0.1, pass: true }] },
  { name: "Treatment Recommender v1.2", type: "Neural Network", status: "non-compliant", lastAudit: "2026-01-15", fairnessScore: 0.65, biasIndicators: [{ metric: "Demographic Parity", value: 0.18, threshold: 0.1, pass: false }, { metric: "Equalized Odds", value: 0.15, threshold: 0.1, pass: false }] },
  { name: "Cohort Clustering v1.5", type: "K-Means", status: "compliant", lastAudit: "2026-03-05", fairnessScore: 0.89, biasIndicators: [{ metric: "Demographic Parity", value: 0.07, threshold: 0.1, pass: true }, { metric: "Equalized Odds", value: 0.06, threshold: 0.1, pass: true }] },
];

const DEMO_DRIFT_RESULTS: DriftResult[] = [
  { modelName: "Risk Scoring v2.3", featureDrift: 0.04, predictionDrift: 0.03, dataQuality: 0.98, status: "stable" },
  { modelName: "Readmission Predictor v1.8", featureDrift: 0.08, predictionDrift: 0.06, dataQuality: 0.95, status: "stable" },
  { modelName: "NLP Extraction v2.0", featureDrift: 0.22, predictionDrift: 0.18, dataQuality: 0.87, status: "drifting" },
  { modelName: "Treatment Recommender v1.2", featureDrift: 0.19, predictionDrift: 0.14, dataQuality: 0.91, status: "warning" },
  { modelName: "Anomaly Detection v3.1", featureDrift: 0.02, predictionDrift: 0.01, dataQuality: 0.99, status: "stable" },
  { modelName: "Cohort Clustering v1.5", featureDrift: 0.09, predictionDrift: 0.07, dataQuality: 0.94, status: "stable" },
];

const DEMO_CONSENTS: ConsentRecord[] = [
  { id: "c1", patient: "Sarah Johnson (#1042)", consentType: "Treatment", scope: "All clinical care", status: "active", dateGranted: "2026-01-15", dateRevoked: null },
  { id: "c2", patient: "Michael Chen (#1087)", consentType: "AI Processing", scope: "Risk scoring, readmission prediction", status: "active", dateGranted: "2026-02-01", dateRevoked: null },
  { id: "c3", patient: "Emily Rodriguez (#1123)", consentType: "Research", scope: "De-identified data sharing", status: "active", dateGranted: "2025-11-20", dateRevoked: null },
  { id: "c4", patient: "James Wilson (#1156)", consentType: "Data Sharing", scope: "Third-party analytics", status: "revoked", dateGranted: "2025-09-10", dateRevoked: "2026-03-12" },
  { id: "c5", patient: "Maria Garcia (#1201)", consentType: "Treatment", scope: "All clinical care", status: "active", dateGranted: "2026-03-01", dateRevoked: null },
  { id: "c6", patient: "Robert Taylor (#1089)", consentType: "AI Processing", scope: "NLP extraction, treatment recommendation", status: "expired", dateGranted: "2025-03-15", dateRevoked: null },
  { id: "c7", patient: "Linda Park (#1234)", consentType: "Research", scope: "Genomic study participation", status: "active", dateGranted: "2026-02-14", dateRevoked: null },
  { id: "c8", patient: "David Kim (#1178)", consentType: "Data Sharing", scope: "Insurance data exchange", status: "revoked", dateGranted: "2025-08-22", dateRevoked: "2026-01-30" },
];

const DEMO_CONSENT_EVENTS: ConsentEvent[] = [
  { id: "e1", timestamp: "2026-03-15 14:20:00", patient: "Sarah Johnson (#1042)", action: "Consent renewed", consentType: "Treatment", actor: "Dr. Williams" },
  { id: "e2", timestamp: "2026-03-14 11:30:00", patient: "James Wilson (#1156)", action: "Consent revoked", consentType: "Data Sharing", actor: "Patient Portal" },
  { id: "e3", timestamp: "2026-03-13 09:15:00", patient: "Linda Park (#1234)", action: "Consent captured", consentType: "Research", actor: "Research Coordinator" },
  { id: "e4", timestamp: "2026-03-12 16:45:00", patient: "Michael Chen (#1087)", action: "Scope updated", consentType: "AI Processing", actor: "Compliance Officer" },
  { id: "e5", timestamp: "2026-03-11 10:00:00", patient: "Maria Garcia (#1201)", action: "Consent captured", consentType: "Treatment", actor: "Dr. Patel" },
  { id: "e6", timestamp: "2026-03-10 08:30:00", patient: "David Kim (#1178)", action: "Expiration notice sent", consentType: "Data Sharing", actor: "System" },
  { id: "e7", timestamp: "2026-03-09 14:00:00", patient: "Emily Rodriguez (#1123)", action: "Consent reviewed", consentType: "Research", actor: "IRB Committee" },
  { id: "e8", timestamp: "2026-03-08 12:15:00", patient: "Robert Taylor (#1089)", action: "Consent expired", consentType: "AI Processing", actor: "System" },
];

const DEMO_FRAMEWORKS: Framework[] = [
  { key: "hipaa", name: "HIPAA", score: 94, controls: 78, passing: 73, failing: 3, pending: 2, lastAudit: "2026-02-15", nextReview: "2026-08-15", status: "Certified" },
  { key: "hitrust", name: "HITRUST CSF", score: 88, controls: 156, passing: 137, failing: 12, pending: 7, lastAudit: "2025-11-01", nextReview: "2026-05-01", status: "In Progress" },
  { key: "soc2", name: "SOC 2 Type II", score: 91, controls: 64, passing: 58, failing: 4, pending: 2, lastAudit: "2026-01-20", nextReview: "2026-07-20", status: "Certified" },
  { key: "gdpr", name: "GDPR", score: 86, controls: 52, passing: 45, failing: 4, pending: 3, lastAudit: "2025-12-10", nextReview: "2026-06-10", status: "In Progress" },
  { key: "state", name: "State Regulations", score: 96, controls: 42, passing: 40, failing: 1, pending: 1, lastAudit: "2026-03-01", nextReview: "2026-09-01", status: "Compliant" },
];

const DEMO_GAPS: GapItem[] = [
  { id: "g1", severity: "critical", framework: "HIPAA", description: "Two internal microservice connections still using TLS 1.2 instead of required TLS 1.3 for ePHI transmission.", recommendedAction: "Upgrade microservice TLS configurations and rotate certificates. Coordinate with DevOps for zero-downtime migration.", deadline: "2026-04-01" },
  { id: "g2", severity: "high", framework: "HITRUST", description: "Legacy audit endpoints not integrated with centralized logging system. 3 endpoints remain outside audit coverage.", recommendedAction: "Deploy audit middleware to legacy endpoints and verify log ingestion in SIEM. Update HITRUST control mapping.", deadline: "2026-04-15" },
  { id: "g3", severity: "high", framework: "HIPAA", description: "Treatment Recommender v1.2 model exceeds bias thresholds and has not been audited in 60+ days.", recommendedAction: "Immediately suspend model from production decisions. Retrain with debiased dataset and conduct full fairness audit.", deadline: "2026-03-30" },
  { id: "g4", severity: "medium", framework: "SOC 2", description: "Incident response playbook has not been tested via tabletop exercise in 6 months.", recommendedAction: "Schedule and execute tabletop exercise with all stakeholders. Document findings and update playbook.", deadline: "2026-05-01" },
  { id: "g5", severity: "medium", framework: "GDPR", description: "Data subject access request (DSAR) response time averaging 22 days against 30-day regulatory requirement.", recommendedAction: "Automate DSAR fulfillment pipeline. Add monitoring alerts at 15-day and 25-day thresholds.", deadline: "2026-05-15" },
  { id: "g6", severity: "low", framework: "SOC 2", description: "Employee security awareness training completion at 94% against 100% target.", recommendedAction: "Send reminder notifications to non-compliant staff. Escalate to department heads for persistent non-compliance.", deadline: "2026-06-01" },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

const statusBadge = (status: string) => {
  switch (status) {
    case "compliant":
    case "active":
      return "bg-green-50 text-green-700 border border-green-200";
    case "warning":
    case "review-needed":
    case "expired":
      return "bg-yellow-50 text-yellow-700 border border-yellow-200";
    case "non-compliant":
    case "revoked":
      return "bg-red-50 text-red-700 border border-red-200";
    default:
      return "bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700";
  }
};

const severityBadge = (severity: string) => {
  switch (severity) {
    case "critical":
      return "bg-red-100 text-red-800 border border-red-300";
    case "high":
      return "bg-orange-100 text-orange-800 border border-orange-300";
    case "medium":
      return "bg-yellow-100 text-yellow-800 border border-yellow-300";
    case "low":
      return "bg-blue-100 text-blue-800 border border-blue-300";
    default:
      return "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300 dark:border-gray-600";
  }
};

const scoreBadgeColor = (score: number) =>
  score > 90 ? "bg-green-100 text-green-800 border-green-300" : score >= 70 ? "bg-yellow-100 text-yellow-800 border-yellow-300" : "bg-red-100 text-red-800 border-red-300";

const scoreRingColor = (score: number) =>
  score > 90 ? "text-green-500" : score >= 70 ? "text-yellow-500" : "text-red-500";

const scoreTrackColor = (score: number) =>
  score > 90 ? "text-green-100" : score >= 70 ? "text-yellow-100" : "text-red-100";

// ── Component ───────────────────────────────────────────────────────────────

type TabKey = "hipaa" | "ai-governance" | "consent" | "reports";

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState<TabKey>("hipaa");
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [hipaaCategories, setHipaaCategories] = useState<HIPAACategory[]>(DEMO_HIPAA_CATEGORIES);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>(DEMO_AUDIT_LOG);
  const [aiModels, setAiModels] = useState<AIModel[]>(DEMO_AI_MODELS);
  const [driftResults, setDriftResults] = useState<DriftResult[]>(DEMO_DRIFT_RESULTS);
  const [consents, setConsents] = useState<ConsentRecord[]>(DEMO_CONSENTS);
  const [consentEvents, setConsentEvents] = useState<ConsentEvent[]>(DEMO_CONSENT_EVENTS);
  const [frameworks, setFrameworks] = useState<Framework[]>(DEMO_FRAMEWORKS);
  const [gaps, setGaps] = useState<GapItem[]>(DEMO_GAPS);
  const [auditingModel, setAuditingModel] = useState<string | null>(null);
  const [overallScore, setOverallScore] = useState(94);

  // Consent form state
  const [consentForm, setConsentForm] = useState({ patient: "", consentType: "Treatment", scope: "" });
  const [revokeForm, setRevokeForm] = useState({ consentId: "", reason: "" });
  const [showCaptureForm, setShowCaptureForm] = useState(false);
  const [showRevokeForm, setShowRevokeForm] = useState(false);

  // Report form state
  const [reportForm, setReportForm] = useState({ framework: "hipaa", startDate: "2026-01-01", endDate: "2026-03-15", scope: "full" });
  const [generatingReport, setGeneratingReport] = useState(false);
  const [runningGapAnalysis, setRunningGapAnalysis] = useState(false);

  // ── Data Fetching ─────────────────────────────────────────────────────────

  useEffect(() => {
    fetchHIPAAStatus()
      .then((data: Record<string, unknown>) => {
        if (data && typeof data === "object" && "score" in data) {
          setOverallScore(data.score as number);
        }
      })
      .catch(() => { /* use demo */ });

    fetchAIGovernanceModels()
      .then((data: Record<string, unknown>) => {
        if (data && Array.isArray((data as { models?: unknown }).models)) {
          setAiModels((data as { models: AIModel[] }).models);
        }
      })
      .catch(() => { /* use demo */ });

    fetchComplianceFrameworks()
      .then((data: Record<string, unknown>) => {
        if (Array.isArray(data)) {
          setFrameworks(data as Framework[]);
        } else if (data && Array.isArray((data as { frameworks?: unknown }).frameworks)) {
          setFrameworks((data as { frameworks: Framework[] }).frameworks);
        }
      })
      .catch(() => { /* use demo */ });

    fetchConsentAuditTrail()
      .then((data: Record<string, unknown>) => {
        if (data && Array.isArray((data as { events?: unknown }).events)) {
          setConsentEvents((data as { events: ConsentEvent[] }).events);
        }
      })
      .catch(() => { /* use demo */ });
  }, []);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleRunScan = useCallback(async () => {
    setScanning(true);
    setScanResult(null);
    try {
      const result = (await runHIPAAScan()) as unknown as ScanResult;
      if (result?.summary) {
        setScanResult(result);
        setOverallScore(Math.round(result.summary.compliance_rate));
        if (result.findings) {
          setHipaaCategories(result.findings.map((f) => ({
            id: f.control_id,
            name: f.title,
            status: f.status as HIPAACategory["status"] || (f.severity === "high" ? "non-compliant" : "warning"),
            description: f.description || f.title,
            remediation: f.remediation,
          })));
        }
      }
    } catch {
      const demoResult: ScanResult = {
        summary: { total_controls: 78, passed: 73, failed: 3, compliance_rate: 94.0 },
        findings: DEMO_HIPAA_CATEGORIES.map((c) => ({
          control_id: c.id, title: c.name, severity: c.status === "non-compliant" ? "high" : c.status === "warning" ? "medium" : "low",
          status: c.status, description: c.description, remediation: c.remediation,
        })),
        scan_timestamp: new Date().toISOString(),
      };
      setScanResult(demoResult);
      setOverallScore(94);
    } finally {
      setScanning(false);
    }
  }, []);

  const handleAuditModel = useCallback(async (modelName: string) => {
    setAuditingModel(modelName);
    try {
      await auditAIModel({ model_name: modelName });
    } catch {
      // demo mode
    } finally {
      setTimeout(() => setAuditingModel(null), 1500);
    }
  }, []);

  const handleCaptureConsent = useCallback(async () => {
    if (!consentForm.patient || !consentForm.scope) return;
    try {
      await captureConsent({ patient: consentForm.patient, consent_type: consentForm.consentType, scope: consentForm.scope });
    } catch {
      // demo mode
    }
    const newConsent: ConsentRecord = {
      id: `c${Date.now()}`,
      patient: consentForm.patient,
      consentType: consentForm.consentType,
      scope: consentForm.scope,
      status: "active",
      dateGranted: new Date().toISOString().slice(0, 10),
      dateRevoked: null,
    };
    setConsents((prev) => [newConsent, ...prev]);
    setConsentEvents((prev) => [{
      id: `e${Date.now()}`, timestamp: new Date().toISOString().replace("T", " ").slice(0, 19),
      patient: consentForm.patient, action: "Consent captured", consentType: consentForm.consentType, actor: "Compliance Officer",
    }, ...prev]);
    setConsentForm({ patient: "", consentType: "Treatment", scope: "" });
    setShowCaptureForm(false);
  }, [consentForm]);

  const handleRevokeConsent = useCallback(async () => {
    if (!revokeForm.consentId) return;
    try {
      await revokeConsent({ consent_id: revokeForm.consentId, reason: revokeForm.reason });
    } catch {
      // demo mode
    }
    setConsents((prev) => prev.map((c) => c.id === revokeForm.consentId ? { ...c, status: "revoked" as const, dateRevoked: new Date().toISOString().slice(0, 10) } : c));
    const target = consents.find((c) => c.id === revokeForm.consentId);
    if (target) {
      setConsentEvents((prev) => [{
        id: `e${Date.now()}`, timestamp: new Date().toISOString().replace("T", " ").slice(0, 19),
        patient: target.patient, action: "Consent revoked", consentType: target.consentType, actor: "Compliance Officer",
      }, ...prev]);
    }
    setRevokeForm({ consentId: "", reason: "" });
    setShowRevokeForm(false);
  }, [revokeForm, consents]);

  const handleGenerateReport = useCallback(async () => {
    setGeneratingReport(true);
    try {
      await generateComplianceReport({ framework: reportForm.framework, start_date: reportForm.startDate, end_date: reportForm.endDate, scope: reportForm.scope, format: "pdf" });
    } catch {
      // demo mode
    } finally {
      setTimeout(() => setGeneratingReport(false), 2000);
    }
  }, [reportForm]);

  const handleGapAnalysis = useCallback(async () => {
    setRunningGapAnalysis(true);
    try {
      const result = await runGapAnalysis({ framework: reportForm.framework });
      if (result && Array.isArray((result as { gaps?: unknown }).gaps)) {
        setGaps((result as { gaps: GapItem[] }).gaps);
      }
    } catch {
      // use demo gaps
    } finally {
      setTimeout(() => setRunningGapAnalysis(false), 1500);
    }
  }, [reportForm.framework]);

  // ── KPI calculations ──────────────────────────────────────────────────────

  const activeConsents = consents.filter((c) => c.status === "active").length;
  const openFindings = gaps.filter((g) => g.severity === "critical" || g.severity === "high").length;
  const frameworksCovered = frameworks.length;

  // ── Circular Score Indicator ──────────────────────────────────────────────

  const CircularScore = ({ score, size = 160 }: { score: number; size?: number }) => {
    const radius = (size - 16) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    return (
      <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={12} className={`stroke-current ${scoreTrackColor(score)}`} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={12} strokeLinecap="round"
            className={`stroke-current ${scoreRingColor(score)} transition-all duration-1000 ease-out`}
            strokeDasharray={circumference} strokeDashoffset={offset} />
        </svg>
        <div className="absolute flex flex-col items-center">
          <span className={`text-2xl sm:text-4xl font-bold ${score > 90 ? "text-green-600" : score >= 70 ? "text-yellow-600" : "text-red-600"}`}>{score}%</span>
          <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">HIPAA Score</span>
        </div>
      </div>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const tabs: { key: TabKey; label: string }[] = [
    { key: "hipaa", label: "HIPAA Compliance" },
    { key: "ai-governance", label: "AI Governance" },
    { key: "consent", label: "Consent Management" },
    { key: "reports", label: "Reports & Frameworks" },
  ];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Compliance &amp; Governance</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">HIPAA monitoring, AI governance, consent management, and regulatory reporting</p>
          </div>
          <span className={`ml-2 rounded-full px-3 py-1 text-sm font-bold border ${scoreBadgeColor(overallScore)}`}>
            {overallScore}%
          </span>
        </div>
        <button onClick={handleRunScan} disabled={scanning}
          className="rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 flex items-center gap-2 transition-colors">
          {scanning && (
            <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
          {scanning ? "Scanning..." : "Run HIPAA Scan"}
        </button>
      </div>

      {/* ── Stats Bar ───────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5 animate-fade-in-up">
        {[
          { label: "HIPAA Score", value: `${overallScore}%`, color: overallScore > 90 ? "text-green-600" : overallScore >= 70 ? "text-yellow-600" : "text-red-600", icon: (
            <svg className="h-5 w-5 text-healthos-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>
          ) },
          { label: "AI Models Monitored", value: String(aiModels.length), color: "text-blue-600", icon: (
            <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21a48.25 48.25 0 01-8.135-.687c-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg>
          ) },
          { label: "Active Consents", value: String(activeConsents), color: "text-emerald-600", icon: (
            <svg className="h-5 w-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" /></svg>
          ) },
          { label: "Open Findings", value: String(openFindings), color: openFindings > 3 ? "text-red-600" : "text-yellow-600", icon: (
            <svg className="h-5 w-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
          ) },
          { label: "Frameworks Covered", value: String(frameworksCovered), color: "text-purple-600", icon: (
            <svg className="h-5 w-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" /></svg>
          ) },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-2">{kpi.icon}</div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{kpi.label}</p>
                <p className={`text-2xl font-bold ${kpi.color}`}>{kpi.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Tabs ────────────────────────────────────────────────────────────── */}
      <div className="flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-1 overflow-x-auto w-fit">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === t.key ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab 1: HIPAA Compliance ─────────────────────────────────────────── */}
      {activeTab === "hipaa" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Score + Scan Button Row */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="card card-hover flex flex-col items-center justify-center py-8">
              <CircularScore score={overallScore} />
              <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Overall HIPAA Compliance</p>
              {scanResult && (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {scanResult.summary.passed} of {scanResult.summary.total_controls} controls passing
                </p>
              )}
              <button onClick={handleRunScan} disabled={scanning}
                className="mt-4 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 flex items-center gap-2">
                {scanning && (
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                {scanning ? "Scanning..." : "Run Scan"}
              </button>
            </div>

            <div className="lg:col-span-2 space-y-3">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Compliance Categories</h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {hipaaCategories.map((cat) => (
                  <div key={cat.id} className="card card-hover">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{cat.name}</h4>
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge(cat.status)}`}>
                        {cat.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed mb-2">{cat.description}</p>
                    {cat.status !== "compliant" && (
                      <div className="rounded-lg bg-amber-50 border border-amber-200 p-2 mt-2">
                        <p className="text-xs font-medium text-amber-800">Remediation</p>
                        <p className="text-xs text-amber-700 mt-0.5">{cat.remediation}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Audit Log Table */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Recent Audit Log</h3>
            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Timestamp</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">User</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Resource</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
                    {auditLog.map((entry) => (
                      <tr key={entry.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{entry.timestamp}</td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{entry.action}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{entry.user}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{entry.resource}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            entry.outcome.includes("Passed") || entry.outcome.includes("No Incidents") || entry.outcome.includes("Approved")
                              ? "bg-green-50 text-green-700"
                              : entry.outcome.includes("Blocked") || entry.outcome.includes("Failed")
                                ? "bg-red-50 text-red-700"
                                : "bg-blue-50 text-blue-700"
                          }`}>
                            {entry.outcome}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 2: AI Governance ────────────────────────────────────────────── */}
      {activeTab === "ai-governance" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Model Registry */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">AI Model Registry</h3>
            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Model Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Last Audit</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Fairness Score</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Bias Indicators</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
                    {aiModels.map((model) => (
                      <tr key={model.name} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{model.name}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.type}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge(model.status)}`}>
                            {model.status.replace(/-/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.lastAudit}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-16 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                              <div className={`h-full rounded-full ${model.fairnessScore >= 0.85 ? "bg-green-400" : model.fairnessScore >= 0.7 ? "bg-yellow-400" : "bg-red-400"}`}
                                style={{ width: `${model.fairnessScore * 100}%` }} />
                            </div>
                            <span className={`text-xs font-medium ${model.fairnessScore >= 0.85 ? "text-green-600" : model.fairnessScore >= 0.7 ? "text-yellow-600" : "text-red-600"}`}>
                              {(model.fairnessScore * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            {model.biasIndicators.map((bi) => (
                              <span key={bi.metric} className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${bi.pass ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}
                                title={`${bi.metric}: ${bi.value.toFixed(2)} (threshold: ${bi.threshold})`}>
                                {bi.metric.split(" ").map((w) => w[0]).join("")} {bi.pass ? "OK" : "FAIL"}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <button onClick={() => handleAuditModel(model.name)} disabled={auditingModel === model.name}
                            className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 flex items-center gap-1.5">
                            {auditingModel === model.name && (
                              <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                              </svg>
                            )}
                            {auditingModel === model.name ? "Auditing..." : "Audit Model"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>

          {/* Drift Check Results */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Drift Check Results</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {driftResults.map((drift) => (
                <div key={drift.modelName} className="card card-hover">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{drift.modelName}</h4>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      drift.status === "stable" ? "bg-green-50 text-green-700 border border-green-200" :
                      drift.status === "warning" ? "bg-yellow-50 text-yellow-700 border border-yellow-200" :
                      "bg-red-50 text-red-700 border border-red-200"
                    }`}>{drift.status}</span>
                  </div>
                  <div className="space-y-2">
                    {[
                      { label: "Feature Drift", value: drift.featureDrift, threshold: 0.15 },
                      { label: "Prediction Drift", value: drift.predictionDrift, threshold: 0.1 },
                      { label: "Data Quality", value: drift.dataQuality, threshold: 0.9, invert: true },
                    ].map((m) => (
                      <div key={m.label}>
                        <div className="flex items-center justify-between text-xs mb-0.5">
                          <span className="text-gray-500 dark:text-gray-400">{m.label}</span>
                          <span className={`font-medium ${
                            m.invert
                              ? (m.value >= m.threshold ? "text-green-600" : "text-red-600")
                              : (m.value <= m.threshold ? "text-green-600" : m.value <= m.threshold * 1.5 ? "text-yellow-600" : "text-red-600")
                          }`}>{m.invert ? `${(m.value * 100).toFixed(0)}%` : m.value.toFixed(3)}</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${
                            m.invert
                              ? (m.value >= m.threshold ? "bg-green-400" : "bg-red-400")
                              : (m.value <= m.threshold ? "bg-green-400" : m.value <= m.threshold * 1.5 ? "bg-yellow-400" : "bg-red-400")
                          }`} style={{ width: m.invert ? `${m.value * 100}%` : `${Math.min(m.value / (m.threshold * 2), 1) * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 3: Consent Management ──────────────────────────────────────── */}
      {activeTab === "consent" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={() => { setShowCaptureForm(!showCaptureForm); setShowRevokeForm(false); }}
              className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
              Capture Consent
            </button>
            <button onClick={() => { setShowRevokeForm(!showRevokeForm); setShowCaptureForm(false); }}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50">
              Revoke Consent
            </button>
          </div>

          {/* Capture Consent Form */}
          {showCaptureForm && (
            <div className="card animate-fade-in-up border-2 border-healthos-200">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Capture New Consent</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient</label>
                  <input type="text" value={consentForm.patient} onChange={(e) => setConsentForm((p) => ({ ...p, patient: e.target.value }))}
                    placeholder="Patient name or ID" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Consent Type</label>
                  <select value={consentForm.consentType} onChange={(e) => setConsentForm((p) => ({ ...p, consentType: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none">
                    <option>Treatment</option>
                    <option>AI Processing</option>
                    <option>Research</option>
                    <option>Data Sharing</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Scope</label>
                  <input type="text" value={consentForm.scope} onChange={(e) => setConsentForm((p) => ({ ...p, scope: e.target.value }))}
                    placeholder="Scope description" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none" />
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <button onClick={handleCaptureConsent} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">Submit</button>
                <button onClick={() => setShowCaptureForm(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
              </div>
            </div>
          )}

          {/* Revoke Consent Form */}
          {showRevokeForm && (
            <div className="card animate-fade-in-up border-2 border-red-200">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Revoke Consent</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Consent ID</label>
                  <select value={revokeForm.consentId} onChange={(e) => setRevokeForm((p) => ({ ...p, consentId: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none">
                    <option value="">Select consent...</option>
                    {consents.filter((c) => c.status === "active").map((c) => (
                      <option key={c.id} value={c.id}>{c.patient} - {c.consentType}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Reason</label>
                  <input type="text" value={revokeForm.reason} onChange={(e) => setRevokeForm((p) => ({ ...p, reason: e.target.value }))}
                    placeholder="Reason for revocation" className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none" />
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <button onClick={handleRevokeConsent} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Revoke</button>
                <button onClick={() => setShowRevokeForm(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
              </div>
            </div>
          )}

          {/* Active Consents Table */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Active Consents</h3>
            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Patient</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Consent Type</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Scope</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Date Granted</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Date Revoked</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
                    {consents.map((consent) => (
                      <tr key={consent.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{consent.patient}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{consent.consentType}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 max-w-[200px] truncate">{consent.scope}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge(consent.status)}`}>
                            {consent.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{consent.dateGranted}</td>
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{consent.dateRevoked || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>

          {/* Consent Audit Trail Timeline */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Consent Audit Trail</h3>
            <div className="card">
              <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />
                <div className="space-y-6">
                  {consentEvents.map((event, i) => (
                    <div key={event.id} className="relative flex gap-4 pl-10">
                      <div className={`absolute left-2.5 top-1 h-3 w-3 rounded-full border-2 border-white ${
                        event.action.includes("revoked") ? "bg-red-400" :
                        event.action.includes("expired") ? "bg-gray-400" :
                        event.action.includes("captured") || event.action.includes("renewed") ? "bg-green-400" :
                        "bg-blue-400"
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{event.action}</span>
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                            event.action.includes("revoked") ? "bg-red-50 text-red-700" :
                            event.action.includes("expired") ? "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400" :
                            event.action.includes("captured") || event.action.includes("renewed") ? "bg-green-50 text-green-700" :
                            "bg-blue-50 text-blue-700"
                          }`}>{event.consentType}</span>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">{event.patient}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{event.timestamp} &middot; {event.actor}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 4: Reports & Frameworks ────────────────────────────────────── */}
      {activeTab === "reports" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Compliance Frameworks */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Compliance Frameworks</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {frameworks.map((fw) => (
                <div key={fw.key} className="card card-hover">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{fw.name}</h4>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      fw.status === "Certified" ? "bg-green-50 text-green-700 border border-green-200" :
                      fw.status === "Compliant" ? "bg-blue-50 text-blue-700 border border-blue-200" :
                      "bg-yellow-50 text-yellow-700 border border-yellow-200"
                    }`}>{fw.status}</span>
                  </div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`text-2xl font-bold ${fw.score > 90 ? "text-green-600" : fw.score >= 70 ? "text-yellow-600" : "text-red-600"}`}>{fw.score}%</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">coverage</span>
                  </div>
                  <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden mb-2">
                    <div className={`h-full rounded-full ${fw.score > 90 ? "bg-green-400" : fw.score >= 70 ? "bg-yellow-400" : "bg-red-400"}`}
                      style={{ width: `${fw.score}%` }} />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-1 text-[11px] text-gray-500 dark:text-gray-400">
                    <span>{fw.passing} passing</span>
                    <span>{fw.failing} failing</span>
                    <span>{fw.pending} pending</span>
                  </div>
                  <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400 flex justify-between">
                    <span>Last: {fw.lastAudit}</span>
                    <span>Next: {fw.nextReview}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Generate Report Form */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Generate Compliance Report</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Framework</label>
                <select value={reportForm.framework} onChange={(e) => setReportForm((p) => ({ ...p, framework: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none">
                  {frameworks.map((fw) => (
                    <option key={fw.key} value={fw.key}>{fw.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Start Date</label>
                <input type="date" value={reportForm.startDate} onChange={(e) => setReportForm((p) => ({ ...p, startDate: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">End Date</label>
                <input type="date" value={reportForm.endDate} onChange={(e) => setReportForm((p) => ({ ...p, endDate: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Scope</label>
                <select value={reportForm.scope} onChange={(e) => setReportForm((p) => ({ ...p, scope: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none">
                  <option value="full">Full Organization</option>
                  <option value="clinical">Clinical Systems</option>
                  <option value="it">IT Infrastructure</option>
                  <option value="ai">AI/ML Systems</option>
                </select>
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              <button onClick={handleGenerateReport} disabled={generatingReport}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 flex items-center gap-2">
                {generatingReport && (
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                {generatingReport ? "Generating..." : "Generate Report"}
              </button>
              <button onClick={handleGapAnalysis} disabled={runningGapAnalysis}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 flex items-center gap-2">
                {runningGapAnalysis && (
                  <svg className="animate-spin h-4 w-4 text-gray-500 dark:text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                {runningGapAnalysis ? "Analyzing..." : "Run Gap Analysis"}
              </button>
            </div>
          </div>

          {/* Gap Analysis Results */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Gap Analysis Results</h3>
            <div className="space-y-3">
              {gaps.map((gap) => (
                <div key={gap.id} className="card card-hover">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${severityBadge(gap.severity)}`}>
                        {gap.severity}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{gap.framework}</span>
                        <span className="text-xs text-gray-300">&middot;</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">Deadline: {gap.deadline}</span>
                      </div>
                      <p className="text-sm text-gray-900 dark:text-gray-100 leading-relaxed">{gap.description}</p>
                      <div className="mt-2 rounded-lg bg-blue-50 border border-blue-200 p-2">
                        <p className="text-xs font-medium text-blue-800">Recommended Action</p>
                        <p className="text-xs text-blue-700 mt-0.5">{gap.recommendedAction}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
