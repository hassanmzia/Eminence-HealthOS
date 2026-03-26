/**
 * Eminence HealthOS — Platform API Client (Phase 1-6 EHR Routes)
 * CRUD operations for hospitals, providers, clinical data, devices,
 * messaging, billing, and enterprise authentication.
 */

const API_PREFIX = "/api/v1";

/** Extract the user role from the JWT stored in localStorage (returns "" if unavailable). */
export function getUserRole(): string {
  if (typeof window === "undefined") return "";
  const token = localStorage.getItem("access_token");
  if (!token) return "";
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role ?? "";
  } catch {
    return "";
  }
}

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

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Hospitals ────────────────────────────────────────────────────────────────

export interface HospitalResponse {
  id: string;
  name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DepartmentResponse {
  id: string;
  hospital_id: string;
  name: string;
  location: string | null;
  phone: string | null;
  email: string | null;
  head_of_department: string | null;
  is_active: boolean;
  created_at: string;
}

export async function fetchHospitals() {
  return request<HospitalResponse[]>("/hospitals");
}

export async function createHospital(body: {
  name: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  phone?: string;
  email?: string;
  website?: string;
}) {
  return request<HospitalResponse>("/hospitals", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchHospital(hospitalId: string) {
  return request<HospitalResponse>(`/hospitals/${hospitalId}`);
}

export async function fetchDepartments(hospitalId: string) {
  return request<DepartmentResponse[]>(`/hospitals/${hospitalId}/departments`);
}

export async function createDepartment(body: {
  hospital_id: string;
  name: string;
  location?: string;
  phone?: string;
  email?: string;
  head_of_department?: string;
}) {
  return request<DepartmentResponse>("/hospitals/departments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Providers ────────────────────────────────────────────────────────────────

export interface ProviderProfileResponse {
  id: string;
  user_id: string;
  specialty: string;
  npi: string;
  license_number: string | null;
  hospital_id: string | null;
  department_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface NurseProfileResponse {
  id: string;
  user_id: string;
  specialty: string;
  license_number: string;
  hospital_id: string | null;
  department_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface OfficeAdminProfileResponse {
  id: string;
  user_id: string;
  position: string;
  employee_id: string;
  hospital_id: string | null;
  department_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ProviderDashboard {
  role: string;
  total_patients: number;
  pending_alerts: number;
  scheduled_encounters: number;
}

export async function fetchProviders() {
  return request<ProviderProfileResponse[]>("/providers");
}

export async function createProvider(body: {
  user_id: string;
  specialty: string;
  npi: string;
  license_number?: string;
  hospital_id?: string;
  department_id?: string;
}) {
  return request<ProviderProfileResponse>("/providers", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchProvider(providerId: string) {
  return request<ProviderProfileResponse>(`/providers/${providerId}`);
}

export async function fetchNurses() {
  return request<NurseProfileResponse[]>("/providers/nurses");
}

export async function createNurse(body: {
  user_id: string;
  specialty?: string;
  license_number: string;
  hospital_id?: string;
  department_id?: string;
}) {
  return request<NurseProfileResponse>("/providers/nurses", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchOfficeAdmins() {
  return request<OfficeAdminProfileResponse[]>("/providers/office-admins");
}

export async function createOfficeAdmin(body: {
  user_id: string;
  position?: string;
  employee_id: string;
  hospital_id?: string;
  department_id?: string;
}) {
  return request<OfficeAdminProfileResponse>("/providers/office-admins", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchProviderDashboard() {
  return request<ProviderDashboard>("/providers/dashboard");
}

// ── Clinical Data ────────────────────────────────────────────────────────────

export interface DiagnosisResponse {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  diagnosis_description: string;
  icd10_code: string | null;
  icd11_code: string | null;
  diagnosis_type: string;
  status: string;
  diagnosed_by: string | null;
  diagnosed_at: string;
  notes: string | null;
  created_at: string;
}

export interface PrescriptionResponse {
  id: string;
  patient_id: string;
  provider_id: string | null;
  medication_name: string;
  dosage: string;
  frequency: string;
  route: string | null;
  start_date: string;
  end_date: string | null;
  refills: number;
  quantity: number | null;
  instructions: string | null;
  status: string;
  created_at: string;
}

export interface AllergyResponse {
  id: string;
  patient_id: string;
  allergen: string;
  allergy_type: string;
  severity: string;
  reaction: string | null;
  onset_date: string | null;
  is_active: boolean;
  created_at: string;
}

export interface MedicalHistoryResponse {
  id: string;
  patient_id: string;
  condition: string;
  diagnosis_date: string | null;
  resolution_date: string | null;
  status: string;
  treatment_notes: string | null;
  created_at: string;
}

export interface SocialHistoryResponse {
  id: string;
  patient_id: string;
  smoking_status: string;
  alcohol_use: string;
  occupation: string | null;
  marital_status: string | null;
  created_at: string;
}

export interface FamilyHistoryResponse {
  id: string;
  patient_id: string;
  relationship: string;
  condition: string;
  age_at_diagnosis: number | null;
  is_alive: boolean;
  cause_of_death: string | null;
  created_at: string;
}

export interface LabTestResponse {
  id: string;
  patient_id: string;
  provider_id: string | null;
  test_name: string;
  test_code: string | null;
  ordered_date: string;
  sample_collected_date: string | null;
  result_date: string | null;
  status: string;
  result_value: string | null;
  result_unit: string | null;
  reference_range: string | null;
  abnormal_flag: boolean;
  interpretation: string | null;
  created_at: string;
}

// Clinical - Diagnoses
export async function fetchDiagnoses(patientId: string) {
  return request<DiagnosisResponse[]>(`/clinical/diagnoses/${patientId}`);
}

export async function createDiagnosis(body: {
  patient_id: string;
  encounter_id?: string;
  diagnosis_description: string;
  icd10_code?: string;
  icd11_code?: string;
  diagnosis_type?: string;
  status?: string;
  notes?: string;
}) {
  return request<DiagnosisResponse>("/clinical/diagnoses", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Clinical - Prescriptions
export async function fetchAllPrescriptions(status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<PrescriptionResponse[]>(
    `/clinical/prescriptions/all${qs ? `?${qs}` : ""}`,
  );
}

export async function fetchPrescriptions(patientId: string, status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<PrescriptionResponse[]>(
    `/clinical/prescriptions/${patientId}${qs ? `?${qs}` : ""}`,
  );
}

export async function createPrescriptionRecord(body: {
  patient_id: string;
  encounter_id?: string;
  medication_name: string;
  dosage: string;
  frequency: string;
  route?: string;
  start_date: string;
  end_date?: string;
  refills?: number;
  quantity?: number;
  instructions?: string;
  status?: string;
  notes?: string;
}) {
  return request<PrescriptionResponse>("/clinical/prescriptions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Clinical - Allergies
export async function fetchAllergies(patientId: string) {
  return request<AllergyResponse[]>(`/clinical/allergies/${patientId}`);
}

export async function createAllergy(body: {
  patient_id: string;
  allergen: string;
  allergy_type: string;
  severity: string;
  reaction?: string;
  onset_date?: string;
  notes?: string;
}) {
  return request<AllergyResponse>("/clinical/allergies", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Clinical - Medical History
export async function fetchMedicalHistory(patientId: string) {
  return request<MedicalHistoryResponse[]>(
    `/clinical/medical-history/${patientId}`,
  );
}

export async function createMedicalHistory(body: {
  patient_id: string;
  condition: string;
  diagnosis_date?: string;
  resolution_date?: string;
  status?: string;
  treatment_notes?: string;
}) {
  return request<MedicalHistoryResponse>("/clinical/medical-history", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Clinical - Social History
export async function fetchSocialHistory(patientId: string) {
  return request<SocialHistoryResponse[]>(
    `/clinical/social-history/${patientId}`,
  );
}

export async function createSocialHistory(body: {
  patient_id: string;
  smoking_status?: string;
  alcohol_use?: string;
  drug_use?: string;
  occupation?: string;
  marital_status?: string;
  living_situation?: string;
  exercise?: string;
  diet?: string;
  notes?: string;
}) {
  return request<SocialHistoryResponse>("/clinical/social-history", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Clinical - Family History
export async function fetchFamilyHistory(patientId: string) {
  return request<FamilyHistoryResponse[]>(
    `/clinical/family-history/${patientId}`,
  );
}

export async function createFamilyHistory(body: {
  patient_id: string;
  relationship: string;
  condition: string;
  age_at_diagnosis?: number;
  is_alive?: boolean;
  age_at_death?: number;
  cause_of_death?: string;
  notes?: string;
}) {
  return request<FamilyHistoryResponse>("/clinical/family-history", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Clinical - Lab Tests
export async function fetchAllLabTests(status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<LabTestResponse[]>(
    `/clinical/labs/all${qs ? `?${qs}` : ""}`,
  );
}

export async function fetchLabTests(patientId: string, status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<LabTestResponse[]>(
    `/clinical/labs/${patientId}${qs ? `?${qs}` : ""}`,
  );
}

export async function createLabTest(body: {
  patient_id: string;
  encounter_id?: string;
  test_name: string;
  test_code?: string;
  status?: string;
  notes?: string;
}) {
  return request<LabTestResponse>("/clinical/labs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateLabTest(
  labId: string,
  body: {
    status?: string;
    result_value?: string;
    result_unit?: string;
    reference_range?: string;
    abnormal_flag?: boolean;
    interpretation?: string;
    notes?: string;
  },
) {
  return request<LabTestResponse>(`/clinical/labs/${labId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Devices / IoT ────────────────────────────────────────────────────────────

export interface DeviceInfoResponse {
  id: string;
  device_unique_id: string;
  device_name: string;
  device_type: string;
  manufacturer: string | null;
  model_number: string | null;
  firmware_version: string | null;
  status: string;
  battery_level: number | null;
  last_sync: string | null;
  created_at: string;
}

export interface DeviceAlertRuleResponse {
  id: string;
  rule_name: string;
  metric_name: string;
  condition: string;
  threshold_value: number;
  alert_level: string;
  alert_message: string;
  is_active: boolean;
  created_at: string;
}

export async function fetchDevices() {
  return request<DeviceInfoResponse[]>("/device/manage/list");
}

export async function registerDevice(body: {
  patient_id: string;
  device_unique_id: string;
  device_name: string;
  device_type: string;
  manufacturer?: string;
  model_number?: string;
  serial_number?: string;
  firmware_version?: string;
}) {
  return request<DeviceInfoResponse>("/device/manage/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function rotateDeviceApiKey(
  deviceId: string,
  keyName = "default",
) {
  return request<{ api_key: string; device_id: string }>(
    `/device/manage/${deviceId}/api-key?key_name=${keyName}`,
    { method: "POST" },
  );
}

export async function fetchDeviceAlertRules() {
  return request<DeviceAlertRuleResponse[]>("/device/alert-rules");
}

// ── Patient Questionnaires (clinician view) ─────────────────────────────────

export interface PatientQuestionnaireResponse {
  id: string;
  questionnaire_type: string;
  status: string;
  responses: Record<string, unknown>;
  submitted_at: string | null;
  reviewed_at: string | null;
  reviewer_notes: string | null;
  created_at: string | null;
  ai_insights?: {
    chief_complaint?: string;
    review_of_systems?: Record<string, string[]>;
    patient_reported_symptoms?: string[];
    social_history?: Record<string, string>;
    history_present_illness?: string;
  };
}

export async function fetchPatientQuestionnaires(
  patientId: string,
  status?: string,
) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<PatientQuestionnaireResponse[]>(
    `/clinical/questionnaires/${patientId}${qs ? `?${qs}` : ""}`,
  );
}

export async function reviewQuestionnaire(
  questionnaireId: string,
  notes: string,
) {
  return request<PatientQuestionnaireResponse>(
    `/clinical/questionnaires/${questionnaireId}/review`,
    { method: "POST", body: JSON.stringify({ notes }) },
  );
}

// ── Patient Devices (assignment) ────────────────────────────────────────────

export async function fetchPatientDevices(patientId: string) {
  return request<DeviceInfoResponse[]>(
    `/device/manage/patient/${patientId}`,
  );
}

export async function assignDeviceToPatient(body: {
  patient_id: string;
  device_id: string;
}) {
  return request<DeviceInfoResponse>("/device/manage/assign", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function unassignDevice(deviceId: string) {
  return request<{ detail: string }>(`/device/manage/${deviceId}/unassign`, {
    method: "POST",
  });
}

export async function createDeviceAlertRule(body: {
  device_id?: string;
  patient_id?: string;
  rule_name: string;
  metric_name: string;
  condition: string;
  threshold_value: number;
  alert_level?: string;
  alert_message: string;
  notify_patient?: boolean;
  notify_provider?: boolean;
}) {
  return request<DeviceAlertRuleResponse>("/device/alert-rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Messaging ────────────────────────────────────────────────────────────────

export interface MessageResponse {
  id: string;
  sender_id: string;
  recipient_id: string;
  subject: string;
  body: string;
  is_read: boolean;
  read_at: string | null;
  parent_message_id: string | null;
  created_at: string;
}

export interface NotificationResponse {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  read_at: string | null;
  link: string | null;
  created_at: string;
}

export interface NotificationPreferenceResponse {
  email_enabled: boolean;
  sms_enabled: boolean;
  whatsapp_enabled: boolean;
  enable_quiet_hours: boolean;
  digest_mode: boolean;
}

export async function fetchInbox(page = 1, pageSize = 20) {
  return request<MessageResponse[]>(
    `/messaging/inbox?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchSentMessages(page = 1, pageSize = 20) {
  return request<MessageResponse[]>(
    `/messaging/sent?page=${page}&page_size=${pageSize}`,
  );
}

export async function sendSecureMessage(body: {
  recipient_id: string;
  subject: string;
  body: string;
  parent_message_id?: string;
}) {
  return request<MessageResponse>("/messaging/send", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchMessageThread(messageId: string) {
  return request<MessageResponse[]>(`/messaging/thread/${messageId}`);
}

export async function markMessageRead(messageId: string) {
  return request<{ status: string }>(`/messaging/${messageId}/read`, {
    method: "POST",
  });
}

export async function fetchNotifications(
  unreadOnly = false,
  page = 1,
  pageSize = 20,
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (unreadOnly) params.set("unread_only", "true");
  return request<NotificationResponse[]>(
    `/messaging/notifications?${params.toString()}`,
  );
}

export async function fetchUnreadNotificationCount() {
  return request<{ unread_count: number }>(
    "/messaging/notifications/unread-count",
  );
}

export async function markNotificationRead(notificationId: string) {
  return request<{ status: string }>(
    `/messaging/notifications/${notificationId}/read`,
    { method: "POST" },
  );
}

export async function markAllNotificationsRead() {
  return request<{ status: string }>("/messaging/notifications/mark-all-read", {
    method: "POST",
  });
}

export async function fetchNotificationPreferences() {
  return request<NotificationPreferenceResponse>("/messaging/preferences");
}

export async function updateNotificationPreferences(body: {
  email_enabled?: boolean;
  email_emergency?: boolean;
  email_critical?: boolean;
  email_warning?: boolean;
  sms_enabled?: boolean;
  sms_emergency?: boolean;
  sms_critical?: boolean;
  sms_warning?: boolean;
  whatsapp_enabled?: boolean;
  whatsapp_number?: string;
  enable_quiet_hours?: boolean;
  quiet_start_time?: string;
  quiet_end_time?: string;
  digest_mode?: boolean;
  digest_frequency_hours?: number;
}) {
  return request<NotificationPreferenceResponse>("/messaging/preferences", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function respondToAlert(
  responseToken: string,
  body: {
    response_status: string;
    wants_doctor?: boolean;
    wants_nurse?: boolean;
    wants_ems?: boolean;
    response_method?: string;
  },
) {
  return request<{ status: string }>(
    `/messaging/alerts/respond/${responseToken}`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

// ── Billing ──────────────────────────────────────────────────────────────────

export interface BillingResponse {
  id: string;
  patient_id: string;
  invoice_number: string;
  billing_date: string;
  due_date: string;
  total_amount: number;
  amount_paid: number;
  amount_due: number;
  status: string;
  notes: string | null;
  created_at: string;
}

export interface BillingItemResponse {
  id: string;
  service_code: string;
  service_description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface PaymentResponse {
  id: string;
  patient_id: string;
  billing_id: string;
  amount: number;
  payment_method: string;
  transaction_id: string | null;
  status: string;
  payment_date: string;
}

export interface InsuranceResponse {
  id: string;
  patient_id: string;
  provider_name: string;
  policy_number: string;
  group_number: string | null;
  policyholder_name: string;
  policyholder_relationship: string;
  effective_date: string;
  termination_date: string | null;
  is_primary: boolean;
  copay_amount: number | null;
  deductible_amount: number | null;
  created_at: string;
}

export async function fetchInvoices(params?: {
  patient_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) {
  const query = new URLSearchParams();
  if (params?.patient_id) query.set("patient_id", params.patient_id);
  if (params?.status) query.set("status", params.status);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const qs = query.toString();
  return request<BillingResponse[]>(`/billing/invoices${qs ? `?${qs}` : ""}`);
}

export async function createInvoice(body: {
  patient_id: string;
  encounter_id?: string;
  invoice_number: string;
  billing_date: string;
  due_date: string;
  items?: Array<{
    service_code: string;
    service_description: string;
    quantity?: number;
    unit_price: number;
  }>;
  notes?: string;
}) {
  return request<BillingResponse>("/billing/invoices", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchInvoice(invoiceId: string) {
  return request<BillingResponse>(`/billing/invoices/${invoiceId}`);
}

export async function fetchInvoiceItems(invoiceId: string) {
  return request<BillingItemResponse[]>(
    `/billing/invoices/${invoiceId}/items`,
  );
}

export async function fetchPayments(patientId?: string) {
  const qs = patientId ? `?patient_id=${patientId}` : "";
  return request<PaymentResponse[]>(`/billing/payments${qs}`);
}

export async function createPayment(body: {
  billing_id: string;
  patient_id: string;
  amount: number;
  payment_method: string;
  transaction_id?: string;
  notes?: string;
}) {
  return request<PaymentResponse>("/billing/payments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchInsurance(patientId: string) {
  return request<InsuranceResponse[]>(`/billing/insurance/${patientId}`);
}

export async function createInsurance(body: {
  patient_id: string;
  provider_name: string;
  policy_number: string;
  group_number?: string;
  policyholder_name: string;
  policyholder_relationship: string;
  effective_date: string;
  termination_date?: string;
  is_primary?: boolean;
  copay_amount?: number;
  deductible_amount?: number;
}) {
  return request<InsuranceResponse>("/billing/insurance", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateInsurance(
  insuranceId: string,
  body: {
    patient_id: string;
    provider_name: string;
    policy_number: string;
    group_number?: string;
    policyholder_name: string;
    policyholder_relationship: string;
    effective_date: string;
    termination_date?: string;
    is_primary?: boolean;
    copay_amount?: number;
    deductible_amount?: number;
  },
) {
  return request<InsuranceResponse>(`/billing/insurance/${insuranceId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

// ── Enterprise Auth ──────────────────────────────────────────────────────────

export interface AuthConfigResponse {
  id: string;
  auth_method: string;
  is_enabled: boolean;
  is_primary: boolean;
  config: Record<string, unknown>;
  created_at: string;
}

export interface SessionResponse {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  last_activity: string;
  is_active: boolean;
  created_at: string;
}

export async function fetchAuthConfigs() {
  return request<AuthConfigResponse[]>("/enterprise-auth/configs");
}

export async function createAuthConfig(body: {
  auth_method: string;
  is_enabled?: boolean;
  is_primary?: boolean;
  config?: Record<string, unknown>;
}) {
  return request<AuthConfigResponse>("/enterprise-auth/configs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateAuthConfig(
  configId: string,
  body: {
    auth_method: string;
    is_enabled?: boolean;
    is_primary?: boolean;
    config?: Record<string, unknown>;
  },
) {
  return request<AuthConfigResponse>(`/enterprise-auth/configs/${configId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteAuthConfig(configId: string) {
  return request<void>(`/enterprise-auth/configs/${configId}`, {
    method: "DELETE",
  });
}

export async function setupEnterpriseMFA() {
  return request<{ secret: string; provisioning_uri: string }>(
    "/enterprise-auth/mfa/setup",
    { method: "POST" },
  );
}

export async function verifyEnterpriseMFA(code: string) {
  return request<{ status: string; backup_codes: string[] }>(
    "/enterprise-auth/mfa/verify",
    { method: "POST", body: JSON.stringify({ code }) },
  );
}

export async function disableEnterpriseMFA(code: string) {
  return request<{ status: string }>("/enterprise-auth/mfa/disable", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function sendEmailVerification() {
  return request<{ message: string }>(
    "/enterprise-auth/email/send-verification",
    { method: "POST" },
  );
}

export async function verifyEmail(token: string) {
  return request<{ message: string }>("/enterprise-auth/email/verify", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export async function changeEnterprisePassword(body: {
  current_password: string;
  new_password: string;
}) {
  return request<{ message: string }>("/enterprise-auth/password/change", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function unlockAccount(userId: string) {
  return request<{ message: string }>(
    `/enterprise-auth/account/unlock/${userId}`,
    { method: "POST" },
  );
}

export async function fetchSessions() {
  return request<SessionResponse[]>("/enterprise-auth/sessions");
}

export async function revokeSession(sessionId: string) {
  return request<{ status: string }>(
    `/enterprise-auth/sessions/${sessionId}/revoke`,
    { method: "POST" },
  );
}

export async function revokeAllSessions() {
  return request<{ status: string }>("/enterprise-auth/sessions/revoke-all", {
    method: "POST",
  });
}

// ── Admin User Management ─────────────────────────────────────────────────────

export interface AdminUserResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id: string;
  is_active: boolean;
  mfa_enabled: boolean;
  phone: string | null;
  avatar_url: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminUserListResponse {
  users: AdminUserResponse[];
  total: number;
  page: number;
  page_size: number;
}

export async function fetchAdminUsers(params?: {
  page?: number;
  page_size?: number;
  role?: string;
  is_active?: boolean;
  search?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.role) qs.set("role", params.role);
  if (params?.is_active !== undefined) qs.set("is_active", String(params.is_active));
  if (params?.search) qs.set("search", params.search);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request<AdminUserListResponse>(`/admin/users${query}`);
}

export async function createAdminUser(body: {
  email: string;
  password: string;
  full_name: string;
  role?: string;
  hospital_id?: string;
  department_id?: string;
  // Provider-specific
  specialty?: string;
  npi?: string;
  license_number?: string;
  // Office-admin-specific
  position?: string;
  employee_id?: string;
}) {
  return request<AdminUserResponse>("/admin/users", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateAdminUser(
  userId: string,
  body: {
    full_name?: string;
    role?: string;
    is_active?: boolean;
    phone?: string;
    hospital_id?: string;
    department_id?: string;
    specialty?: string;
    npi?: string;
    license_number?: string;
    position?: string;
    employee_id?: string;
  }
) {
  return request<AdminUserResponse>(`/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deactivateAdminUser(userId: string) {
  return request<{ message: string }>(`/admin/users/${userId}`, {
    method: "DELETE",
  });
}

export async function promoteSelfToAdmin() {
  return request<AdminUserResponse>("/admin/users/promote-self", {
    method: "POST",
  });
}

// ── Operations ─────────────────────────────────────────────────────────────

export async function fetchPriorAuthorizations(status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<{ items: Record<string, unknown>[]; total: number }>(
    `/operations/prior-auth/list${qs ? `?${qs}` : ""}`
  );
}

export async function fetchInsuranceVerifications() {
  return request<{ items: Record<string, unknown>[]; total: number }>(
    "/operations/insurance/list"
  );
}

export async function fetchReferrals(status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<{ items: Record<string, unknown>[]; total: number }>(
    `/operations/referrals/list${qs ? `?${qs}` : ""}`
  );
}

export async function fetchOperationalWorkflows(status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<{ items: Record<string, unknown>[]; total: number }>(
    `/operations/workflows/list${qs ? `?${qs}` : ""}`
  );
}

export async function fetchWorkflowTemplates() {
  return request<{ templates: string[] }>("/operations/workflows/templates");
}

export async function createOperationalWorkflow(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/operations/workflows/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function completeWorkflowStep(
  workflowId: string,
  stepId: string,
  output: Record<string, unknown> = {}
) {
  return request<Record<string, unknown>>(
    `/operations/workflows/${workflowId}/steps/${stepId}/complete`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ output }),
    }
  );
}

export async function createOperationalTask(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/operations/tasks/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function submitPriorAuth(body: Record<string, unknown>) {
  return request<Record<string, unknown>>("/operations/prior-auth/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// =============================================================================
// Clinical AI Assessment API (HITL Workflow)
// =============================================================================

export interface ClinicalFinding {
  type: string;
  name: string;
  value: string | number;
  unit?: string;
  status: "normal" | "abnormal" | "critical";
  interpretation: string;
  source: string;
  reference_range?: string;
}

export interface AIDiagnosisRecommendation {
  diagnosis: string;
  icd10_code: string;
  confidence: number;
  supporting_findings: ClinicalFinding[];
  rationale: string;
  differential_diagnoses?: Array<{
    diagnosis: string;
    icd10: string;
    confidence: number;
    rationale: string;
  }>;
}

export interface AITreatmentRecommendation {
  treatment_type: string;
  description: string;
  priority: string;
  rationale: string;
  cpt_code?: string;
  contraindications?: string[];
  monitoring?: string[];
}

export interface ClinicalAssessmentResult {
  patient_summary: {
    patient_id: string;
    name?: string;
    age?: number;
    sex?: string;
  };
  findings: ClinicalFinding[];
  critical_findings: ClinicalFinding[];
  diagnoses: AIDiagnosisRecommendation[];
  treatments: AITreatmentRecommendation[];
  icd10_codes: Array<{ code: string; description: string; category: string; confidence: number }>;
  cpt_codes: Array<{ code: string; description: string; category: string }>;
  confidence: number;
  reasoning: string[];
  warnings: string[];
  requires_human_review: boolean;
  review_reason?: string;
  assessment_id?: string;
  persisted_recommendation_id?: number;
}

export interface ClinicalAssessmentResponse {
  success: boolean;
  patient_id: string;
  assessment?: ClinicalAssessmentResult;
  error?: string;
  llm_provider?: string;
}

export interface PhysicianReviewSubmission {
  assessment_id: string;
  physician_id: string;
  physician_name: string;
  physician_npi?: string;
  physician_specialty?: string;
  decision: "approved" | "approved_modified" | "rejected" | "deferred";
  approved_diagnoses: number[];
  rejected_diagnoses: number[];
  approved_treatments: number[];
  rejected_treatments: number[];
  modified_diagnoses?: Array<Record<string, unknown>>;
  modified_treatments?: Array<Record<string, unknown>>;
  physician_notes?: string;
  rejection_reason?: string;
  clinical_rationale?: string;
  attest: boolean;
  review_started_at?: string;
}

export interface PhysicianReviewResult {
  id: string;
  assessment: string;
  physician_id: string;
  physician_name: string;
  physician_npi?: string;
  physician_specialty?: string;
  decision: string;
  approved_diagnoses: number[];
  rejected_diagnoses: number[];
  approved_treatments: number[];
  rejected_treatments: number[];
  final_icd10_codes: Array<{ code: string; description: string }>;
  final_cpt_codes: Array<{ code: string; description: string }>;
  physician_notes: string;
  attested: boolean;
  signature_datetime?: string;
  review_completed_at?: string;
  time_spent_seconds: number;
  created_at: string;
}

export interface ClinicalDocumentResult {
  id: string;
  assessment: string;
  document_type: string;
  title: string;
  format: string;
  status: string;
  content: string;
  created_at: string;
}

export interface EHROrderResult {
  id: string;
  order_type: string;
  status: string;
  description: string;
  cpt_code?: string;
  ehr_order_id?: string;
  created_at: string;
}

export interface LLMStatusResponse {
  status: string;
  primary_provider?: string;
  available_providers?: string[];
  config?: {
    claude_model: string;
    ollama_model: string;
    ollama_base_url: string;
    temperature: number;
    max_tokens: number;
  };
  error?: string;
}

// Run comprehensive clinical assessment
export async function runClinicalAssessment(
  patientId: string,
  fhirId?: string
): Promise<ClinicalAssessmentResponse> {
  return request<ClinicalAssessmentResponse>("/clinical-assessment/assess", {
    method: "POST",
    body: JSON.stringify({
      patient_id: patientId,
      fhir_id: fhirId,
      include_diagnoses: true,
      include_treatments: true,
      include_codes: true,
    }),
  });
}

// Get LLM status
export async function fetchLLMStatus(): Promise<LLMStatusResponse> {
  return request<LLMStatusResponse>("/clinical-assessment/llm/status");
}

// Submit physician review (HITL)
export async function submitPhysicianReview(
  review: PhysicianReviewSubmission
): Promise<PhysicianReviewResult> {
  return request<PhysicianReviewResult>("/clinical/reviews/submit/", {
    method: "POST",
    body: JSON.stringify(review),
  });
}

// Generate clinical document
export async function generateClinicalDocument(
  assessmentId: string,
  reviewId?: string,
  documentType = "assessment_summary",
  format = "html",
  includeReasoning = false
): Promise<ClinicalDocumentResult> {
  return request<ClinicalDocumentResult>("/clinical/documents/generate/", {
    method: "POST",
    body: JSON.stringify({
      assessment_id: assessmentId,
      review_id: reviewId,
      document_type: documentType,
      format,
      include_reasoning: includeReasoning,
      include_codes: true,
    }),
  });
}

// Download clinical document
export async function downloadClinicalDocument(
  documentId: string,
  title: string,
  format = "pdf"
): Promise<void> {
  const url = `${API_PREFIX}/clinical/documents/${documentId}/download/?download_format=${format}`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${title.replace(/\s+/g, "_").replace(/\//g, "-")}.${format === "pdf" ? "pdf" : "html"}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

// Create EHR orders from approved treatments
export async function createEHROrders(
  assessmentId: string,
  reviewId: string,
  treatmentIndices: number[],
  physicianId: string,
  physicianName: string,
  physicianNpi?: string
): Promise<{ success: boolean; orders_created: number; orders: EHROrderResult[] }> {
  return request<{ success: boolean; orders_created: number; orders: EHROrderResult[] }>(
    "/clinical/orders/create/",
    {
      method: "POST",
      body: JSON.stringify({
        assessment_id: assessmentId,
        review_id: reviewId,
        treatment_indices: treatmentIndices,
        ordering_physician_id: physicianId,
        ordering_physician_name: physicianName,
        ordering_physician_npi: physicianNpi || "",
      }),
    }
  );
}
