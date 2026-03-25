/**
 * Eminence HealthOS — Patient Portal API Client
 * Patient-facing API functions hitting /api/v1/portal/* endpoints.
 */

const API_PREFIX = "/api/v1/portal";

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

// ── Types ────────────────────────────────────────────────────────────────────

export interface PatientProfile {
  id: string;
  name: string;
  dob: string;
  risk_level: string;
}

export interface PatientHealthSummary {
  patient: PatientProfile;
  conditions: Array<Record<string, unknown>>;
  medications: Array<Record<string, unknown>>;
  latest_vitals: PatientVital[];
  active_alerts: PatientAlert[];
}

export interface PatientVital {
  id?: string;
  type: string;
  value: Record<string, unknown> | number | string;
  unit: string;
  source?: string | null;
  recorded_at: string | null;
}

export interface PatientVitalsResponse {
  patient_id: string;
  period_days: number;
  total: number;
  vitals: PatientVital[];
}

export interface PatientAlert {
  id: string;
  type: string;
  priority: string;
  status?: string;
  message: string | null;
  created_at: string | null;
}

export interface PatientAppointment {
  id: string;
  type: string;
  status: string;
  reason: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface CarePlan {
  id: string;
  type: string;
  goals: string[];
  interventions: string[];
  monitoring: string | null;
  status: string;
  created_at: string | null;
}

export interface PatientMessage {
  id: string;
  sender_type: "patient" | "provider";
  sender_name: string;
  subject: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

export interface PatientMessagesResponse {
  messages: PatientMessage[];
  total: number;
  unread: number;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function fetchPatientProfile(): Promise<PatientHealthSummary> {
  return request<PatientHealthSummary>("/me/summary");
}

export async function fetchPatientVitals(
  vitalType?: string,
  days = 30,
): Promise<PatientVitalsResponse> {
  const params = new URLSearchParams();
  if (vitalType) params.set("vital_type", vitalType);
  params.set("days", String(days));
  const qs = params.toString();
  return request<PatientVitalsResponse>(`/me/vitals${qs ? `?${qs}` : ""}`);
}

export async function fetchPatientAppointments(
  status?: string,
): Promise<PatientAppointment[]> {
  const qs = status ? `?status=${status}` : "";
  return request<PatientAppointment[]>(`/me/appointments${qs}`);
}

export async function fetchPatientCarePlans(): Promise<CarePlan[]> {
  return request<CarePlan[]>("/me/care-plans");
}

export async function fetchPatientAlerts(): Promise<PatientAlert[]> {
  return request<PatientAlert[]>("/me/alerts");
}

export async function fetchPatientMessages(): Promise<PatientMessagesResponse> {
  return request<PatientMessagesResponse>("/me/messages");
}

export async function sendMessage(body: {
  subject: string;
  body: string;
}): Promise<PatientMessage> {
  return request<PatientMessage>("/me/messages", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function requestAppointment(body: {
  type: string;
  reason: string;
  preferred_date?: string;
}): Promise<{ message: string; appointment_id: string }> {
  return request("/me/appointments/request", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── My Account / Profile ────────────────────────────────────────────────────

export interface PatientDemographics {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: string;
  gender_identity: string | null;
  race: string | null;
  ethnicity: string | null;
  preferred_language: string | null;
  email: string | null;
  phone: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
}

export interface EmergencyContact {
  name: string | null;
  phone: string | null;
  relationship: string | null;
}

export interface InsuranceInfo {
  provider: string | null;
  member_id: string | null;
  group_number: string | null;
}

export interface PatientAccountDetails {
  id: string;
  mrn: string | null;
  demographics: PatientDemographics;
  emergency_contact: EmergencyContact;
  insurance: InsuranceInfo;
  blood_type: string | null;
  allergies: PatientAllergy[];
}

export interface PatientAllergy {
  id: string;
  allergen: string;
  allergy_type: string;
  severity: string;
  reaction: string | null;
  onset_date: string | null;
  is_active: boolean;
}

export async function fetchMyAccount(): Promise<PatientAccountDetails> {
  return request<PatientAccountDetails>("/me/account");
}

export async function updateMyDemographics(
  data: Partial<PatientDemographics>,
): Promise<PatientAccountDetails> {
  return request<PatientAccountDetails>("/me/demographics", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function updateMyEmergencyContact(
  data: EmergencyContact,
): Promise<PatientAccountDetails> {
  return request<PatientAccountDetails>("/me/emergency-contact", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function updateMyInsurance(
  data: InsuranceInfo,
): Promise<PatientAccountDetails> {
  return request<PatientAccountDetails>("/me/insurance", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function addMyAllergy(body: {
  allergen: string;
  allergy_type: string;
  severity: string;
  reaction?: string;
  onset_date?: string;
}): Promise<PatientAllergy> {
  return request<PatientAllergy>("/me/allergies", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function removeMyAllergy(allergyId: string): Promise<void> {
  return request<void>(`/me/allergies/${allergyId}`, {
    method: "DELETE",
  });
}
