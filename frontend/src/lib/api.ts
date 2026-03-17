const API_PREFIX = "/api/v1";

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_PREFIX}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...options?.headers,
    },
    ...options,
  });

  if (res.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ── User Profile ──────────────────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id: string;
  avatar_url: string | null;
  phone: string | null;
  profile: Record<string, unknown>;
  mfa_enabled: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface MFASetup {
  secret: string;
  provisioning_uri: string;
}

export async function fetchMyProfile() {
  return request<UserProfile>("/users/me");
}

export async function updateMyProfile(body: {
  full_name?: string;
  email?: string;
  phone?: string;
  profile?: Record<string, unknown>;
}) {
  return request<UserProfile>("/users/me", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function uploadAvatar(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const url = `${API_PREFIX}/users/me/avatar`;
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const res = await fetch(url, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (res.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json() as Promise<UserProfile>;
}

export async function deleteAvatar() {
  return request<UserProfile>("/users/me/avatar", { method: "DELETE" });
}

export async function changePassword(body: { current_password: string; new_password: string }) {
  return request<{ message: string }>("/users/me/change-password", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function setupMFA() {
  return request<MFASetup>("/users/me/mfa/setup", { method: "POST" });
}

export async function verifyMFA(code: string) {
  return request<{ message: string }>("/users/me/mfa/verify", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function disableMFA(code: string) {
  return request<{ message: string }>("/users/me/mfa/disable", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function deleteMyAccount() {
  return request<{ message: string }>("/users/me", { method: "DELETE" });
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardSummary {
  active_patients: number;
  vitals_today: number;
  open_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  agent_decisions: number;
}

export async function fetchDashboardSummary() {
  return request<DashboardSummary>("/dashboard/summary");
}

// ── Patients ─────────────────────────────────────────────────────────────────

export interface PatientData {
  id: string;
  mrn: string | null;
  demographics: Record<string, unknown>;
  conditions: Array<Record<string, unknown>>;
  medications: Array<Record<string, unknown>>;
  risk_level: string;
  created_at: string;
  updated_at: string;
}

export interface PatientListResponse {
  patients: PatientData[];
  total: number;
  page: number;
  page_size: number;
}

export async function fetchPatients(params?: { risk_level?: string; search?: string; page?: number }) {
  const query = new URLSearchParams();
  if (params?.risk_level) query.set("risk_level", params.risk_level);
  if (params?.search) query.set("search", params.search);
  if (params?.page) query.set("page", String(params.page));
  const qs = query.toString();
  return request<PatientListResponse>(`/patients${qs ? `?${qs}` : ""}`);
}

export async function fetchPatient(id: string) {
  return request<PatientData>(`/patients/${id}`);
}

export interface PatientCreatePayload {
  mrn?: string;
  demographics: Record<string, unknown>;
  conditions?: Array<Record<string, unknown>>;
  medications?: Array<Record<string, unknown>>;
}

export async function createPatient(data: PatientCreatePayload) {
  return request<PatientData>("/patients", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Vitals ───────────────────────────────────────────────────────────────────

export interface VitalData {
  id: string;
  patient_id: string;
  vital_type: string;
  value: Record<string, unknown>;
  unit: string;
  recorded_at: string;
  source: string | null;
  quality_score: number | null;
  created_at: string;
}

export async function fetchVitals(patientId: string, vitalType?: string) {
  const query = new URLSearchParams();
  if (vitalType) query.set("vital_type", vitalType);
  const qs = query.toString();
  return request<VitalData[]>(`/vitals/${patientId}${qs ? `?${qs}` : ""}`);
}

// ── Risk Score ───────────────────────────────────────────────────────────────

export interface RiskScoreData {
  score: number;
  risk_level: string;
  factors: Array<Record<string, unknown>>;
  recommendations: string[];
}

export async function fetchRiskScore(patientId: string) {
  return request<RiskScoreData>(`/patients/${patientId}/risk-score`);
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export interface AlertData {
  id: string;
  patient_id: string;
  alert_type: string;
  priority: string;
  status: string;
  message: string | null;
  created_at: string;
  acknowledged_at: string | null;
}

export async function fetchAlerts(params?: {
  status?: string;
  priority?: string;
  patient_id?: string;
}) {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.priority) query.set("priority", params.priority);
  if (params?.patient_id) query.set("patient_id", params.patient_id);
  const qs = query.toString();
  return request<AlertData[]>(`/alerts${qs ? `?${qs}` : ""}`);
}

export async function acknowledgeAlert(alertId: string) {
  return request<AlertData>(`/alerts/${alertId}/acknowledge`, { method: "POST" });
}

export async function resolveAlert(alertId: string) {
  return request<AlertData>(`/alerts/${alertId}/resolve`, { method: "POST" });
}

export async function createTelehealthSession(body: Record<string, unknown>) {
  return request<TelehealthSession>("/telehealth/sessions", { method: "POST", body: JSON.stringify(body) });
}

// ── Agents ───────────────────────────────────────────────────────────────────

export interface AgentAuditEntry {
  id: string;
  agent_name: string;
  action: string;
  patient_id: string | null;
  confidence_score: number | null;
  created_at: string;
}

export async function fetchAgents() {
  return request<{ agents: unknown[] }>("/agents");
}

export async function fetchRecentAgentActivity() {
  return request<AgentAuditEntry[]>("/dashboard/agent-activity");
}

// ── Agent Activity (detailed) ────────────────────────────────────────────────

export interface AgentExecutionEntry {
  id: string;
  agent_name: string;
  action: string;
  status: string;
  confidence_score: number | null;
  duration_ms: number | null;
  patient_id: string | null;
  trace_id: string;
  created_at: string | null;
}

export interface PipelineRunEntry {
  trace_id: string;
  agents_executed: string[];
  total_duration_ms: number;
  trigger_event: string;
  started_at: string | null;
}

export interface AgentActivityResponse {
  executions: AgentExecutionEntry[];
  pipeline_runs: PipelineRunEntry[];
  agent_statuses: Record<string, string>;
}

export async function fetchAgentActivity(limit = 10) {
  return request<AgentActivityResponse>(`/agents/activity?limit=${limit}`);
}

// ── Health ───────────────────────────────────────────────────────────────────

export interface HealthStatus {
  status: string;
  version: string;
  environment: string;
}

export async function fetchHealth() {
  const res = await fetch("/health");
  if (!res.ok) throw new Error("Health check failed");
  return res.json() as Promise<HealthStatus>;
}

// ── Telehealth ──────────────────────────────────────────────────────────────

export interface TelehealthSession {
  session_id: string;
  patient_id: string;
  visit_type: string;
  urgency: string;
  status: string;
  estimated_wait_minutes?: number;
  chief_complaint?: string;
  patient_name?: string;
  created_at: string;
}

export async function fetchTelehealthSessions() {
  return request<{ sessions: TelehealthSession[] }>("/telehealth/sessions");
}

export async function fetchTelehealthSession(sessionId: string) {
  return request<TelehealthSession>(`/telehealth/sessions/${sessionId}`);
}

export async function prepareVisit(sessionId: string) {
  return request<Record<string, unknown>>(`/telehealth/sessions/${sessionId}/prepare`, {
    method: "POST",
  });
}

export async function generateClinicalNote(sessionId: string, body: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/telehealth/sessions/${sessionId}/note`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function generateFollowUp(sessionId: string, body: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/telehealth/sessions/${sessionId}/follow-up`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface ClinicalNoteSection {
  section: string;
  content: string;
  confidence?: number;
}

export interface ClinicalNote {
  note_id: string;
  session_id: string;
  status: "draft" | "pending_review" | "signed";
  sections: ClinicalNoteSection[];
  generated_at: string;
  generated_by: string;
  signed_at?: string;
  signed_by?: string;
  amendments?: { section: string; content: string; amended_at: string }[];
  overall_confidence?: number;
}

export async function fetchClinicalNotes(sessionId: string) {
  return request<{ notes: ClinicalNote[] }>(`/telehealth/sessions/${sessionId}/notes`);
}

export async function signClinicalNote(
  sessionId: string,
  noteId: string,
  amendments?: string,
) {
  return request<ClinicalNote>(`/telehealth/sessions/${sessionId}/note/sign`, {
    method: "POST",
    body: JSON.stringify({ note_id: noteId, amendments }),
  });
}

export async function amendClinicalNote(
  sessionId: string,
  noteId: string,
  amendments: { section: string; content: string }[],
) {
  return request<ClinicalNote>(`/telehealth/sessions/${sessionId}/note`, {
    method: "PUT",
    body: JSON.stringify({ note_id: noteId, amendments }),
  });
}

// ── Telehealth Video ────────────────────────────────────────────────────────

export async function startVideoSession(sessionId: string) {
  return request<Record<string, unknown>>(`/telehealth/sessions/${sessionId}/video/start`, { method: "POST", body: JSON.stringify({}) });
}

export async function getVideoToken(sessionId: string, role: string = "participant") {
  return request<Record<string, unknown>>(`/telehealth/sessions/${sessionId}/video/token?role=${role}`);
}

export async function endVideoSession(sessionId: string) {
  return request<Record<string, unknown>>(`/telehealth/sessions/${sessionId}/video/end`, { method: "POST", body: JSON.stringify({}) });
}

// ── FHIR ─────────────────────────────────────────────────────────────────────

export async function fetchFHIRPatient(patientId: string) {
  return request<unknown>(`/fhir/r4/Patient/${patientId}`);
}

// ── RPM (Remote Patient Monitoring) ──────────────────────────────────────────

export interface RPMDashboard {
  active_patients: number;
  critical_alerts: number;
  devices_online: number;
  avg_adherence: number;
  patient_id?: string;
  latest_vitals?: Record<string, unknown>;
  risk_score?: Record<string, unknown>;
  active_alerts?: unknown[];
  adherence?: Record<string, unknown>;
  trends?: unknown[];
}

export async function fetchRPMDashboard(patientId?: string) {
  const path = patientId ? `/rpm/dashboard/${patientId}` : "/rpm/dashboard/summary";
  return request<RPMDashboard>(path);
}

export async function ingestRPMData(patientId: string, vitals: Record<string, unknown>[]) {
  return request<Record<string, unknown>>(`/rpm/ingest?patient_id=${patientId}`, {
    method: "POST",
    body: JSON.stringify(vitals),
  });
}

// ── Imaging & Radiology ──────────────────────────────────────────────────────

export interface ImagingStudy {
  study_id: string;
  patient_id: string;
  modality: string;
  body_part: string;
  description: string;
  status: string;
  date: string;
  radiologist?: string;
}

export interface AIAnalysis {
  study_id: string;
  model: string;
  finding: string;
  confidence: number;
  severity: string;
  action: string;
}

export async function fetchImagingStudies(patientId: string) {
  return request<ImagingStudy[]>(`/imaging/studies/${patientId}`);
}

export async function analyzeImage(body: Record<string, unknown>) {
  return request<AIAnalysis>("/imaging/analysis/analyze", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchImagingWorklist() {
  return request<Record<string, unknown>>("/imaging/workflow/worklist");
}

export async function evaluateCriticalFinding(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/imaging/critical/evaluate", { method: "POST", body: JSON.stringify(body) });
}

// ── Labs & Pathology ─────────────────────────────────────────────────────────

export interface LabResult {
  test: string;
  value: number;
  unit: string;
  reference_range: string;
  flag: string;
  date: string;
}

export interface LabOrder {
  id: string;
  patient_id: string;
  panels: string[];
  priority: string;
  status: string;
  ordered_date: string;
  provider: string;
}

export async function createLabOrder(body: Record<string, unknown>) {
  return request<LabOrder>("/labs/orders/create", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchLabOrderStatus(orderId: string) {
  return request<LabOrder>(`/labs/orders/${orderId}/status`);
}

export async function receiveLabResults(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/labs/results/ingest", { method: "POST", body: JSON.stringify(body) });
}

export async function interpretLabResults(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/labs/results/flag-abnormals", { method: "POST", body: JSON.stringify(body) });
}

export async function analyzeLabTrends(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/labs/trends/analyze", { method: "POST", body: JSON.stringify(body) });
}

export async function evaluateCriticalLabValue(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/labs/critical/evaluate", { method: "POST", body: JSON.stringify(body) });
}

// ── Pharmacy ─────────────────────────────────────────────────────────────────

export async function createPrescription(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/pharmacy/prescriptions/create", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchPrescriptionHistory(patientId: string) {
  return request<Record<string, unknown>[]>(`/pharmacy/prescriptions/history/${patientId}`);
}

export async function checkDrugInteractions(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/pharmacy/interactions/check", { method: "POST", body: JSON.stringify(body) });
}

export async function checkFormulary(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/pharmacy/formulary/check", { method: "POST", body: JSON.stringify(body) });
}

export async function trackMedicationAdherence(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/pharmacy/adherence/calculate", { method: "POST", body: JSON.stringify(body) });
}

export async function processRefill(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/pharmacy/refills/initiate", { method: "POST", body: JSON.stringify(body) });
}

// ── RCM (Revenue Cycle Management) ───────────────────────────────────────────

export async function captureCharges(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/rcm/charges/capture", { method: "POST", body: JSON.stringify(body) });
}

export async function optimizeClaim(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/rcm/claims/optimize", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchCleanClaimRate() {
  return request<Record<string, unknown>>("/rcm/claims/clean-rate");
}

export async function analyzeDenial(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/rcm/denials/analyze", { method: "POST", body: JSON.stringify(body) });
}

export async function appealDenial(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/rcm/denials/appeal", { method: "POST", body: JSON.stringify(body) });
}

export async function verifyRevenueIntegrity(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/rcm/integrity/scan", { method: "POST", body: JSON.stringify(body) });
}

// ── Mental Health & Behavioral ───────────────────────────────────────────────

export async function submitPHQ9Screening(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/mental-health/screening/phq9", { method: "POST", body: JSON.stringify(body) });
}

export async function submitGAD7Screening(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/mental-health/screening/gad7", { method: "POST", body: JSON.stringify(body) });
}

export async function detectCrisis(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/mental-health/crisis/assess", { method: "POST", body: JSON.stringify(body) });
}

export async function submitTherapeuticEngagement(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/mental-health/engagement/mood-check", { method: "POST", body: JSON.stringify(body) });
}

export async function createSafetyPlan(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/mental-health/crisis/safety-plan", { method: "POST", body: JSON.stringify(body) });
}

// ── Compliance & Governance ──────────────────────────────────────────────────

export async function runHIPAAScan(body?: Record<string, unknown>) {
  return request<Record<string, unknown>>("/compliance/hipaa/scan", { method: "POST", body: JSON.stringify(body ?? {}) });
}

export async function fetchHIPAAStatus() {
  return request<Record<string, unknown>>("/compliance/hipaa/status");
}

export async function fetchAIGovernanceModels() {
  return request<Record<string, unknown>>("/compliance/ai-governance/models");
}

export async function auditAIModel(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/compliance/ai-governance/audit", { method: "POST", body: JSON.stringify(body) });
}

export async function captureConsent(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/compliance/consent/capture", { method: "POST", body: JSON.stringify(body) });
}

export async function revokeConsent(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/compliance/consent/revoke", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchConsentAuditTrail() {
  return request<Record<string, unknown>>("/compliance/consent/audit-trail");
}

export async function fetchComplianceFrameworks() {
  return request<Record<string, unknown>>("/compliance/frameworks");
}

export async function generateComplianceReport(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/compliance/reports/generate", { method: "POST", body: JSON.stringify(body) });
}

export async function runGapAnalysis(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/compliance/reports/gap-analysis", { method: "POST", body: JSON.stringify(body) });
}

// ── Patient Engagement & SDOH ────────────────────────────────────────────────

export async function triageSymptoms(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/patient-engagement/triage/assess", { method: "POST", body: JSON.stringify(body) });
}

export async function navigateCare(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/patient-engagement/navigation/create-journey", { method: "POST", body: JSON.stringify(body) });
}

export async function screenSDOH(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/patient-engagement/sdoh/screen", { method: "POST", body: JSON.stringify(body) });
}

export async function findCommunityResources(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/patient-engagement/resources/find", { method: "POST", body: JSON.stringify(body) });
}

export async function submitMotivationalEngagement(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/patient-engagement/engagement/nudge", { method: "POST", body: JSON.stringify(body) });
}

// ── Ambient AI Documentation ─────────────────────────────────────────────────

export async function startAmbientSession(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ambient-ai/session/start", { method: "POST", body: JSON.stringify(body) });
}

export async function endAmbientSession(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ambient-ai/session/end", { method: "POST", body: JSON.stringify(body) });
}

export async function generateSOAPNote(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ambient-ai/soap/generate", { method: "POST", body: JSON.stringify(body) });
}

export async function validateSOAPNote(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ambient-ai/soap/validate", { method: "POST", body: JSON.stringify(body) });
}

export async function codeEncounter(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ambient-ai/coding/encounter", { method: "POST", body: JSON.stringify(body) });
}

export async function submitAttestation(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ambient-ai/attestation/submit", { method: "POST", body: JSON.stringify(body) });
}

export async function approveAttestation(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ambient-ai/attestation/approve", { method: "POST", body: JSON.stringify(body) });
}

// ── Digital Twin & Simulation ────────────────────────────────────────────────

export async function buildDigitalTwin(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/digital-twin/twin/build", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchTwinState(patientId: string) {
  return request<Record<string, unknown>>(`/digital-twin/twin/state?patient_id=${patientId}`);
}

export async function simulateScenario(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/digital-twin/scenario/medication", { method: "POST", body: JSON.stringify(body) });
}

export async function predictTrajectory(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/digital-twin/trajectory/forecast", { method: "POST", body: JSON.stringify(body) });
}

export async function recommendTreatment(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/digital-twin/optimize/plan", { method: "POST", body: JSON.stringify(body) });
}

// ── Research & Genomics ──────────────────────────────────────────────────────

export async function matchClinicalTrials(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/research-genomics/trials/match", { method: "POST", body: JSON.stringify(body) });
}

export async function checkTrialEligibility(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/research-genomics/trials/eligibility", { method: "POST", body: JSON.stringify(body) });
}

export async function deidentifyDataset(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/research-genomics/deidentify/dataset", { method: "POST", body: JSON.stringify(body) });
}

export async function assessGeneticRisk(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/research-genomics/genetic/prs", { method: "POST", body: JSON.stringify(body) });
}

export async function analyzePharmacogenomics(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/research-genomics/pgx/check", { method: "POST", body: JSON.stringify(body) });
}

// ── Analytics ────────────────────────────────────────────────────────────────

export async function analyzePopulationHealth(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/population-health", { method: "POST", body: JSON.stringify(body) });
}

export async function riskStratification(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/population-health/risk-stratification", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchQualityMetrics(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/population-health/quality-metrics", { method: "POST", body: JSON.stringify(body) });
}

export async function trackOutcomes(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/outcomes", { method: "POST", body: JSON.stringify(body) });
}

export async function analyzeCosts(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/costs", { method: "POST", body: JSON.stringify(body) });
}

export async function createCohort(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/cohorts", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchCohortTemplates() {
  return request<Record<string, unknown>>("/analytics/cohorts/templates");
}

export async function predictReadmissionRisk(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/readmission-risk", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchExecutiveSummary() {
  return request<Record<string, unknown>>("/analytics/executive/summary");
}

export async function fetchKPIScorecard(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/executive/scorecard", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchTrendDigest() {
  return request<Record<string, unknown>>("/analytics/executive/trends");
}

export async function fetchCostDrivers(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/cost-risk/drivers", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchOpportunities(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/cost-risk/opportunities", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchRiskDistribution(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/analytics/population-health/risk-stratification", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchPopulationKPIs() {
  return request<Record<string, unknown>>("/analytics/population-health/kpis");
}

// ── Operations ───────────────────────────────────────────────────────────────

export async function evaluatePriorAuth(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/operations/prior-auth/evaluate", { method: "POST", body: JSON.stringify(body) });
}

export async function verifyInsurance(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/operations/insurance/verify", { method: "POST", body: JSON.stringify(body) });
}

export async function createReferral(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/operations/referrals/create", { method: "POST", body: JSON.stringify(body) });
}

export async function scheduleAppointment(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/operations/schedule/suggest", { method: "POST", body: JSON.stringify(body) });
}

// ── AI Marketplace ──────────────────────────────────────────────────────────

export async function fetchMarketplaceAgents() {
  return request<Record<string, unknown>>("/marketplace/agents");
}

export async function fetchMarketplaceAgent(agentId: string) {
  return request<Record<string, unknown>>(`/marketplace/agents/${agentId}`);
}

export async function publishMarketplaceAgent(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/marketplace/agents/publish", { method: "POST", body: JSON.stringify(body) });
}

export async function installMarketplaceAgent(agentId: string) {
  return request<Record<string, unknown>>(`/marketplace/agents/${agentId}/install`, { method: "POST", body: JSON.stringify({}) });
}

export async function scanMarketplaceAgent(agentId: string) {
  return request<Record<string, unknown>>(`/marketplace/agents/${agentId}/scan`, { method: "POST", body: JSON.stringify({}) });
}

export async function fetchMarketplaceAnalytics() {
  return request<Record<string, unknown>>("/marketplace/analytics");
}

// ── Clinical RAG Intelligence ─────────────────────────────────────────────────

export interface RAGSearchResult {
  query: string;
  results: Array<{
    content: string;
    source: string;
    collection: string;
    score: number;
    metadata: Record<string, unknown>;
  }>;
  answer: string;
  sources: string[];
  confidence: number;
}

export async function searchClinicalRAG(body: {
  query: string;
  collection?: string;
  top_k?: number;
}) {
  return request<RAGSearchResult>("/rag/search", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchRAGCollections() {
  return request<{ collections: Array<{ name: string; doc_count: number; description: string }> }>("/rag/collections");
}

export async function ingestRAGDocument(body: {
  collection: string;
  content: string;
  metadata?: Record<string, unknown>;
}) {
  return request<{ document_id: string; status: string }>("/rag/ingest", { method: "POST", body: JSON.stringify(body) });
}

// ── Knowledge Graph ───────────────────────────────────────────────────────────

export interface KGNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface KGEdge {
  source: string;
  target: string;
  relationship: string;
  properties: Record<string, unknown>;
}

export interface KGQueryResult {
  nodes: KGNode[];
  edges: KGEdge[];
  total_nodes: number;
  total_edges: number;
}

export async function queryKnowledgeGraph(body: {
  query_type: string;
  entity?: string;
  depth?: number;
  limit?: number;
}) {
  return request<KGQueryResult>("/knowledge-graph/query", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchKGStats() {
  return request<{
    total_nodes: number;
    total_edges: number;
    node_types: Record<string, number>;
    edge_types: Record<string, number>;
  }>("/knowledge-graph/stats");
}

export async function fetchDrugInteractionsKG(drugName: string) {
  return request<KGQueryResult>(`/knowledge-graph/drugs/${encodeURIComponent(drugName)}/interactions`);
}

export async function fetchDiseaseRelationsKG(diseaseName: string) {
  return request<KGQueryResult>(`/knowledge-graph/diseases/${encodeURIComponent(diseaseName)}/relations`);
}

export async function fetchPatientGraphKG(patientId: string) {
  return request<KGQueryResult>(`/knowledge-graph/patients/${patientId}/graph`);
}

// ── EHR Interoperability ──────────────────────────────────────────────────────

export interface EHRConnector {
  id: string;
  name: string;
  type: "fhir" | "hl7v2";
  status: "active" | "inactive" | "error";
  base_url?: string;
  last_sync?: string;
  sync_count: number;
  error_count: number;
  created_at: string;
}

export async function fetchEHRConnectors() {
  return request<{ connectors: EHRConnector[] }>("/ehr/connectors");
}

export async function registerEHRConnector(body: {
  name: string;
  type: "fhir" | "hl7v2";
  config: Record<string, unknown>;
}) {
  return request<EHRConnector>("/ehr/connectors/register", { method: "POST", body: JSON.stringify(body) });
}

export async function syncEHRPatient(body: {
  connector_id: string;
  patient_id: string;
  direction: "push" | "pull";
}) {
  return request<Record<string, unknown>>("/ehr/sync/patient", { method: "POST", body: JSON.stringify(body) });
}

export async function syncEHREncounters(body: {
  connector_id: string;
  patient_id: string;
}) {
  return request<Record<string, unknown>>("/ehr/sync/encounters", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchEHRSyncHistory(connectorId: string) {
  return request<Array<{ id: string; direction: string; status: string; records: number; timestamp: string }>>(`/ehr/connectors/${connectorId}/history`);
}

// ── MCP Bridge ────────────────────────────────────────────────────────────────

export interface MCPServer {
  id: string;
  name: string;
  url: string;
  status: "connected" | "disconnected" | "error";
  tools: string[];
  last_heartbeat?: string;
}

export async function fetchMCPServers() {
  return request<{ servers: MCPServer[] }>("/mcp/servers");
}

export async function registerMCPServer(body: { name: string; url: string }) {
  return request<MCPServer>("/mcp/servers/register", { method: "POST", body: JSON.stringify(body) });
}

export async function executeMCPTool(body: {
  server_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
}) {
  return request<Record<string, unknown>>("/mcp/tools/execute", { method: "POST", body: JSON.stringify(body) });
}

// ── ML Models ─────────────────────────────────────────────────────────────────

export interface MLModelInfo {
  id: string;
  name: string;
  type: string;
  version: string;
  status: "active" | "training" | "inactive" | "error";
  accuracy?: number;
  last_trained?: string;
  predictions_count: number;
  description: string;
}

export interface MLPrediction {
  model_name: string;
  prediction: Record<string, unknown>;
  confidence: number;
  features_used: string[];
  timestamp: string;
}

export async function fetchMLModels() {
  return request<{ models: MLModelInfo[] }>("/ml/models");
}

export async function fetchMLModelMetrics(modelId: string) {
  return request<{
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    auc_roc: number;
    predictions_today: number;
    avg_latency_ms: number;
    fairness_metrics: Record<string, number>;
  }>(`/ml/models/${modelId}/metrics`);
}

export async function runMLPrediction(body: {
  model_name: string;
  patient_id: string;
  features?: Record<string, unknown>;
}) {
  return request<MLPrediction>("/ml/predict", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchFederatedStatus() {
  return request<{
    status: string;
    current_round: number;
    total_rounds: number;
    participating_tenants: number;
    global_accuracy: number;
    privacy_budget_remaining: number;
    last_aggregation?: string;
  }>("/ml/federated/status");
}

export async function startFederatedRound(body: {
  model_name: string;
  rounds: number;
  min_clients: number;
}) {
  return request<{ round_id: string; status: string }>("/ml/federated/start", { method: "POST", body: JSON.stringify(body) });
}

// ── SDOH (Social Determinants of Health) ──────────────────────────────────────

export interface SDOHAssessment {
  id: string;
  patient_id: string;
  domains: Array<{
    domain: string;
    risk_level: string;
    score: number;
    factors: string[];
  }>;
  overall_risk: string;
  recommendations: string[];
  resources: Array<{
    name: string;
    type: string;
    distance?: string;
    phone?: string;
    address?: string;
  }>;
  assessed_at: string;
}

export async function runSDOHAssessment(body: {
  patient_id: string;
  responses: Record<string, unknown>;
}) {
  return request<SDOHAssessment>("/sdoh/assess", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchSDOHHistory(patientId: string) {
  return request<SDOHAssessment[]>(`/sdoh/history/${patientId}`);
}

export async function fetchCommunityResources(body: {
  needs: string[];
  zip_code?: string;
  radius_miles?: number;
}) {
  return request<{ resources: Array<{ name: string; type: string; distance: string; phone: string; address: string; services: string[] }> }>("/sdoh/resources", { method: "POST", body: JSON.stringify(body) });
}

// ── Agent Pipelines ───────────────────────────────────────────────────────────

export interface PipelineExecution {
  trace_id: string;
  status: "running" | "completed" | "failed" | "halted";
  agents: Array<{
    name: string;
    tier: string;
    status: string;
    duration_ms: number;
    confidence?: number;
    output_summary?: string;
  }>;
  trigger_event: string;
  patient_id?: string;
  started_at: string;
  completed_at?: string;
  hitl_required: boolean;
}

export interface HITLReviewItem {
  id: string;
  trace_id: string;
  agent_name: string;
  patient_id: string;
  action: string;
  confidence: number;
  reason: string;
  context: Record<string, unknown>;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export async function fetchPipelineExecutions(params?: { status?: string; limit?: number }) {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return request<{ executions: PipelineExecution[] }>(`/agents/pipelines${qs ? `?${qs}` : ""}`);
}

export async function triggerPipeline(body: {
  event_type: string;
  patient_id?: string;
  payload?: Record<string, unknown>;
}) {
  return request<{ trace_id: string; status: string }>("/agents/trigger", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchHITLQueue() {
  return request<{ items: HITLReviewItem[] }>("/agents/hitl/queue");
}

export async function resolveHITLItem(itemId: string, body: {
  action: "approve" | "reject";
  notes?: string;
}) {
  return request<HITLReviewItem>(`/agents/hitl/${itemId}/resolve`, { method: "POST", body: JSON.stringify(body) });
}

// ── Feature Store ─────────────────────────────────────────────────────────────

export async function fetchFeatureStoreStats() {
  return request<{
    total_features: number;
    cached_patients: number;
    hit_rate: number;
    avg_compute_ms: number;
    feature_groups: Array<{ name: string; feature_count: number; last_updated: string }>;
  }>("/feature-store/stats");
}

// ── MS Risk Screening ──────────────────────────────────────────────────────

export interface MSRiskDashboard {
  total_patients: number;
  total_assessments: number;
  latest_run: {
    id: string;
    status: string;
    candidates_found: number;
    precision: number | null;
    recall: number | null;
    created_at: string;
  } | null;
  action_breakdown: {
    no_action: number;
    recommend_neuro_review: number;
    draft_mri_order: number;
    auto_order: number;
  };
}

export interface MSRiskAssessment {
  id: string;
  patient: { patient_id: string; age: number; sex: string };
  risk_score: number;
  action: string;
  autonomy_level: string;
  feature_contributions: Record<string, number>;
  flags: string[];
  flag_count: number;
  rationale: Record<string, unknown>;
  llm_summary: string;
  reviewed_by: string;
  review_notes: string;
  reviewed_at: string | null;
  created_at: string;
}

export interface MSRiskWorkflow {
  id: string;
  status: string;
  total_patients: number;
  candidates_found: number;
  flagged_count: number;
  precision: number | null;
  recall: number | null;
  auto_actions: number;
  draft_actions: number;
  recommend_actions: number;
  safety_flag_rate: number | null;
  duration_seconds: number | null;
  created_at: string;
}

export interface MSRiskPolicy {
  id: string;
  name: string;
  risk_review_threshold: number;
  draft_order_threshold: number;
  auto_order_threshold: number;
  max_auto_actions_per_day: number;
  is_active: boolean;
  created_at: string;
}

export async function fetchMSRiskDashboard() {
  return request<MSRiskDashboard>("/ms-risk-screening/dashboard");
}

export async function fetchMSRiskPatients(params?: { page?: number; page_size?: number }) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const qs = query.toString();
  return request<{ results: unknown[]; count: number }>(`/ms-risk-screening/patients${qs ? `?${qs}` : ""}`);
}

export async function fetchMSRiskAssessments(params?: { page?: number; page_size?: number }) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const qs = query.toString();
  return request<{ results: MSRiskAssessment[]; count: number }>(`/ms-risk-screening/assessments${qs ? `?${qs}` : ""}`);
}

export async function fetchMSRiskWorkflows(params?: { page?: number }) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  const qs = query.toString();
  return request<{ results: MSRiskWorkflow[]; count: number }>(`/ms-risk-screening/workflows${qs ? `?${qs}` : ""}`);
}

export async function triggerMSRiskWorkflow(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ms-risk-screening/workflows/trigger", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchMSRiskPolicies() {
  return request<{ results: MSRiskPolicy[] }>("/ms-risk-screening/policies");
}

export async function createMSRiskPolicy(body: Record<string, unknown>) {
  return request<MSRiskPolicy>("/ms-risk-screening/policies", { method: "POST", body: JSON.stringify(body) });
}

export async function runMSRiskWhatIf(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/ms-risk-screening/what-if", { method: "POST", body: JSON.stringify(body) });
}

export async function reviewMSRiskAssessment(assessmentId: string, body: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/ms-risk-screening/assessments/${assessmentId}/review`, { method: "POST", body: JSON.stringify(body) });
}

export async function fetchMSRiskGovernanceRules() {
  return request<{ results: unknown[] }>("/ms-risk-screening/governance-rules");
}

export async function fetchMSRiskComplianceReports() {
  return request<{ results: unknown[] }>("/ms-risk-screening/compliance-reports");
}

export async function fetchMSRiskAuditLogs(params?: { page?: number; action_type?: string; actor?: string }) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.action_type) query.set("action_type", params.action_type);
  if (params?.actor) query.set("actor", params.actor);
  const qs = query.toString();
  return request<{ results: unknown[]; count: number }>(`/ms-risk-screening/audit-logs${qs ? `?${qs}` : ""}`);
}

export async function fetchMSRiskPatientSummary() {
  return request<{
    total_patients: number;
    at_risk_count: number;
    at_risk_rate: number;
    by_sex: { sex: string; count: number }[];
    by_diagnosis: { lookalike_dx: string; count: number }[];
    avg_age: number;
  }>("/ms-risk-screening/patients/summary");
}

export async function fetchMSRiskPatientRiskHistory(patientId: string) {
  return request<MSRiskAssessment[]>(`/ms-risk-screening/patients/${patientId}/risk_history`);
}

export async function fetchMSRiskHighRiskAssessments(params?: { threshold?: number; run_id?: string }) {
  const query = new URLSearchParams();
  if (params?.threshold != null) query.set("threshold", String(params.threshold));
  if (params?.run_id) query.set("run_id", params.run_id);
  const qs = query.toString();
  return request<MSRiskAssessment[]>(`/ms-risk-screening/assessments/high_risk${qs ? `?${qs}` : ""}`);
}

export async function fetchMSRiskPendingReviews() {
  return request<MSRiskAssessment[]>("/ms-risk-screening/assessments/pending_review");
}

export async function activateMSRiskPolicy(policyId: string) {
  return request<MSRiskPolicy>(`/ms-risk-screening/policies/${policyId}/activate`, { method: "POST" });
}

export async function fetchMSRiskWorkflowMetrics(runId: string) {
  return request<Record<string, unknown>>(`/ms-risk-screening/workflows/${runId}/metrics`);
}

export async function fetchMSRiskWorkflowRiskDistribution(runId: string) {
  return request<unknown[]>(`/ms-risk-screening/workflows/${runId}/risk_distribution`);
}

export async function fetchMSRiskWorkflowActionDistribution(runId: string) {
  return request<unknown[]>(`/ms-risk-screening/workflows/${runId}/action_distribution`);
}

export async function fetchMSRiskWorkflowAutonomyDistribution(runId: string) {
  return request<unknown[]>(`/ms-risk-screening/workflows/${runId}/autonomy_distribution`);
}

export async function fetchMSRiskWorkflowCalibration(runId: string) {
  return request<unknown[]>(`/ms-risk-screening/workflows/${runId}/calibration`);
}

export async function fetchMSRiskWorkflowFairness(runId: string, groupBy: string = "sex") {
  return request<unknown[]>(`/ms-risk-screening/workflows/${runId}/fairness?group_by=${groupBy}`);
}

export async function generateMSRiskComplianceReport(body: { run_id: string }) {
  return request<{ task_id: string; status: string }>("/ms-risk-screening/compliance-reports/generate", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchMSRiskNotifications(params?: { page?: number }) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  const qs = query.toString();
  return request<{ results: unknown[]; count: number }>(`/ms-risk-screening/notifications${qs ? `?${qs}` : ""}`);
}

export async function fetchMSRiskUnreadNotificationCount() {
  return request<{ unread_count: number }>("/ms-risk-screening/notifications/unread_count");
}

export async function markMSRiskNotificationRead(notificationId: string) {
  return request<unknown>(`/ms-risk-screening/notifications/${notificationId}/mark_read`, { method: "POST" });
}

export async function markAllMSRiskNotificationsRead() {
  return request<{ status: string }>("/ms-risk-screening/notifications/mark_all_read", { method: "POST" });
}
