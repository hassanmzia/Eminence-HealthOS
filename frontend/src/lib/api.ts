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
