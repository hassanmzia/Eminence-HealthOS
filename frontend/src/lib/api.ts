const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4090";
const API_PREFIX = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${API_PREFIX}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ── Patients ─────────────────────────────────────────────────────────────────

export async function fetchPatients() {
  return request<{ patients: unknown[] }>("/patients");
}

export async function fetchPatient(id: string) {
  return request<unknown>(`/patients/${id}`);
}

// ── Vitals ───────────────────────────────────────────────────────────────────

export async function fetchVitals(patientId: string) {
  return request<{ vitals: unknown[] }>(`/vitals?patient_id=${patientId}`);
}

// ── Alerts ───────────────────────────────────────────────────────────────────

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
  return request<{ alerts: unknown[] }>(`/alerts${qs ? `?${qs}` : ""}`);
}

// ── Agents ───────────────────────────────────────────────────────────────────

export async function fetchAgents() {
  return request<{ agents: unknown[] }>("/agents");
}

// ── FHIR ─────────────────────────────────────────────────────────────────────

export async function fetchFHIRPatient(patientId: string) {
  return request<unknown>(`/fhir/r4/Patient/${patientId}`);
}
