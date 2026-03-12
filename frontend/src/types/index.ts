// ── Patient ──────────────────────────────────────────────────────────────────

export interface Patient {
  id: string;
  org_id: string;
  fhir_id?: string;
  mrn?: string;
  demographics: {
    name: string;
    dob: string;
    gender: string;
    first_name?: string;
    last_name?: string;
    date_of_birth?: string;
    phone?: string;
    email?: string;
    address?: string;
  };
  conditions: Condition[];
  medications: Medication[];
  risk_level: RiskLevel;
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
  name: string;
  role: string;
}

// ── Vitals ───────────────────────────────────────────────────────────────────

export type VitalType =
  | "heart_rate"
  | "blood_pressure"
  | "glucose"
  | "spo2"
  | "weight"
  | "temperature"
  | "respiratory_rate";

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

// ── Alerts ───────────────────────────────────────────────────────────────────

export type AlertType =
  | "patient_notification"
  | "nurse_review"
  | "physician_review"
  | "telehealth_trigger"
  | "emergency";

export type AlertStatus = "pending" | "acknowledged" | "resolved";

export interface Alert {
  id: string;
  patient_id: string;
  alert_type: AlertType;
  priority: Severity;
  status: AlertStatus;
  message: string;
  assigned_to?: string;
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

// ── Risk & Anomalies ─────────────────────────────────────────────────────────

export type Severity = "low" | "moderate" | "high" | "critical";
export type RiskLevel = "low" | "moderate" | "high" | "critical";

export interface RiskScore {
  id: string;
  patient_id: string;
  score_type: string;
  score: number;
  risk_level: RiskLevel;
  factors: RiskFactor[];
  created_at: string;
}

export interface RiskFactor {
  factor: string;
  weight: number;
  contribution: number;
}

// ── Agents ───────────────────────────────────────────────────────────────────

export type AgentTier =
  | "sensing"
  | "interpretation"
  | "decisioning"
  | "action"
  | "measurement";

export interface AgentInfo {
  name: string;
  tier: AgentTier;
  version: string;
  description: string;
  requires_hitl: boolean;
}

// ── WebSocket Events ─────────────────────────────────────────────────────────

export interface WSEvent {
  event_type: string;
  data: Record<string, unknown>;
  timestamp: string;
}
