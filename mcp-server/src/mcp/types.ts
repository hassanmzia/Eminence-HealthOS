/**
 * Eminence HealthOS — MCP Type Definitions
 * TypeScript interfaces for the Model Context Protocol server.
 */

// ── Patient Context ─────────────────────────────────────────────────────────

export interface PatientDemographics {
  id: string;
  mrn: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  gender: string;
  race?: string;
  ethnicity?: string;
  language?: string;
  insurancePlan?: string;
  primaryPhysician?: string;
}

export interface Condition {
  id: string;
  code: string;
  codeSystem: string;
  display: string;
  category: string;
  clinicalStatus: string;
  onsetDate?: string;
  severity?: string;
}

export interface Medication {
  id: string;
  code: string;
  codeSystem: string;
  display: string;
  dosage: string;
  route: string;
  frequency: string;
  status: string;
  prescribedDate: string;
  rxNormCode?: string;
}

export interface Vital {
  type: string;
  value: number | Record<string, number>;
  unit: string;
  recordedAt: string;
  source: string;
  qualityScore: number;
}

export interface Allergy {
  id: string;
  substance: string;
  reaction: string;
  severity: string;
  status: string;
  recordedDate: string;
}

export interface RiskScore {
  scoreType: string;
  score: number;
  riskLevel: "low" | "medium" | "high" | "critical";
  contributingFactors: Array<{ factor: string; weight: number }>;
  modelVersion: string;
  calculatedAt: string;
}

export interface EncounterNote {
  id: string;
  type: string;
  date: string;
  provider: string;
  chiefComplaint?: string;
  assessment?: string;
  plan?: string;
}

export interface CareGap {
  id: string;
  gapType: string;
  description: string;
  priority: string;
  dueDate?: string;
  status: string;
}

// ── MCP Context ─────────────────────────────────────────────────────────────

export interface PatientContext {
  demographics: PatientDemographics;
  conditions: Condition[];
  medications: Medication[];
  vitals: Vital[];
  allergies: Allergy[];
  riskScores: RiskScore[];
  encounters: EncounterNote[];
  careGaps: CareGap[];
}

export interface ClinicalConstraints {
  guidelines: Array<{ source: string; recommendation: string; evidenceLevel: string }>;
  contraindications: Array<{ drug: string; condition: string; severity: string }>;
  protocols: Array<{ name: string; steps: string[]; applicability: number }>;
}

export interface MCPContext {
  version: string;
  timestamp: string;
  patient: PatientContext;
  constraints: ClinicalConstraints;
  metadata: Record<string, unknown>;
}

// ── MCP Tools ───────────────────────────────────────────────────────────────

export interface MCPToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface MCPToolCall {
  tool: string;
  arguments: Record<string, unknown>;
  callId: string;
}

export interface MCPToolResult {
  callId: string;
  tool: string;
  success: boolean;
  result: unknown;
  error?: string;
  durationMs: number;
}

// ── Drug Interactions ───────────────────────────────────────────────────────

export interface DrugInteraction {
  drug1: string;
  drug2: string;
  severity: "contraindicated" | "major" | "moderate" | "minor";
  description: string;
  management: string;
  source: string;
}

// ── Notifications ───────────────────────────────────────────────────────────

export interface NotificationRequest {
  recipientId: string;
  recipientType: "patient" | "physician" | "nurse" | "care_team";
  channel: "sms" | "email" | "push" | "in_app";
  priority: "critical" | "high" | "normal" | "low";
  subject: string;
  body: string;
  metadata?: Record<string, unknown>;
}

// ── Appointments ────────────────────────────────────────────────────────────

export interface AppointmentRequest {
  patientId: string;
  providerId: string;
  appointmentType: string;
  preferredDate?: string;
  urgency: "stat" | "urgent" | "routine";
  reason: string;
  duration?: number;
}

// ── Audit ───────────────────────────────────────────────────────────────────

export interface AuditLog {
  timestamp: string;
  userId: string;
  action: string;
  resource: string;
  resourceId: string;
  details: Record<string, unknown>;
  ipAddress?: string;
}

// ── MCP Protocol Messages ───────────────────────────────────────────────────

export interface MCPRequest {
  version: string;
  method: string;
  params: Record<string, unknown>;
  id: string;
}

export interface MCPResponse {
  version: string;
  result?: unknown;
  error?: { code: number; message: string };
  id: string;
}
