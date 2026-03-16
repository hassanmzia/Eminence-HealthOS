import axios from "axios";
import { api } from "./http";

// Orchestrator API for AI services
const orchestrator = axios.create({
  baseURL: import.meta.env.VITE_ORCH_BASE || import.meta.env.VITE_ORCHESTRATOR_BASE || "http://localhost:8003",
  timeout: 60000, // Longer timeout for AI processing
});

export type Recommendation = {
  id: number;
  patient_id?: string;
  created_at: string;
  severity?: "info" | "warning" | "critical";
  title: string;
  summary: string;
  rationale?: string;
  evidence?: Array<{ source: string; snippet: string }>;
};

export async function fetchRecommendations(patientId?: string) {
  const params = patientId ? { patient_id: patientId } : {};
  const res = await api.get<Recommendation[]>("/api/v1/recommendations/", { params });
  return res.data;
}

// Clinical Assessment Types
export type ClinicalFinding = {
  type: string;
  name: string;
  value: string | number;
  unit?: string;
  status: "normal" | "abnormal" | "critical";
  interpretation: string;
  source: string;
  reference_range?: string;
};

export type DiagnosisRecommendation = {
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
};

export type TreatmentRecommendation = {
  treatment_type: string;
  description: string;
  priority: string;
  rationale: string;
  cpt_code?: string;
  contraindications?: string[];
  monitoring?: string[];
};

export type ClinicalAssessment = {
  patient_summary: {
    patient_id: string;
    name?: string;
    age?: number;
    sex?: string;
  };
  findings: ClinicalFinding[];
  critical_findings: ClinicalFinding[];
  diagnoses: DiagnosisRecommendation[];
  treatments: TreatmentRecommendation[];
  icd10_codes: Array<{ code: string; description: string; category: string; confidence: number }>;
  cpt_codes: Array<{ code: string; description: string; category: string }>;
  confidence: number;
  reasoning: string[];
  warnings: string[];
  requires_human_review: boolean;
  review_reason?: string;
  assessment_id?: string;
  persisted_recommendation_id?: number;
};

export type AssessmentResponse = {
  success: boolean;
  patient_id: string;
  assessment?: ClinicalAssessment;
  error?: string;
  llm_provider?: string;
};

export type LLMStatus = {
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
};

export type AgentInfo = {
  agent_id: string;
  name: string;
  description: string;
  version: string;
  specialties: string[];
  capabilities: Array<{
    name: string;
    description: string;
  }>;
};

// Fetch comprehensive clinical assessment
export async function fetchClinicalAssessment(patientId: string, fhirId?: string): Promise<AssessmentResponse> {
  const res = await orchestrator.post<AssessmentResponse>("/api/v1/assess", {
    patient_id: patientId,
    fhir_id: fhirId,
    include_diagnoses: true,
    include_treatments: true,
    include_codes: true,
  });
  return res.data;
}

// Get quick assessment via GET
export async function getQuickAssessment(patientId: string): Promise<AssessmentResponse> {
  const res = await orchestrator.get<AssessmentResponse>(`/api/v1/assess/${patientId}`);
  return res.data;
}

// Get LLM status
export async function fetchLLMStatus(): Promise<LLMStatus> {
  const res = await orchestrator.get<LLMStatus>("/api/v1/llm/status");
  return res.data;
}

// Switch LLM provider
export async function switchLLMProvider(provider: string): Promise<{ success: boolean; new_provider: string }> {
  const res = await orchestrator.post(`/api/v1/llm/switch?provider=${provider}`);
  return res.data;
}

// Get available agents
export async function fetchAgents(): Promise<{ agents: AgentInfo[] }> {
  const res = await orchestrator.get<{ agents: AgentInfo[] }>("/api/v1/agents");
  return res.data;
}

// Get MCP server status
export async function fetchMCPStatus(): Promise<{ mcp_servers: Record<string, { url: string; status: string; error?: string }> }> {
  const res = await orchestrator.get("/api/v1/mcp/status");
  return res.data;
}

// =============================================================================
// Physician Review API Types and Functions
// =============================================================================

export type PhysicianReviewSubmission = {
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
  added_diagnoses?: Array<Record<string, unknown>>;
  added_treatments?: Array<Record<string, unknown>>;
  physician_notes?: string;
  rejection_reason?: string;
  clinical_rationale?: string;
  attest: boolean;
  review_started_at?: string;
};

export type PhysicianReview = {
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
};

export type ClinicalDocument = {
  id: string;
  assessment: string;
  document_type: string;
  title: string;
  format: string;
  status: string;
  content: string;
  created_at: string;
};

export type EHROrder = {
  id: string;
  order_type: string;
  status: string;
  description: string;
  cpt_code?: string;
  ehr_order_id?: string;
  created_at: string;
};

// Submit physician review
export async function submitPhysicianReview(review: PhysicianReviewSubmission): Promise<PhysicianReview> {
  const res = await api.post<PhysicianReview>("/api/v1/clinical/reviews/submit/", review);
  return res.data;
}

// Get review details
export async function fetchPhysicianReview(reviewId: string): Promise<PhysicianReview> {
  const res = await api.get<PhysicianReview>(`/api/v1/clinical/reviews/${reviewId}/`);
  return res.data;
}

// Generate clinical document
export async function generateClinicalDocument(
  assessmentId: string,
  reviewId?: string,
  documentType: string = "assessment_summary",
  format: string = "html",
  includeReasoning: boolean = false
): Promise<ClinicalDocument> {
  const res = await api.post<ClinicalDocument>("/api/v1/clinical/documents/generate/", {
    assessment_id: assessmentId,
    review_id: reviewId,
    document_type: documentType,
    format,
    include_reasoning: includeReasoning,
    include_codes: true,
  });
  return res.data;
}

// Download clinical document as PDF or HTML
export function getDocumentDownloadUrl(documentId: string, format: string = "pdf"): string {
  const baseUrl = api.defaults.baseURL || "";
  return `${baseUrl}/api/v1/clinical/documents/${documentId}/download/?download_format=${format}`;
}

export async function downloadClinicalDocument(documentId: string, title: string, format: string = "pdf"): Promise<void> {
  const res = await api.get(`/api/v1/clinical/documents/${documentId}/download/`, {
    params: { format },
    responseType: "blob",
  });
  const blob = new Blob([res.data], {
    type: format === "pdf" ? "application/pdf" : "text/html",
  });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${title.replace(/\s+/g, "_").replace(/\//g, "-")}.${format === "pdf" ? "pdf" : "html"}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

// Create EHR orders from approved treatments
export async function createEHROrders(
  assessmentId: string,
  reviewId: string,
  treatmentIndices: number[],
  physicianId: string,
  physicianName: string,
  physicianNpi?: string
): Promise<{ success: boolean; orders_created: number; orders: EHROrder[] }> {
  const res = await api.post("/api/v1/clinical/orders/create/", {
    assessment_id: assessmentId,
    review_id: reviewId,
    treatment_indices: treatmentIndices,
    ordering_physician_id: physicianId,
    ordering_physician_name: physicianName,
    ordering_physician_npi: physicianNpi || "",
  });
  return res.data;
}

// Get audit logs for an assessment
export async function fetchAssessmentAuditLogs(assessmentId: string): Promise<{ total: number; results: Array<{
  id: string;
  action: string;
  action_detail: string;
  actor_name: string;
  timestamp: string;
}> }> {
  const res = await api.get(`/api/v1/clinical/assessments/${assessmentId}/audit/`);
  return res.data;
}
