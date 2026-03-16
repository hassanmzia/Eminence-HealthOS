import { api } from "./http";

export interface Alert {
  id: number;
  patient: number;
  patient_name?: string;
  patient_mrn?: string;
  device?: number;
  device_name?: string;
  rule?: number;
  rule_name?: string;
  vital_type: string;
  vital_value: number;
  threshold_value: number;
  condition?: string;
  severity: "info" | "warning" | "critical";
  severity_display?: string;
  status: "active" | "acknowledged" | "resolved" | "escalated" | "auto_resolved";
  status_display?: string;
  title: string;
  message?: string;
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  escalated_at?: string;
  acknowledged_by?: string;
  resolved_by?: string;
  resolution_notes?: string;
  fhir_observation_id?: string;
  duration_seconds?: number;
}

export interface AlertRule {
  id: number;
  name: string;
  description?: string;
  vital_type: string;
  vital_type_display?: string;
  condition: string;
  condition_display?: string;
  threshold_value: number;
  threshold_value_high?: number;
  severity: "info" | "warning" | "critical";
  severity_display?: string;
  patient?: number;
  patient_name?: string;
  is_active: boolean;
  cooldown_minutes: number;
  auto_acknowledge_minutes: number;
  notify_on_trigger: boolean;
  escalate_after_minutes: number;
  created_at: string;
  updated_at?: string;
  created_by?: string;
}

export interface AlertSummary {
  total_active: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  acknowledged_today: number;
  resolved_today: number;
  escalated_count: number;
  average_response_time_seconds: number | null;
}

export interface AlertListResponse {
  total: number;
  limit: number;
  offset: number;
  results: Alert[];
}

export interface AlertRuleListResponse {
  results: AlertRule[];
}

// Constants
export const VITAL_TYPES = [
  { value: "heart_rate", label: "Heart Rate", unit: "bpm" },
  { value: "blood_pressure_systolic", label: "Blood Pressure (Systolic)", unit: "mmHg" },
  { value: "blood_pressure_diastolic", label: "Blood Pressure (Diastolic)", unit: "mmHg" },
  { value: "oxygen_saturation", label: "Oxygen Saturation (SpO2)", unit: "%" },
  { value: "temperature", label: "Temperature", unit: "°C" },
  { value: "respiratory_rate", label: "Respiratory Rate", unit: "/min" },
  { value: "glucose", label: "Blood Glucose", unit: "mg/dL" },
];

export const CONDITIONS = [
  { value: "gt", label: "Greater Than", symbol: ">" },
  { value: "gte", label: "Greater Than or Equal", symbol: ">=" },
  { value: "lt", label: "Less Than", symbol: "<" },
  { value: "lte", label: "Less Than or Equal", symbol: "<=" },
  { value: "eq", label: "Equal To", symbol: "=" },
  { value: "range_outside", label: "Outside Range", symbol: "< or >" },
];

export const SEVERITIES = [
  { value: "info", label: "Information", color: "#3b82f6", bg: "#dbeafe" },
  { value: "warning", label: "Warning", color: "#f59e0b", bg: "#fef3c7" },
  { value: "critical", label: "Critical", color: "#ef4444", bg: "#fee2e2" },
];

// Alert API
export async function fetchAlerts(params?: {
  status?: string;
  severity?: string;
  patient?: number;
  vital_type?: string;
  start_date?: string;
  end_date?: string;
  active_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<AlertListResponse> {
  const res = await api.get<AlertListResponse>("/api/v1/alerts/", {
    params: {
      ...params,
      active_only: params?.active_only ? "true" : undefined,
    }
  });
  return res.data;
}

export async function fetchAlert(alertId: number): Promise<Alert> {
  const res = await api.get<Alert>(`/api/v1/alerts/${alertId}/`);
  return res.data;
}

export async function acknowledgeAlert(alertId: number, data: { acknowledged_by: string; notes?: string }): Promise<Alert> {
  const res = await api.post<Alert>(`/api/v1/alerts/${alertId}/acknowledge/`, data);
  return res.data;
}

export async function resolveAlert(alertId: number, data: { resolved_by: string; resolution_notes?: string }): Promise<Alert> {
  const res = await api.post<Alert>(`/api/v1/alerts/${alertId}/resolve/`, data);
  return res.data;
}

export async function bulkAcknowledgeAlerts(alertIds: number[], acknowledgedBy: string): Promise<{ acknowledged_count: number }> {
  const res = await api.post("/api/v1/alerts/bulk-acknowledge/", {
    alert_ids: alertIds,
    acknowledged_by: acknowledgedBy,
  });
  return res.data;
}

export async function fetchAlertSummary(): Promise<AlertSummary> {
  const res = await api.get<AlertSummary>("/api/v1/alerts/summary/");
  return res.data;
}

// Alert Rules API
export async function fetchAlertRules(params?: {
  active?: boolean;
  vital_type?: string;
  severity?: string;
  patient?: number | "global";
}): Promise<AlertRuleListResponse> {
  const res = await api.get<AlertRuleListResponse>("/api/v1/alerts/rules/", {
    params: {
      ...params,
      active: params?.active !== undefined ? String(params.active) : undefined,
    }
  });
  return res.data;
}

export async function fetchAlertRule(ruleId: number): Promise<AlertRule> {
  const res = await api.get<AlertRule>(`/api/v1/alerts/rules/${ruleId}/`);
  return res.data;
}

export async function createAlertRule(data: Partial<AlertRule>): Promise<AlertRule> {
  const res = await api.post<AlertRule>("/api/v1/alerts/rules/", data);
  return res.data;
}

export async function updateAlertRule(ruleId: number, data: Partial<AlertRule>): Promise<AlertRule> {
  const res = await api.put<AlertRule>(`/api/v1/alerts/rules/${ruleId}/`, data);
  return res.data;
}

export async function deleteAlertRule(ruleId: number): Promise<void> {
  await api.delete(`/api/v1/alerts/rules/${ruleId}/`);
}

export async function initializeDefaultRules(): Promise<{ message: string; total_rules: number }> {
  const res = await api.post("/api/v1/alerts/rules/initialize-defaults/");
  return res.data;
}

// Patient Alerts API
export async function fetchPatientAlerts(patientId: number, activeOnly?: boolean): Promise<{ results: Alert[] }> {
  const res = await api.get(`/api/v1/alerts/patient/${patientId}/`, {
    params: { active_only: activeOnly ? "true" : undefined }
  });
  return res.data;
}

// Helper functions
export function getVitalTypeLabel(vitalType: string): string {
  return VITAL_TYPES.find(v => v.value === vitalType)?.label || vitalType;
}

export function getVitalTypeUnit(vitalType: string): string {
  return VITAL_TYPES.find(v => v.value === vitalType)?.unit || "";
}

export function getSeverityColor(severity: string): { color: string; bg: string } {
  return SEVERITIES.find(s => s.value === severity) || { color: "#666", bg: "#f3f4f6" };
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
}
