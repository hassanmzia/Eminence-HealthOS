import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

// Create axios instance with auth interceptor
const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Types
export interface MedicationCatalog {
  id: number;
  rxnorm_code: string;
  ndc_code: string;
  generic_name: string;
  brand_names: string[];
  category: string;
  drug_class: string;
  form: string;
  route: string;
  strength: string;
  unit: string;
  typical_dose_min: number | null;
  typical_dose_max: number | null;
  max_daily_dose: number | null;
  frequency_options: string[];
  contraindications: string;
  warnings: string;
  side_effects: string;
  is_controlled: boolean;
  controlled_schedule: string;
  requires_monitoring: boolean;
  monitoring_parameters: string;
  is_high_alert: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MedicationCatalogList {
  id: number;
  rxnorm_code: string;
  generic_name: string;
  brand_names: string[];
  category: string;
  form: string;
  route: string;
  strength: string;
  is_controlled: boolean;
  is_high_alert: boolean;
  is_active: boolean;
}

export interface DrugInteraction {
  id: number;
  drug_a: number;
  drug_a_name: string;
  drug_b: number;
  drug_b_name: string;
  severity: "minor" | "moderate" | "major" | "contraindicated";
  description: string;
  clinical_effects: string;
  management: string;
  created_at: string;
}

export interface PatientAllergy {
  id: number;
  patient: number;
  patient_name: string;
  allergen_type: "drug" | "drug_class" | "ingredient";
  allergen_name: string;
  medication: number | null;
  medication_name: string | null;
  reaction_type: "allergy" | "intolerance" | "adverse_reaction";
  severity: "mild" | "moderate" | "severe" | "life_threatening";
  reaction_description: string;
  onset_date: string | null;
  is_active: boolean;
  verified: boolean;
  verified_by: string;
  verified_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Prescription {
  id: number;
  prescription_number: string;
  fhir_id: string;
  patient: number;
  patient_name: string;
  medication: number;
  medication_name: string;
  medication_details?: MedicationCatalogList;
  dose_quantity: number;
  dose_unit: string;
  route: string;
  frequency: string;
  frequency_hours: number | null;
  start_date: string;
  end_date: string | null;
  duration_days: number | null;
  quantity_prescribed: number | null;
  refills_allowed: number;
  refills_remaining: number;
  prn_reason: string;
  max_prn_doses_per_day: number | null;
  indication: string;
  diagnosis_codes: string[];
  special_instructions: string;
  prescriber_name: string;
  prescriber_id: string;
  prescriber_npi: string;
  status: "draft" | "pending" | "active" | "on_hold" | "completed" | "discontinued" | "cancelled";
  priority: "routine" | "urgent" | "stat" | "prn";
  pharmacy_notes: string;
  dispensed_at: string | null;
  dispensed_by: string;
  allergy_check_passed: boolean;
  interaction_check_passed: boolean;
  interaction_warnings: { severity: string; drug: string; description: string }[];
  hold_reason: string;
  held_at: string | null;
  held_by: string;
  discontinued_reason: string;
  discontinued_at: string | null;
  discontinued_by: string;
  prescribed_at: string;
  updated_at: string;
  administrations_count?: number;
  is_high_alert?: boolean;
}

export interface PrescriptionCreate {
  patient: number;
  medication: number;
  dose_quantity: number;
  dose_unit: string;
  route: string;
  frequency: string;
  frequency_hours?: number;
  start_date: string;
  end_date?: string;
  duration_days?: number;
  quantity_prescribed?: number;
  refills_allowed?: number;
  prn_reason?: string;
  max_prn_doses_per_day?: number;
  indication?: string;
  diagnosis_codes?: string[];
  special_instructions?: string;
  prescriber_name: string;
  prescriber_id?: string;
  prescriber_npi?: string;
  priority?: string;
}

export interface MedicationAdministration {
  id: number;
  prescription: number;
  prescription_number: string;
  medication_name: string;
  patient_name: string;
  fhir_id: string;
  scheduled_time: string;
  status: "scheduled" | "given" | "not_given" | "refused" | "held" | "missed";
  administered_at: string | null;
  administered_by: string;
  administered_by_id: string;
  dose_given: number | null;
  dose_unit: string;
  route_given: string;
  site: string;
  not_given_reason: string;
  not_given_details: string;
  witness_name: string;
  witness_id: string;
  patient_response: string;
  vital_signs_before: Record<string, unknown>;
  vital_signs_after: Record<string, unknown>;
  notes: string;
  is_high_alert: boolean;
  created_at: string;
  updated_at: string;
}

export interface MedicationStats {
  prescriptions: {
    total: number;
    active: number;
    pending_review: number;
    high_alert_active: number;
    controlled_active: number;
  };
  administrations_today: {
    due_now: number;
    given: number;
    missed: number;
    total_scheduled: number;
  };
  category_breakdown: { category: string; count: number }[];
  catalog_size: number;
}

export interface PatientMedicationHistory {
  prescriptions: {
    active: Prescription[];
    on_hold: Prescription[];
    completed: Prescription[];
  };
  allergies: PatientAllergy[];
  recent_administrations: MedicationAdministration[];
}

// Medication Catalog API
export async function fetchMedications(params?: {
  category?: string;
  form?: string;
  route?: string;
  is_controlled?: boolean;
  is_high_alert?: boolean;
  is_active?: boolean;
  search?: string;
}): Promise<MedicationCatalogList[]> {
  const response = await api.get("/medications/catalog/", { params });
  return response.data;
}

export async function fetchMedication(id: number): Promise<MedicationCatalog> {
  const response = await api.get(`/medications/catalog/${id}/`);
  return response.data;
}

export async function seedMedicationCatalog(): Promise<{ message: string; total: number }> {
  const response = await api.post("/medications/catalog/seed/");
  return response.data;
}

// Drug Interactions API
export async function checkDrugInteractions(medicationIds: number[]): Promise<{
  interactions: DrugInteraction[];
  has_major: boolean;
  count: number;
}> {
  const response = await api.post("/medications/interactions/check/", {
    medication_ids: medicationIds,
  });
  return response.data;
}

// Patient Allergies API
export async function fetchPatientAllergies(patientId: number): Promise<PatientAllergy[]> {
  const response = await api.get("/medications/allergies/", {
    params: { patient_id: patientId, is_active: true },
  });
  return response.data;
}

export async function createPatientAllergy(data: Partial<PatientAllergy>): Promise<PatientAllergy> {
  const response = await api.post("/medications/allergies/", data);
  return response.data;
}

export async function checkMedicationSafety(
  patientId: number,
  medicationId: number
): Promise<{
  safe: boolean;
  warnings: { type: string; severity: string; allergen: string; reaction: string }[];
  medication: string;
}> {
  const response = await api.post("/medications/allergies/check_medication/", {
    patient_id: patientId,
    medication_id: medicationId,
  });
  return response.data;
}

// Prescriptions API
export async function fetchPrescriptions(params?: {
  patient_id?: number;
  status?: string;
  active?: boolean;
  priority?: string;
  prescriber?: string;
}): Promise<Prescription[]> {
  const response = await api.get("/medications/prescriptions/", { params });
  return response.data;
}

export async function fetchPrescription(id: number): Promise<Prescription> {
  const response = await api.get(`/medications/prescriptions/${id}/`);
  return response.data;
}

export async function createPrescription(data: PrescriptionCreate): Promise<Prescription> {
  const response = await api.post("/medications/prescriptions/", data);
  return response.data;
}

export async function activatePrescription(id: number): Promise<Prescription> {
  const response = await api.post(`/medications/prescriptions/${id}/activate/`);
  return response.data;
}

export async function holdPrescription(id: number, reason: string, heldBy: string): Promise<Prescription> {
  const response = await api.post(`/medications/prescriptions/${id}/hold/`, {
    reason,
    held_by: heldBy,
  });
  return response.data;
}

export async function resumePrescription(id: number): Promise<Prescription> {
  const response = await api.post(`/medications/prescriptions/${id}/resume/`);
  return response.data;
}

export async function discontinuePrescription(
  id: number,
  reason: string,
  discontinuedBy: string
): Promise<Prescription> {
  const response = await api.post(`/medications/prescriptions/${id}/discontinue/`, {
    reason,
    discontinued_by: discontinuedBy,
  });
  return response.data;
}

// Medication Administrations API
export async function fetchAdministrations(params?: {
  prescription_id?: number;
  patient_id?: number;
  status?: string;
  date_from?: string;
  date_to?: string;
  due?: boolean;
}): Promise<MedicationAdministration[]> {
  const response = await api.get("/medications/administrations/", { params });
  return response.data;
}

export async function administerMedication(
  id: number,
  data: {
    administered_by: string;
    administered_by_id?: string;
    dose_given?: number;
    dose_unit?: string;
    route_given?: string;
    site?: string;
    witness_name?: string;
    witness_id?: string;
    patient_response?: string;
    vital_signs_before?: Record<string, unknown>;
    vital_signs_after?: Record<string, unknown>;
    notes?: string;
  }
): Promise<MedicationAdministration> {
  const response = await api.post(`/medications/administrations/${id}/administer/`, data);
  return response.data;
}

export async function recordNotGiven(
  id: number,
  data: {
    reason: string;
    details?: string;
    documented_by: string;
    notes?: string;
  }
): Promise<MedicationAdministration> {
  const response = await api.post(`/medications/administrations/${id}/not_given/`, data);
  return response.data;
}

// Patient Medication History API
export async function fetchPatientMedicationHistory(patientId: number): Promise<PatientMedicationHistory> {
  const response = await api.get(`/medications/patient/${patientId}/history/`);
  return response.data;
}

// Stats API
export async function fetchMedicationStats(): Promise<MedicationStats> {
  const response = await api.get("/medications/stats/");
  return response.data;
}
