import { api } from "./http";

// Overview Stats
export interface OverviewStats {
  patients: {
    total: number;
    active: number;
    new_this_week: number;
  };
  devices: {
    total: number;
    active: number;
    assigned: number;
    unassigned: number;
  };
  alerts: {
    active: number;
    critical: number;
    today: number;
    this_week: number;
  };
  encounters: {
    active: number;
    today: number;
  };
  generated_at: string;
}

// Vitals Analytics
export interface VitalsAnalytics {
  period_days: number;
  statistics: {
    avg_heart_rate: number | null;
    max_heart_rate: number | null;
    min_heart_rate: number | null;
    avg_systolic: number | null;
    max_systolic: number | null;
    min_systolic: number | null;
    avg_diastolic: number | null;
    avg_spo2: number | null;
    min_spo2: number | null;
    avg_temp: number | null;
    max_temp: number | null;
    avg_resp_rate: number | null;
    total_readings: number;
  };
  daily_trends: Array<{
    date: string;
    readings: number;
    avg_heart_rate: number | null;
    avg_systolic: number | null;
    avg_diastolic: number | null;
    avg_spo2: number | null;
    avg_temp: number | null;
  }>;
  abnormal_counts: {
    high_heart_rate: number;
    low_heart_rate: number;
    high_bp: number;
    low_spo2: number;
    fever: number;
  };
  generated_at: string;
}

// Alert Analytics
export interface AlertAnalytics {
  period_days: number;
  total_alerts: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_vital_type: Record<string, number>;
  daily_trends: Array<{
    date: string;
    total: number;
    critical: number;
    warning: number;
    info: number;
  }>;
  hourly_distribution: Array<{
    hour: number;
    count: number;
  }>;
  response_metrics: {
    avg_response_time_seconds: number | null;
    total_acknowledged: number;
  };
  top_rules: Array<{
    rule__name: string;
    rule__severity: string;
    count: number;
  }>;
  top_patients: Array<{
    patient__first_name: string;
    patient__last_name: string;
    patient_id: number;
    alert_count: number;
    critical_count: number;
  }>;
  generated_at: string;
}

// Device Analytics
export interface DeviceAnalytics {
  total_devices: number;
  status_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
  assignment_stats: {
    assigned: number;
    unassigned: number;
    utilization_rate: number;
  };
  assignment_trends: Array<{
    date: string;
    new_assignments: number;
  }>;
  capability_distribution: Record<string, number>;
  most_used_devices: Array<{
    device_id: string;
    name: string;
    device_type: string;
    assignment_count: number;
  }>;
  needs_attention: number;
  generated_at: string;
}

// Patient Analytics
export interface PatientAnalytics {
  total_patients: number;
  active_patients: number;
  gender_distribution: Record<string, number>;
  age_distribution: Record<string, number>;
  new_patient_trends: Array<{
    date: string;
    count: number;
  }>;
  engagement: {
    with_active_alerts: number;
    in_encounters: number;
    with_devices: number;
  };
  top_diagnoses: Array<{
    icd10_code: string;
    description: string;
    patient_count: number;
  }>;
  generated_at: string;
}

// Clinical Analytics
export interface ClinicalAnalytics {
  encounters: {
    by_type: Record<string, number>;
    by_status: Record<string, number>;
    trends: Array<{
      date: string;
      count: number;
    }>;
    total: number;
    active: number;
  };
  notes: {
    by_type: Record<string, number>;
    by_status: Record<string, number>;
    total: number;
    this_week: number;
    top_authors: Array<{
      author: string;
      note_count: number;
    }>;
  };
  care_plans: {
    by_status: Record<string, number>;
    by_category: Record<string, number>;
    total: number;
    active: number;
  };
  diagnoses: {
    by_status: Record<string, number>;
    by_category: Record<string, number>;
    total: number;
    active: number;
  };
  generated_at: string;
}

// API Functions
export async function fetchOverviewStats(): Promise<OverviewStats> {
  const res = await api.get<OverviewStats>("/api/v1/analytics/overview/");
  return res.data;
}

export async function fetchVitalsAnalytics(params?: {
  patient_id?: number;
  days?: number;
}): Promise<VitalsAnalytics> {
  const res = await api.get<VitalsAnalytics>("/api/v1/analytics/vitals/", { params });
  return res.data;
}

export async function fetchAlertAnalytics(params?: {
  patient_id?: number;
  days?: number;
}): Promise<AlertAnalytics> {
  const res = await api.get<AlertAnalytics>("/api/v1/analytics/alerts/", { params });
  return res.data;
}

export async function fetchDeviceAnalytics(): Promise<DeviceAnalytics> {
  const res = await api.get<DeviceAnalytics>("/api/v1/analytics/devices/");
  return res.data;
}

export async function fetchPatientAnalytics(): Promise<PatientAnalytics> {
  const res = await api.get<PatientAnalytics>("/api/v1/analytics/patients/");
  return res.data;
}

export async function fetchClinicalAnalytics(): Promise<ClinicalAnalytics> {
  const res = await api.get<ClinicalAnalytics>("/api/v1/analytics/clinical/");
  return res.data;
}
