/** HealthOS API type definitions */

export interface Organization {
  id: string;
  name: string;
  slug: string;
  tier: string;
}

export interface Patient {
  id: string;
  org_id: string;
  fhir_id?: string;
  mrn?: string;
  demographics: {
    first_name: string;
    last_name: string;
    date_of_birth: string;
    gender: string;
    phone?: string;
    email?: string;
    address?: string;
  };
  conditions: Condition[];
  medications: Medication[];
  risk_level: "low" | "moderate" | "high" | "critical";
  care_team: CareTeamMember[];
  created_at: string;
  updated_at: string;
}

export interface Condition {
  code: string;
  display: string;
  onset_date?: string;
  status: string;
}

export interface Medication {
  name: string;
  dosage: string;
  frequency: string;
  status: string;
}

export interface CareTeamMember {
  user_id: string;
  role: string;
  name: string;
}

export interface Vital {
  id: string;
  patient_id: string;
  vital_type: VitalType;
  value: Record<string, number>;
  unit: string;
  recorded_at: string;
  source: string;
  quality_score: number;
}

export type VitalType =
  | "heart_rate"
  | "blood_pressure"
  | "glucose"
  | "spo2"
  | "weight"
  | "temperature"
  | "respiratory_rate"
  | "activity"
  | "sleep";

export interface Alert {
  id: string;
  patient_id: string;
  anomaly_id?: string;
  alert_type: AlertType;
  priority: Severity;
  status: "pending" | "acknowledged" | "resolved" | "escalated";
  message: string;
  assigned_to?: string;
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

export type AlertType =
  | "patient_notification"
  | "nurse_review"
  | "physician_review"
  | "telehealth_trigger"
  | "emergency";

export type Severity = "low" | "moderate" | "high" | "critical";

export interface RiskScore {
  id: string;
  patient_id: string;
  score_type: string;
  score: number;
  risk_level: Severity;
  factors: RiskFactor[];
  model_version: string;
  created_at: string;
}

export interface RiskFactor {
  factor: string;
  weight: number;
  contribution: number;
  count?: number;
}

export interface AgentInfo {
  name: string;
  tier: string;
  version: string;
  description: string;
  requires_hitl: boolean;
}

export interface AgentExecution {
  trace_id: string;
  agent_name: string;
  status: "idle" | "running" | "completed" | "failed" | "waiting_hitl";
  confidence: number;
  duration_ms: number;
  timestamp: string;
}

/** WebSocket event types */
export interface WSEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}
