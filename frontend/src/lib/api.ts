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

// ── Vitals ───────────────────────────────────────────────────────────────────

export async function fetchVitals(patientId: string) {
  return request<{ vitals: unknown[] }>(`/vitals?patient_id=${patientId}`);
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

// ── FHIR ─────────────────────────────────────────────────────────────────────

export async function fetchFHIRPatient(patientId: string) {
  return request<unknown>(`/fhir/r4/Patient/${patientId}`);
}
