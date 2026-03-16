import { api } from "./http";

export interface Patient {
  id: number;
  mrn: string;
  fhir_id?: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  prefix?: string;
  suffix?: string;
  full_name?: string;
  date_of_birth: string;
  age?: number;
  gender: "male" | "female" | "other" | "unknown";
  blood_type?: string;
  ssn?: string;
  phone?: string;
  phone_secondary?: string;
  email?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relationship?: string;
  insurance_provider?: string;
  insurance_policy_number?: string;
  insurance_group_number?: string;
  allergies?: string[];
  medications?: string[];
  medical_conditions?: string[];
  medical_history?: string;
  status: "active" | "inactive" | "deceased";
  primary_care_physician?: string;
  created_at: string;
  updated_at?: string;
  documents?: PatientDocument[];
}

export interface PatientDocument {
  id: number;
  document_type: string;
  title: string;
  description?: string;
  file_url?: string;
  file_data?: string;
  mime_type?: string;
  metadata?: Record<string, unknown>;
  uploaded_at: string;
  uploaded_by?: string;
}

export interface PatientListResponse {
  total: number;
  limit: number;
  offset: number;
  results: Patient[];
}

export interface ImportResult {
  imported: number;
  failed: number;
  created: Array<{ id: number; mrn: string; name: string; fhir_id?: string }>;
  errors: Array<{ index: number; error?: string; errors?: Record<string, string[]> }>;
}

// Fetch all patients with optional filtering
export async function fetchPatients(params?: {
  search?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<PatientListResponse> {
  const res = await api.get<PatientListResponse>("/api/v1/patients/", { params });
  return res.data;
}

// Fetch a single patient by ID
export async function fetchPatient(patientId: number): Promise<Patient> {
  const res = await api.get<Patient>(`/api/v1/patients/${patientId}/`);
  return res.data;
}

// Fetch patient by MRN
export async function fetchPatientByMRN(mrn: string): Promise<Patient> {
  const res = await api.get<Patient>(`/api/v1/patients/by-mrn/${mrn}/`);
  return res.data;
}

// Create a new patient
export async function createPatient(patient: Partial<Patient>): Promise<Patient> {
  const res = await api.post<Patient>("/api/v1/patients/", patient);
  return res.data;
}

// Update a patient
export async function updatePatient(patientId: number, patient: Partial<Patient>): Promise<Patient> {
  const res = await api.put<Patient>(`/api/v1/patients/${patientId}/`, patient);
  return res.data;
}

// Delete a patient (soft delete)
export async function deletePatient(patientId: number): Promise<void> {
  await api.delete(`/api/v1/patients/${patientId}/`);
}

// Import patients from JSON
export async function importPatients(patients: Partial<Patient>[]): Promise<ImportResult> {
  const res = await api.post<ImportResult>("/api/v1/patients/import/", { patients });
  return res.data;
}

// Upload a document for a patient
export async function uploadDocument(
  patientId: number,
  document: Omit<PatientDocument, "id" | "uploaded_at">
): Promise<PatientDocument> {
  const res = await api.post<PatientDocument>(
    `/api/v1/patients/${patientId}/documents/`,
    document
  );
  return res.data;
}

// Fetch documents for a patient
export async function fetchPatientDocuments(
  patientId: number,
  type?: string
): Promise<PatientDocument[]> {
  const params = type ? { type } : {};
  const res = await api.get<PatientDocument[]>(
    `/api/v1/patients/${patientId}/documents/`,
    { params }
  );
  return res.data;
}

// Resync patient to FHIR
export async function resyncPatientToFhir(patientId: number): Promise<{ success: boolean; new_fhir_id?: string; error?: string }> {
  const res = await api.post<{ success: boolean; new_fhir_id?: string; error?: string }>(
    `/api/v1/patients/${patientId}/resync/`
  );
  return res.data;
}
