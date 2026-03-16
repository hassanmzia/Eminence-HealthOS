import { api } from "./http";

// Encounter Types
export interface Encounter {
  id: number;
  patient: number;
  patient_name?: string;
  patient_mrn?: string;
  fhir_id?: string;
  encounter_type: string;
  status: string;
  priority: string;
  start_time: string;
  end_time?: string;
  facility?: string;
  department?: string;
  room?: string;
  bed?: string;
  attending_physician?: string;
  attending_physician_id?: string;
  chief_complaint?: string;
  reason_codes?: string[];
  notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface EncounterListResponse {
  total: number;
  limit: number;
  offset: number;
  results: Encounter[];
}

// Clinical Note Types
export interface ClinicalNote {
  id: number;
  patient: number;
  patient_name?: string;
  patient_mrn?: string;
  encounter?: number;
  encounter_type?: string;
  note_type: string;
  status: string;
  title: string;
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  content?: string;
  author: string;
  author_role?: string;
  co_signer?: string;
  note_datetime: string;
  signed_datetime?: string;
  created_at: string;
  updated_at?: string;
}

export interface ClinicalNoteListResponse {
  total: number;
  limit: number;
  offset: number;
  results: ClinicalNote[];
}

// Diagnosis Types
export interface Diagnosis {
  id: number;
  patient: number;
  patient_name?: string;
  encounter?: number;
  icd10_code: string;
  description: string;
  category: string;
  status: string;
  onset_date?: string;
  resolution_date?: string;
  severity?: string;
  clinical_notes?: string;
  diagnosed_by?: string;
  diagnosed_date: string;
  is_primary: boolean;
  rank: number;
  created_at: string;
  updated_at?: string;
}

export interface DiagnosisListResponse {
  total: number;
  limit: number;
  offset: number;
  results: Diagnosis[];
}

// Care Plan Types
export interface CarePlan {
  id: number;
  patient: number;
  patient_name?: string;
  encounter?: number;
  title: string;
  category: string;
  status: string;
  description?: string;
  goals?: string[];
  activities?: string[];
  start_date: string;
  end_date?: string;
  addresses_diagnoses?: number[];
  diagnoses?: Diagnosis[];
  created_by: string;
  care_team?: string[];
  patient_instructions?: string;
  follow_up_instructions?: string;
  created_at: string;
  updated_at?: string;
}

export interface CarePlanListResponse {
  total: number;
  limit: number;
  offset: number;
  results: CarePlan[];
}

// Vitals Types
export interface VitalsRecord {
  id: number;
  patient: number;
  patient_name?: string;
  encounter?: number;
  heart_rate?: number;
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  blood_pressure?: string;
  respiratory_rate?: number;
  temperature?: number;
  oxygen_saturation?: number;
  weight?: number;
  height?: number;
  bmi?: number;
  pain_level?: number;
  glucose?: number;
  ecg_rhythm?: string;
  ecg_interpretation?: string;
  ecg_findings?: string[];
  recorded_at: string;
  recorded_by?: string;
  method?: string;
  device_id?: string;
  notes?: string;
  created_at: string;
}

export interface VitalsListResponse {
  total: number;
  limit: number;
  offset: number;
  results: VitalsRecord[];
}

// Patient Clinical Summary
export interface PatientClinicalSummary {
  patient_id: number;
  patient_name: string;
  patient_mrn: string;
  age: number;
  gender: string;
  active_encounters: Encounter[];
  recent_notes: ClinicalNote[];
  active_diagnoses: Diagnosis[];
  active_care_plans: CarePlan[];
  latest_vitals: VitalsRecord | null;
  allergies: string[];
  medications: string[];
}

// Constants
export const ENCOUNTER_TYPES = [
  { value: "ambulatory", label: "Ambulatory Visit" },
  { value: "emergency", label: "Emergency Visit" },
  { value: "inpatient", label: "Inpatient Stay" },
  { value: "observation", label: "Observation" },
  { value: "telehealth", label: "Telehealth" },
  { value: "home_health", label: "Home Health" },
  { value: "other", label: "Other" },
];

export const ENCOUNTER_STATUSES = [
  { value: "planned", label: "Planned" },
  { value: "in_progress", label: "In Progress" },
  { value: "on_hold", label: "On Hold" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export const NOTE_TYPES = [
  { value: "progress", label: "Progress Note" },
  { value: "admission", label: "Admission Note" },
  { value: "discharge", label: "Discharge Summary" },
  { value: "consultation", label: "Consultation Note" },
  { value: "procedure", label: "Procedure Note" },
  { value: "nursing", label: "Nursing Note" },
  { value: "soap", label: "SOAP Note" },
  { value: "history_physical", label: "History & Physical" },
  { value: "referral", label: "Referral Note" },
  { value: "other", label: "Other" },
];

export const NOTE_STATUSES = [
  { value: "draft", label: "Draft" },
  { value: "final", label: "Final" },
  { value: "amended", label: "Amended" },
  { value: "entered_in_error", label: "Entered in Error" },
];

export const DIAGNOSIS_CATEGORIES = [
  { value: "admitting", label: "Admitting Diagnosis" },
  { value: "working", label: "Working Diagnosis" },
  { value: "final", label: "Final Diagnosis" },
  { value: "discharge", label: "Discharge Diagnosis" },
  { value: "billing", label: "Billing Diagnosis" },
];

export const DIAGNOSIS_STATUSES = [
  { value: "active", label: "Active" },
  { value: "resolved", label: "Resolved" },
  { value: "inactive", label: "Inactive" },
  { value: "ruled_out", label: "Ruled Out" },
];

// Encounter API
export async function fetchEncounters(params?: {
  patient?: number;
  status?: string;
  type?: string;
  physician?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}): Promise<EncounterListResponse> {
  const res = await api.get<EncounterListResponse>("/api/v1/clinical/encounters/", { params });
  return res.data;
}

export async function fetchEncounter(encounterId: number): Promise<Encounter> {
  const res = await api.get<Encounter>(`/api/v1/clinical/encounters/${encounterId}/`);
  return res.data;
}

export async function createEncounter(data: Partial<Encounter>): Promise<Encounter> {
  const res = await api.post<Encounter>("/api/v1/clinical/encounters/", data);
  return res.data;
}

export async function updateEncounter(encounterId: number, data: Partial<Encounter>): Promise<Encounter> {
  const res = await api.put<Encounter>(`/api/v1/clinical/encounters/${encounterId}/`, data);
  return res.data;
}

export async function deleteEncounter(encounterId: number): Promise<void> {
  await api.delete(`/api/v1/clinical/encounters/${encounterId}/`);
}

// Clinical Notes API
export async function fetchNotes(params?: {
  patient?: number;
  encounter?: number;
  type?: string;
  status?: string;
  author?: string;
  limit?: number;
  offset?: number;
}): Promise<ClinicalNoteListResponse> {
  const res = await api.get<ClinicalNoteListResponse>("/api/v1/clinical/notes/", { params });
  return res.data;
}

export async function fetchNote(noteId: number): Promise<ClinicalNote> {
  const res = await api.get<ClinicalNote>(`/api/v1/clinical/notes/${noteId}/`);
  return res.data;
}

export async function createNote(data: Partial<ClinicalNote>): Promise<ClinicalNote> {
  const res = await api.post<ClinicalNote>("/api/v1/clinical/notes/", data);
  return res.data;
}

export async function updateNote(noteId: number, data: Partial<ClinicalNote>): Promise<ClinicalNote> {
  const res = await api.put<ClinicalNote>(`/api/v1/clinical/notes/${noteId}/`, data);
  return res.data;
}

export async function signNote(noteId: number, coSigner?: string): Promise<ClinicalNote> {
  const res = await api.post<ClinicalNote>(`/api/v1/clinical/notes/${noteId}/sign/`, { co_signer: coSigner });
  return res.data;
}

export async function deleteNote(noteId: number): Promise<void> {
  await api.delete(`/api/v1/clinical/notes/${noteId}/`);
}

// Diagnosis API
export async function fetchDiagnoses(params?: {
  patient?: number;
  encounter?: number;
  status?: string;
  icd10?: string;
  limit?: number;
  offset?: number;
}): Promise<DiagnosisListResponse> {
  const res = await api.get<DiagnosisListResponse>("/api/v1/clinical/diagnoses/", { params });
  return res.data;
}

export async function createDiagnosis(data: Partial<Diagnosis>): Promise<Diagnosis> {
  const res = await api.post<Diagnosis>("/api/v1/clinical/diagnoses/", data);
  return res.data;
}

export async function updateDiagnosis(diagnosisId: number, data: Partial<Diagnosis>): Promise<Diagnosis> {
  const res = await api.put<Diagnosis>(`/api/v1/clinical/diagnoses/${diagnosisId}/`, data);
  return res.data;
}

export async function deleteDiagnosis(diagnosisId: number): Promise<void> {
  await api.delete(`/api/v1/clinical/diagnoses/${diagnosisId}/`);
}

// Care Plan API
export async function fetchCarePlans(params?: {
  patient?: number;
  status?: string;
  category?: string;
  limit?: number;
  offset?: number;
}): Promise<CarePlanListResponse> {
  const res = await api.get<CarePlanListResponse>("/api/v1/clinical/careplans/", { params });
  return res.data;
}

export async function fetchCarePlan(planId: number): Promise<CarePlan> {
  const res = await api.get<CarePlan>(`/api/v1/clinical/careplans/${planId}/`);
  return res.data;
}

export async function createCarePlan(data: Partial<CarePlan>): Promise<CarePlan> {
  const res = await api.post<CarePlan>("/api/v1/clinical/careplans/", data);
  return res.data;
}

export async function updateCarePlan(planId: number, data: Partial<CarePlan>): Promise<CarePlan> {
  const res = await api.put<CarePlan>(`/api/v1/clinical/careplans/${planId}/`, data);
  return res.data;
}

export async function deleteCarePlan(planId: number): Promise<void> {
  await api.delete(`/api/v1/clinical/careplans/${planId}/`);
}

// Vitals API
export async function fetchVitals(params?: {
  patient?: number;
  encounter?: number;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}): Promise<VitalsListResponse> {
  const res = await api.get<VitalsListResponse>("/api/v1/clinical/vitals/", { params });
  return res.data;
}

export async function createVitals(data: Partial<VitalsRecord>): Promise<VitalsRecord> {
  const res = await api.post<VitalsRecord>("/api/v1/clinical/vitals/", data);
  return res.data;
}

// Patient Summary API
export async function fetchPatientClinicalSummary(patientId: number): Promise<PatientClinicalSummary> {
  const res = await api.get<PatientClinicalSummary>(`/api/v1/clinical/patient/${patientId}/summary/`);
  return res.data;
}
