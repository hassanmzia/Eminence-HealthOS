import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchClinicalAssessment,
  fetchLLMStatus,
  submitPhysicianReview,
  generateClinicalDocument,
  downloadClinicalDocument,
  createEHROrders,
  type AssessmentResponse,
  type ClinicalAssessment,
  type ClinicalFinding,
  type DiagnosisRecommendation,
  type TreatmentRecommendation,
  type PhysicianReview,
  type ClinicalDocument,
  type EHROrder,
} from "../lib/api";
import type { Patient } from "../lib/patientApi";
import type { PatientClinicalSummary } from "../lib/clinicalApi";

type Props = {
  patientId: string;
  fhirId?: string;
  patient?: Patient;
  clinicalSummary?: PatientClinicalSummary | null;
};

type ReviewState = {
  approvedDiagnoses: Set<number>;
  approvedTreatments: Set<number>;
  physicianNotes: string;
  reviewStatus: "pending" | "approved" | "rejected" | "modified";
  submittedReview?: PhysicianReview;
  generatedDocument?: ClinicalDocument;
  ehrOrders?: EHROrder[];
};

export function ClinicalAssessmentPanel({ patientId, fhirId, patient, clinicalSummary }: Props) {
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [showReasoning, setShowReasoning] = useState(false);
  const [reviewState, setReviewState] = useState<ReviewState>({
    approvedDiagnoses: new Set(),
    approvedTreatments: new Set(),
    physicianNotes: "",
    reviewStatus: "pending",
  });
  const [isReviewing, setIsReviewing] = useState(false);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewStartedAt, setReviewStartedAt] = useState<string | null>(null);

  // Fetch LLM status
  const llmStatusQuery = useQuery({
    queryKey: ["llm-status"],
    queryFn: fetchLLMStatus,
    refetchInterval: 30000,
  });

  // Run assessment mutation
  const assessmentMutation = useMutation({
    mutationFn: () => fetchClinicalAssessment(patientId, fhirId),
    onSuccess: (data) => {
      setAssessment(data);
      // Initialize review state with all items approved by default
      if (data.assessment) {
        setReviewState({
          approvedDiagnoses: new Set(data.assessment.diagnoses.map((_, i) => i)),
          approvedTreatments: new Set(data.assessment.treatments.map((_, i) => i)),
          physicianNotes: "",
          reviewStatus: "pending",
        });
      }
      setIsReviewing(false);
      setReviewStartedAt(null);
    },
  });

  // Submit physician review mutation
  const reviewMutation = useMutation({
    mutationFn: submitPhysicianReview,
    onSuccess: (data) => {
      setReviewState(prev => ({
        ...prev,
        submittedReview: data,
      }));
      setIsSubmittingReview(false);
    },
    onError: (error) => {
      console.error("Review submission failed:", error);
      setIsSubmittingReview(false);
      alert(`Failed to submit review: ${(error as Error).message}`);
    },
  });

  // Generate clinical document mutation
  const documentMutation = useMutation({
    mutationFn: (params: { assessmentId: string; reviewId?: string }) =>
      generateClinicalDocument(params.assessmentId, params.reviewId, "assessment_summary", "html", true),
    onSuccess: (data) => {
      setReviewState(prev => ({
        ...prev,
        generatedDocument: data,
      }));
    },
    onError: (error) => {
      console.error("Document generation failed:", error);
      alert(`Failed to generate document: ${(error as Error).message}`);
    },
  });

  // Create EHR orders mutation
  const ehrOrdersMutation = useMutation({
    mutationFn: (params: { assessmentId: string; reviewId: string; treatmentIndices: number[] }) =>
      createEHROrders(
        params.assessmentId,
        params.reviewId,
        params.treatmentIndices,
        "physician-001", // In production, get from auth context
        "Dr. Review Physician",
        "1234567890"
      ),
    onSuccess: (data) => {
      setReviewState(prev => ({
        ...prev,
        ehrOrders: data.orders,
      }));
    },
    onError: (error) => {
      console.error("EHR order creation failed:", error);
      alert(`Failed to create EHR orders: ${(error as Error).message}`);
    },
  });

  const handleStartReview = () => {
    setIsReviewing(true);
    setReviewStartedAt(new Date().toISOString());
  };

  const handleToggleDiagnosis = (index: number) => {
    setReviewState(prev => {
      const newSet = new Set(prev.approvedDiagnoses);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return { ...prev, approvedDiagnoses: newSet };
    });
  };

  const handleToggleTreatment = (index: number) => {
    setReviewState(prev => {
      const newSet = new Set(prev.approvedTreatments);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return { ...prev, approvedTreatments: newSet };
    });
  };

  const handleSubmitReview = async (status: "approved" | "rejected" | "modified") => {
    if (!assessment?.assessment?.persisted_recommendation_id) {
      // Fallback for assessments not persisted to backend
      setReviewState(prev => ({ ...prev, reviewStatus: status }));
      setIsReviewing(false);
      alert(`Review submitted as "${status}". Note: Assessment was not persisted to backend.`);
      return;
    }

    setIsSubmittingReview(true);

    // Determine decision type based on status and modifications
    const allDiagnosesApproved = reviewState.approvedDiagnoses.size === assessment.assessment.diagnoses.length;
    const allTreatmentsApproved = reviewState.approvedTreatments.size === assessment.assessment.treatments.length;

    let decision: "approved" | "approved_modified" | "rejected" | "deferred";
    if (status === "rejected") {
      decision = "rejected";
    } else if (status === "approved" && allDiagnosesApproved && allTreatmentsApproved) {
      decision = "approved";
    } else {
      decision = "approved_modified";
    }

    // Build arrays of approved/rejected indices
    const approvedDiagnoses = Array.from(reviewState.approvedDiagnoses);
    const rejectedDiagnoses = assessment.assessment.diagnoses
      .map((_, i) => i)
      .filter(i => !reviewState.approvedDiagnoses.has(i));
    const approvedTreatments = Array.from(reviewState.approvedTreatments);
    const rejectedTreatments = assessment.assessment.treatments
      .map((_, i) => i)
      .filter(i => !reviewState.approvedTreatments.has(i));

    try {
      await reviewMutation.mutateAsync({
        assessment_id: assessment.assessment.assessment_id || String(assessment.assessment.persisted_recommendation_id),
        physician_id: "physician-001", // In production, get from auth context
        physician_name: "Dr. Review Physician",
        physician_npi: "1234567890",
        physician_specialty: "Internal Medicine",
        decision,
        approved_diagnoses: approvedDiagnoses,
        rejected_diagnoses: rejectedDiagnoses,
        approved_treatments: approvedTreatments,
        rejected_treatments: rejectedTreatments,
        physician_notes: reviewState.physicianNotes || undefined,
        clinical_rationale: reviewState.physicianNotes || undefined,
        rejection_reason: status === "rejected" ? reviewState.physicianNotes : undefined,
        attest: true,
        review_started_at: reviewStartedAt || undefined,
      });

      setReviewState(prev => ({ ...prev, reviewStatus: status }));
      setIsReviewing(false);
    } catch (error) {
      console.error("Failed to submit review:", error);
      setIsSubmittingReview(false);
    }
  };

  const handleGenerateDocument = async () => {
    if (!assessment?.assessment?.assessment_id && !assessment?.assessment?.persisted_recommendation_id) {
      alert("Assessment not persisted to backend. Cannot generate document.");
      return;
    }

    await documentMutation.mutateAsync({
      assessmentId: assessment.assessment.assessment_id || String(assessment.assessment.persisted_recommendation_id),
      reviewId: reviewState.submittedReview?.id,
    });
  };

  const handleCreateEHROrders = async () => {
    const assessmentId = assessment?.assessment?.assessment_id || assessment?.assessment?.persisted_recommendation_id;
    if (!assessmentId || !reviewState.submittedReview?.id) {
      alert("Review must be submitted before creating EHR orders.");
      return;
    }

    const approvedTreatmentIndices = Array.from(reviewState.approvedTreatments);
    if (approvedTreatmentIndices.length === 0) {
      alert("No treatments approved. Cannot create orders.");
      return;
    }

    await ehrOrdersMutation.mutateAsync({
      assessmentId: String(assessmentId),
      reviewId: reviewState.submittedReview.id,
      treatmentIndices: approvedTreatmentIndices,
    });
  };

  const sectionStyle: React.CSSProperties = {
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    marginBottom: 20,
    overflow: "hidden",
  };
  const sectionHeaderStyle: React.CSSProperties = {
    padding: "10px 16px",
    background: "#f8fafc",
    borderBottom: "1px solid #e2e8f0",
    fontSize: 13,
    fontWeight: 700,
    color: "#1e293b",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  };
  const sectionBodyStyle: React.CSSProperties = { padding: 16 };

  return (
    <div style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      {/* Professional Report Header */}
      <div style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        borderRadius: 10,
        padding: "20px 24px",
        marginBottom: 20,
        color: "white",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", opacity: 0.7, marginBottom: 4 }}>
              Eminence HealthOS
            </div>
            <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
              AI Clinical Decision Support Report
            </h3>
            <p style={{ margin: "6px 0 0", fontSize: 13, opacity: 0.8 }}>
              Multi-agent clinical analysis with physician Human-in-the-Loop (HITL) approval
            </p>
          </div>
          <div style={{ textAlign: "right", display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
            <button
              onClick={() => assessmentMutation.mutate()}
              disabled={assessmentMutation.isPending || !fhirId}
              style={{
                padding: "10px 24px",
                borderRadius: 6,
                border: "2px solid rgba(255,255,255,0.3)",
                background: assessmentMutation.isPending ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.15)",
                color: "white",
                cursor: assessmentMutation.isPending || !fhirId ? "not-allowed" : "pointer",
                fontWeight: 600,
                fontSize: 13,
                backdropFilter: "blur(4px)",
                transition: "all 0.2s",
              }}
            >
              {assessmentMutation.isPending ? "Analyzing Patient Data..." : "Run AI Assessment"}
            </button>
            {llmStatusQuery.data && (
              <div style={{ fontSize: 11, opacity: 0.7 }}>
                AI Engine: {llmStatusQuery.data.primary_provider || "Not configured"}
                {llmStatusQuery.data.config && ` / ${llmStatusQuery.data.config.claude_model || llmStatusQuery.data.config.ollama_model}`}
              </div>
            )}
          </div>
        </div>

        {/* Patient Quick ID Banner */}
        {patient && (
          <div style={{
            marginTop: 16,
            padding: "10px 16px",
            background: "rgba(255,255,255,0.1)",
            borderRadius: 6,
            display: "flex",
            gap: 24,
            fontSize: 13,
            flexWrap: "wrap",
          }}>
            <span><strong>Patient:</strong> {patient.prefix ? `${patient.prefix} ` : ""}{patient.first_name} {patient.last_name}</span>
            <span><strong>MRN:</strong> {patient.mrn}</span>
            <span><strong>DOB:</strong> {patient.date_of_birth}</span>
            <span><strong>Age:</strong> {patient.age ?? clinicalSummary?.age ?? "—"}</span>
            <span><strong>Sex:</strong> {patient.gender}</span>
            {patient.blood_type && <span><strong>Blood Type:</strong> {patient.blood_type}</span>}
          </div>
        )}

        {!fhirId && (
          <div style={{ marginTop: 12, padding: "8px 12px", background: "rgba(251,191,36,0.2)", borderRadius: 6, fontSize: 12, color: "#fde68a" }}>
            Patient must be synced to FHIR to run clinical assessment
          </div>
        )}
      </div>

      {/* Patient Information Section — shown when assessment is available */}
      {patient && assessment?.success && (
        <div style={sectionStyle}>
          <div style={sectionHeaderStyle}>Patient Information Summary</div>
          <div style={sectionBodyStyle}>
            {/* Demographics Row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>Demographics</div>
                <div style={{ fontSize: 13 }}>
                  <div><strong>Full Name:</strong> {patient.prefix ? `${patient.prefix} ` : ""}{patient.first_name} {patient.middle_name ? `${patient.middle_name} ` : ""}{patient.last_name}{patient.suffix ? ` ${patient.suffix}` : ""}</div>
                  <div><strong>Date of Birth:</strong> {patient.date_of_birth}</div>
                  <div><strong>Age:</strong> {patient.age ?? clinicalSummary?.age ?? "—"} years</div>
                  <div><strong>Sex:</strong> {patient.gender}</div>
                  {patient.blood_type && <div><strong>Blood Type:</strong> {patient.blood_type}</div>}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>Contact Information</div>
                <div style={{ fontSize: 13 }}>
                  {patient.phone && <div><strong>Phone:</strong> {patient.phone}</div>}
                  {patient.email && <div><strong>Email:</strong> {patient.email}</div>}
                  {patient.address_line1 && <div><strong>Address:</strong> {patient.address_line1}{patient.address_line2 ? `, ${patient.address_line2}` : ""}</div>}
                  {patient.city && <div>{patient.city}{patient.state ? `, ${patient.state}` : ""} {patient.postal_code || ""}</div>}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 4 }}>Emergency Contact & Insurance</div>
                <div style={{ fontSize: 13 }}>
                  {patient.emergency_contact_name && <div><strong>Emergency:</strong> {patient.emergency_contact_name} ({patient.emergency_contact_relationship || "N/A"})</div>}
                  {patient.emergency_contact_phone && <div><strong>Phone:</strong> {patient.emergency_contact_phone}</div>}
                  {patient.insurance_provider && <div><strong>Insurance:</strong> {patient.insurance_provider}</div>}
                  {patient.insurance_policy_number && <div><strong>Policy #:</strong> {patient.insurance_policy_number}</div>}
                  {patient.primary_care_physician && <div><strong>PCP:</strong> {patient.primary_care_physician}</div>}
                </div>
              </div>
            </div>

            {/* Medical Background Row */}
            <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>Allergies</div>
                {(patient.allergies?.length || clinicalSummary?.allergies?.length) ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {(patient.allergies || clinicalSummary?.allergies || []).map((a, i) => (
                      <span key={i} style={{ padding: "3px 8px", background: "#fee2e2", color: "#991b1b", borderRadius: 4, fontSize: 12, fontWeight: 500 }}>{a}</span>
                    ))}
                  </div>
                ) : <div style={{ fontSize: 12, color: "#94a3b8" }}>NKDA</div>}
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>Current Medications</div>
                {(patient.medications?.length || clinicalSummary?.medications?.length) ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {(patient.medications || clinicalSummary?.medications || []).map((m, i) => (
                      <span key={i} style={{ padding: "3px 8px", background: "#dbeafe", color: "#1e40af", borderRadius: 4, fontSize: 12, fontWeight: 500 }}>{m}</span>
                    ))}
                  </div>
                ) : <div style={{ fontSize: 12, color: "#94a3b8" }}>None reported</div>}
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>Medical Conditions</div>
                {patient.medical_conditions?.length ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {patient.medical_conditions.map((c, i) => (
                      <span key={i} style={{ padding: "3px 8px", background: "#fef3c7", color: "#92400e", borderRadius: 4, fontSize: 12, fontWeight: 500 }}>{c}</span>
                    ))}
                  </div>
                ) : <div style={{ fontSize: 12, color: "#94a3b8" }}>None reported</div>}
              </div>
            </div>

            {/* Medical History */}
            {patient.medical_history && (
              <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: 16, marginTop: 16 }}>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>Medical / Family History</div>
                <div style={{ fontSize: 13, color: "#334155", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{patient.medical_history}</div>
              </div>
            )}

            {/* Active Diagnoses from clinical summary */}
            {clinicalSummary?.active_diagnoses && clinicalSummary.active_diagnoses.length > 0 && (
              <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: 16, marginTop: 16 }}>
                <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>Active Diagnoses (from EHR)</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {clinicalSummary.active_diagnoses.map((dx, i) => (
                    <span key={i} style={{
                      padding: "4px 10px",
                      background: "#f0f9ff",
                      border: "1px solid #bae6fd",
                      borderRadius: 4,
                      fontSize: 12,
                    }}>
                      <strong style={{ color: "#0369a1" }}>{dx.icd10_code}</strong>
                      <span style={{ color: "#475569", marginLeft: 4 }}>{dx.description}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Display */}
      {assessmentMutation.isError && (
        <div style={{ ...cardStyle, background: "#fef2f2", border: "1px solid #fecaca" }}>
          <h4 style={{ margin: 0, color: "#dc2626" }}>Assessment Failed</h4>
          <p style={{ margin: "8px 0 0", color: "#7f1d1d" }}>{(assessmentMutation.error as Error).message}</p>
        </div>
      )}

      {/* Assessment Results */}
      {assessment?.success && assessment.assessment && (
        <AssessmentResults
          assessment={assessment.assessment}
          llmProvider={assessment.llm_provider}
          patient={patient}
          clinicalSummary={clinicalSummary}
          showReasoning={showReasoning}
          onToggleReasoning={() => setShowReasoning(!showReasoning)}
          reviewState={reviewState}
          isReviewing={isReviewing}
          isSubmittingReview={isSubmittingReview}
          onStartReview={handleStartReview}
          onToggleDiagnosis={handleToggleDiagnosis}
          onToggleTreatment={handleToggleTreatment}
          onSubmitReview={handleSubmitReview}
          onNotesChange={(notes) => setReviewState(prev => ({ ...prev, physicianNotes: notes }))}
          onGenerateDocument={handleGenerateDocument}
          onCreateEHROrders={handleCreateEHROrders}
          isGeneratingDocument={documentMutation.isPending}
          isCreatingOrders={ehrOrdersMutation.isPending}
        />
      )}

      {assessment && !assessment.success && (
        <div style={{ ...cardStyle, background: "#fef2f2", border: "1px solid #fecaca" }}>
          <h4 style={{ margin: 0, color: "#dc2626" }}>Assessment Error</h4>
          <p style={{ margin: "8px 0 0", color: "#7f1d1d" }}>{assessment.error}</p>
        </div>
      )}
    </div>
  );
}

// Assessment Results Component
function AssessmentResults({
  assessment,
  llmProvider,
  patient,
  clinicalSummary,
  showReasoning,
  onToggleReasoning,
  reviewState,
  isReviewing,
  isSubmittingReview,
  onStartReview,
  onToggleDiagnosis,
  onToggleTreatment,
  onSubmitReview,
  onNotesChange,
  onGenerateDocument,
  onCreateEHROrders,
  isGeneratingDocument,
  isCreatingOrders,
}: {
  assessment: ClinicalAssessment;
  llmProvider?: string;
  patient?: Patient;
  clinicalSummary?: PatientClinicalSummary | null;
  showReasoning: boolean;
  onToggleReasoning: () => void;
  reviewState: ReviewState;
  isReviewing: boolean;
  isSubmittingReview: boolean;
  onStartReview: () => void;
  onToggleDiagnosis: (index: number) => void;
  onToggleTreatment: (index: number) => void;
  onSubmitReview: (status: "approved" | "rejected" | "modified") => void;
  onNotesChange: (notes: string) => void;
  onGenerateDocument: () => void;
  onCreateEHROrders: () => void;
  isGeneratingDocument: boolean;
  isCreatingOrders: boolean;
}) {
  const cardStyle = { border: "1px solid #eee", borderRadius: 12, padding: 16, marginBottom: 16 };

  const reviewStatusColors = {
    pending: { bg: "#fef3c7", text: "#92400e", label: "Pending Review" },
    approved: { bg: "#dcfce7", text: "#166534", label: "Approved" },
    rejected: { bg: "#fee2e2", text: "#dc2626", label: "Rejected" },
    modified: { bg: "#dbeafe", text: "#1e40af", label: "Modified & Approved" },
  };

  return (
    <div>
      {/* Summary Header */}
      <div style={{ ...cardStyle, background: assessment.requires_human_review ? "#fef3c7" : "#f0fdf4" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 24 }}>{assessment.requires_human_review ? "⚠️" : "✅"}</span>
              <h4 style={{ margin: 0 }}>Assessment Complete</h4>
            </div>
            <div style={{ marginTop: 8, fontSize: 13, color: "#64748b" }}>
              Confidence: <strong>{(assessment.confidence * 100).toFixed(0)}%</strong>
              {llmProvider && <span> • LLM: {llmProvider}</span>}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {reviewState.reviewStatus !== "pending" && (
              <div style={{
                padding: "6px 12px",
                background: reviewStatusColors[reviewState.reviewStatus].bg,
                color: reviewStatusColors[reviewState.reviewStatus].text,
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
              }}>
                {reviewStatusColors[reviewState.reviewStatus].label}
              </div>
            )}
            {reviewState.reviewStatus === "pending" && (
              <button
                onClick={onStartReview}
                style={{
                  padding: "8px 16px",
                  background: isReviewing ? "#64748b" : assessment.requires_human_review ? "#dc2626" : "#059669",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {isReviewing ? "Reviewing..." : assessment.requires_human_review ? "Review Required" : "Start Review"}
              </button>
            )}
          </div>
        </div>

        {assessment.review_reason && (
          <div style={{ marginTop: 12, padding: 8, background: "#fef9c3", borderRadius: 6, fontSize: 13 }}>
            {assessment.review_reason}
          </div>
        )}

        {assessment.warnings.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {assessment.warnings.map((warning, i) => (
              <div key={i} style={{ padding: 8, background: "#fee2e2", borderRadius: 6, fontSize: 13, color: "#dc2626", marginBottom: 4 }}>
                ⚠️ {warning}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Physician Review Panel */}
      {isReviewing && (
        <div style={{ ...cardStyle, background: "#eff6ff", border: "2px solid #3b82f6" }}>
          <h4 style={{ margin: "0 0 16px", color: "#1e40af", display: "flex", alignItems: "center", gap: 8 }}>
            <span>👨‍⚕️</span> Physician Review
          </h4>

          {/* Review Diagnoses */}
          <div style={{ marginBottom: 16 }}>
            <h5 style={{ margin: "0 0 8px", fontSize: 14 }}>Review Diagnoses</h5>
            {assessment.diagnoses.map((dx, i) => (
              <label
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: 8,
                  background: reviewState.approvedDiagnoses.has(i) ? "#dcfce7" : "#fee2e2",
                  borderRadius: 6,
                  marginBottom: 4,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={reviewState.approvedDiagnoses.has(i)}
                  onChange={() => onToggleDiagnosis(i)}
                  style={{ width: 18, height: 18 }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500 }}>{dx.diagnosis}</div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    {dx.icd10_code} • Confidence: {(dx.confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <span style={{ fontSize: 12, fontWeight: 600, color: reviewState.approvedDiagnoses.has(i) ? "#166534" : "#dc2626" }}>
                  {reviewState.approvedDiagnoses.has(i) ? "APPROVED" : "REJECTED"}
                </span>
              </label>
            ))}
          </div>

          {/* Review Treatments */}
          <div style={{ marginBottom: 16 }}>
            <h5 style={{ margin: "0 0 8px", fontSize: 14 }}>Review Treatments</h5>
            {assessment.treatments.map((tx, i) => (
              <label
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: 8,
                  background: reviewState.approvedTreatments.has(i) ? "#dcfce7" : "#fee2e2",
                  borderRadius: 6,
                  marginBottom: 4,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={reviewState.approvedTreatments.has(i)}
                  onChange={() => onToggleTreatment(i)}
                  style={{ width: 18, height: 18 }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500 }}>{tx.description}</div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    {tx.treatment_type} • Priority: {tx.priority}
                  </div>
                </div>
                <span style={{ fontSize: 12, fontWeight: 600, color: reviewState.approvedTreatments.has(i) ? "#166534" : "#dc2626" }}>
                  {reviewState.approvedTreatments.has(i) ? "APPROVED" : "REJECTED"}
                </span>
              </label>
            ))}
          </div>

          {/* Physician Notes */}
          <div style={{ marginBottom: 16 }}>
            <h5 style={{ margin: "0 0 8px", fontSize: 14 }}>Physician Notes</h5>
            <textarea
              value={reviewState.physicianNotes}
              onChange={(e) => onNotesChange(e.target.value)}
              placeholder="Add clinical notes, modifications, or additional recommendations..."
              style={{
                width: "100%",
                minHeight: 80,
                padding: 12,
                borderRadius: 6,
                border: "1px solid #cbd5e1",
                fontSize: 13,
                resize: "vertical",
              }}
            />
          </div>

          {/* Submit Buttons */}
          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
            <button
              onClick={() => onSubmitReview("rejected")}
              disabled={isSubmittingReview}
              style={{
                padding: "10px 20px",
                background: isSubmittingReview ? "#94a3b8" : "#dc2626",
                color: "white",
                border: "none",
                borderRadius: 6,
                fontWeight: 600,
                cursor: isSubmittingReview ? "not-allowed" : "pointer",
              }}
            >
              {isSubmittingReview ? "Submitting..." : "Reject Assessment"}
            </button>
            <button
              onClick={() => onSubmitReview("modified")}
              disabled={isSubmittingReview}
              style={{
                padding: "10px 20px",
                background: isSubmittingReview ? "#94a3b8" : "#2563eb",
                color: "white",
                border: "none",
                borderRadius: 6,
                fontWeight: 600,
                cursor: isSubmittingReview ? "not-allowed" : "pointer",
              }}
            >
              {isSubmittingReview ? "Submitting..." : "Approve with Modifications"}
            </button>
            <button
              onClick={() => onSubmitReview("approved")}
              disabled={isSubmittingReview}
              style={{
                padding: "10px 20px",
                background: isSubmittingReview ? "#94a3b8" : "#059669",
                color: "white",
                border: "none",
                borderRadius: 6,
                fontWeight: 600,
                cursor: isSubmittingReview ? "not-allowed" : "pointer",
              }}
            >
              {isSubmittingReview ? "Submitting..." : "Approve All"}
            </button>
          </div>
        </div>
      )}

      {/* Post-Review Actions Panel */}
      {reviewState.submittedReview && (
        <div style={{ ...cardStyle, background: "#f0fdf4", border: "2px solid #22c55e" }}>
          <h4 style={{ margin: "0 0 16px", color: "#166534", display: "flex", alignItems: "center", gap: 8 }}>
            <span>✅</span> Review Submitted Successfully
          </h4>

          <div style={{ marginBottom: 16, fontSize: 13, color: "#475569" }}>
            <div><strong>Review ID:</strong> {reviewState.submittedReview.id}</div>
            <div><strong>Decision:</strong> {reviewState.submittedReview.decision}</div>
            <div><strong>Attested:</strong> {reviewState.submittedReview.attested ? "Yes" : "No"}</div>
            {reviewState.submittedReview.signature_datetime && (
              <div><strong>Signed:</strong> {new Date(reviewState.submittedReview.signature_datetime).toLocaleString()}</div>
            )}
          </div>

          {/* Final Codes */}
          {reviewState.submittedReview.final_icd10_codes?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Final ICD-10 Codes:</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {reviewState.submittedReview.final_icd10_codes.map((code, i) => (
                  <span key={i} style={{ padding: "4px 8px", background: "#dbeafe", borderRadius: 4, fontSize: 11 }}>
                    {code.code}
                  </span>
                ))}
              </div>
            </div>
          )}

          {reviewState.submittedReview.final_cpt_codes?.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Final CPT Codes:</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {reviewState.submittedReview.final_cpt_codes.map((code, i) => (
                  <span key={i} style={{ padding: "4px 8px", background: "#dcfce7", borderRadius: 4, fontSize: 11 }}>
                    {code.code}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Post-Review Action Buttons */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button
              onClick={onGenerateDocument}
              disabled={isGeneratingDocument}
              style={{
                padding: "10px 16px",
                background: isGeneratingDocument ? "#94a3b8" : "#6366f1",
                color: "white",
                border: "none",
                borderRadius: 6,
                fontWeight: 600,
                cursor: isGeneratingDocument ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>📄</span>
              {isGeneratingDocument ? "Generating..." : "Generate Clinical Document"}
            </button>

            <button
              onClick={onCreateEHROrders}
              disabled={isCreatingOrders || reviewState.submittedReview.decision === "rejected"}
              style={{
                padding: "10px 16px",
                background: isCreatingOrders || reviewState.submittedReview.decision === "rejected" ? "#94a3b8" : "#0891b2",
                color: "white",
                border: "none",
                borderRadius: 6,
                fontWeight: 600,
                cursor: isCreatingOrders || reviewState.submittedReview.decision === "rejected" ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>🏥</span>
              {isCreatingOrders ? "Creating Orders..." : "Create EHR Orders"}
            </button>
          </div>

          {/* Generated Document Display */}
          {reviewState.generatedDocument && (
            <div style={{ marginTop: 16, padding: 12, background: "white", borderRadius: 6, border: "1px solid #e2e8f0" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <h5 style={{ margin: 0 }}>Generated Document: {reviewState.generatedDocument.title}</h5>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button
                    onClick={async () => {
                      try {
                        await downloadClinicalDocument(reviewState.generatedDocument!.id, reviewState.generatedDocument!.title, "pdf");
                      } catch (err) {
                        console.error("PDF download failed:", err);
                        alert("Failed to download PDF. Please try again.");
                      }
                    }}
                    style={{
                      padding: "4px 10px",
                      background: "#dc2626",
                      color: "white",
                      border: "none",
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Download PDF
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        await downloadClinicalDocument(reviewState.generatedDocument!.id, reviewState.generatedDocument!.title, "html");
                      } catch (err) {
                        console.error("HTML download failed:", err);
                        alert("Failed to download HTML. Please try again.");
                      }
                    }}
                    style={{
                      padding: "4px 10px",
                      background: "#2563eb",
                      color: "white",
                      border: "none",
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Download HTML
                  </button>
                  <span style={{
                    padding: "2px 8px",
                    background: reviewState.generatedDocument.status === "final" ? "#dcfce7" : "#fef3c7",
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                  }}>
                    {reviewState.generatedDocument.status.toUpperCase()}
                  </span>
                </div>
              </div>
              <div
                style={{ fontSize: 13, maxHeight: 300, overflow: "auto", background: "#f8fafc", padding: 12, borderRadius: 4 }}
                dangerouslySetInnerHTML={{ __html: reviewState.generatedDocument.content }}
              />
            </div>
          )}

          {/* EHR Orders Display */}
          {reviewState.ehrOrders && reviewState.ehrOrders.length > 0 && (
            <div style={{ marginTop: 16, padding: 12, background: "white", borderRadius: 6, border: "1px solid #e2e8f0" }}>
              <h5 style={{ margin: "0 0 8px" }}>EHR Orders Created ({reviewState.ehrOrders.length})</h5>
              {reviewState.ehrOrders.map((order, i) => (
                <div key={i} style={{ padding: 8, background: "#f0f9ff", borderRadius: 4, marginBottom: 4, fontSize: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontWeight: 600 }}>{order.description}</span>
                    <span style={{
                      padding: "2px 6px",
                      background: order.status === "submitted" ? "#dcfce7" : "#fef3c7",
                      borderRadius: 4,
                      fontSize: 10,
                    }}>
                      {order.status.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ color: "#64748b", marginTop: 4 }}>
                    Type: {order.order_type} {order.cpt_code && `• CPT: ${order.cpt_code}`}
                    {order.ehr_order_id && ` • EHR ID: ${order.ehr_order_id}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Critical Findings */}
      {assessment.critical_findings.length > 0 && (
        <div style={{ ...cardStyle, background: "#fef2f2", border: "1px solid #fecaca" }}>
          <h4 style={{ margin: "0 0 12px", color: "#dc2626" }}>Critical Findings</h4>
          {assessment.critical_findings.map((finding, i) => (
            <FindingCard key={i} finding={finding} />
          ))}
        </div>
      )}

      {/* Main Content Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Diagnoses */}
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 }}>
            <span>🩺</span> Diagnoses
            <span style={{ fontSize: 12, color: "#64748b", fontWeight: 400 }}>
              ({assessment.diagnoses.length})
            </span>
          </h4>
          {assessment.diagnoses.length > 0 ? (
            assessment.diagnoses.map((dx, i) => (
              <DiagnosisCard key={i} diagnosis={dx} />
            ))
          ) : (
            <div style={{ color: "#64748b", fontSize: 13 }}>No diagnoses identified</div>
          )}
        </div>

        {/* Treatments */}
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 }}>
            <span>💊</span> Treatment Recommendations
            <span style={{ fontSize: 12, color: "#64748b", fontWeight: 400 }}>
              ({assessment.treatments.length})
            </span>
          </h4>
          {assessment.treatments.length > 0 ? (
            assessment.treatments.map((tx, i) => (
              <TreatmentCard key={i} treatment={tx} />
            ))
          ) : (
            <div style={{ color: "#64748b", fontSize: 13 }}>No specific treatments recommended</div>
          )}
        </div>
      </div>

      {/* Clinical Codes */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* ICD-10 Codes */}
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px" }}>ICD-10 Codes</h4>
          {assessment.icd10_codes.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {assessment.icd10_codes.map((code, i) => (
                <div
                  key={i}
                  style={{
                    padding: "6px 10px",
                    background: "#dbeafe",
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                  title={code.description}
                >
                  <strong>{code.code}</strong>
                  <span style={{ color: "#64748b", marginLeft: 4 }}>
                    ({(code.confidence * 100).toFixed(0)}%)
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "#64748b", fontSize: 13 }}>No ICD-10 codes suggested</div>
          )}
        </div>

        {/* CPT Codes */}
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px" }}>CPT Codes</h4>
          {assessment.cpt_codes.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {assessment.cpt_codes.map((code, i) => (
                <div
                  key={i}
                  style={{
                    padding: "6px 10px",
                    background: "#dcfce7",
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                  title={code.description}
                >
                  <strong>{code.code}</strong>
                  <span style={{ color: "#64748b", marginLeft: 4 }}>
                    {code.category}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "#64748b", fontSize: 13 }}>No CPT codes suggested</div>
          )}
        </div>
      </div>

      {/* All Findings */}
      {assessment.findings.length > 0 && (
        <div style={cardStyle}>
          <h4 style={{ margin: "0 0 12px" }}>Clinical Findings ({assessment.findings.length})</h4>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            {assessment.findings.map((finding, i) => (
              <FindingCard key={i} finding={finding} compact />
            ))}
          </div>
        </div>
      )}

      {/* Reasoning Toggle */}
      <div style={cardStyle}>
        <button
          onClick={onToggleReasoning}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            color: "#0284c7",
            fontWeight: 500,
          }}
        >
          <span>{showReasoning ? "▼" : "▶"}</span>
          Clinical Reasoning ({assessment.reasoning.length} steps)
        </button>

        {showReasoning && (
          <div style={{ marginTop: 12, maxHeight: 400, overflow: "auto" }}>
            {assessment.reasoning.map((step, i) => (
              <div
                key={i}
                style={{
                  padding: 8,
                  background: i % 2 === 0 ? "#f8fafc" : "#fff",
                  borderRadius: 4,
                  fontSize: 13,
                  fontFamily: "monospace",
                  whiteSpace: "pre-wrap",
                }}
              >
                {step}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Finding Card Component
function FindingCard({ finding, compact }: { finding: ClinicalFinding; compact?: boolean }) {
  const statusColors = {
    normal: { bg: "#f0fdf4", border: "#bbf7d0", text: "#166534" },
    abnormal: { bg: "#fef3c7", border: "#fde68a", text: "#92400e" },
    critical: { bg: "#fee2e2", border: "#fecaca", text: "#dc2626" },
  };

  const colors = statusColors[finding.status];

  if (compact) {
    return (
      <div
        style={{
          padding: 8,
          background: colors.bg,
          border: `1px solid ${colors.border}`,
          borderRadius: 6,
          fontSize: 12,
        }}
      >
        <div style={{ fontWeight: 500, color: colors.text }}>{finding.name}</div>
        <div style={{ color: "#64748b" }}>
          {finding.value} {finding.unit}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 12,
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 600, color: colors.text }}>{finding.name}</div>
          <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>
            {finding.value} {finding.unit}
          </div>
        </div>
        <span
          style={{
            padding: "4px 8px",
            background: colors.text,
            color: "white",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
          }}
        >
          {finding.status}
        </span>
      </div>
      <div style={{ marginTop: 8, fontSize: 13, color: "#64748b" }}>{finding.interpretation}</div>
      {finding.reference_range && (
        <div style={{ marginTop: 4, fontSize: 12, color: "#94a3b8" }}>
          Reference: {finding.reference_range}
        </div>
      )}
    </div>
  );
}

// Diagnosis Card Component
function DiagnosisCard({ diagnosis }: { diagnosis: DiagnosisRecommendation }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        padding: 12,
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        marginBottom: 8,
      }}
    >
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", cursor: "pointer" }}
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <div style={{ fontWeight: 600, color: "#1e293b" }}>{diagnosis.diagnosis}</div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
            ICD-10: <strong style={{ color: "#2563eb" }}>{diagnosis.icd10_code}</strong>
            <span style={{ marginLeft: 12 }}>
              Confidence: <strong>{(diagnosis.confidence * 100).toFixed(0)}%</strong>
            </span>
          </div>
        </div>
        <span style={{ color: "#64748b" }}>{expanded ? "▼" : "▶"}</span>
      </div>

      {expanded && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: 13, color: "#475569", marginBottom: 8 }}>{diagnosis.rationale}</div>

          {diagnosis.differential_diagnoses && diagnosis.differential_diagnoses.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: "#64748b", marginBottom: 4 }}>
                Differential Diagnoses:
              </div>
              {diagnosis.differential_diagnoses.map((diff, i) => (
                <div key={i} style={{ fontSize: 12, color: "#64748b", padding: "4px 0" }}>
                  • {diff.diagnosis} ({diff.icd10}) - {(diff.confidence * 100).toFixed(0)}%
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Treatment Card Component
function TreatmentCard({ treatment }: { treatment: TreatmentRecommendation }) {
  const priorityColors = {
    immediate: { bg: "#fee2e2", text: "#dc2626" },
    urgent: { bg: "#fef3c7", text: "#d97706" },
    routine: { bg: "#dbeafe", text: "#2563eb" },
  };

  const colors = priorityColors[treatment.priority as keyof typeof priorityColors] || priorityColors.routine;

  return (
    <div
      style={{
        padding: 12,
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                padding: "2px 6px",
                background: colors.bg,
                color: colors.text,
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              {treatment.priority}
            </span>
            <span style={{ fontSize: 11, color: "#64748b", textTransform: "capitalize" }}>
              {treatment.treatment_type}
            </span>
          </div>
          <div style={{ fontWeight: 500, marginTop: 6, color: "#1e293b" }}>{treatment.description}</div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>{treatment.rationale}</div>
        </div>
        {treatment.cpt_code && (
          <div style={{ padding: "4px 8px", background: "#dcfce7", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
            CPT: {treatment.cpt_code}
          </div>
        )}
      </div>

      {treatment.contraindications && treatment.contraindications.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#dc2626" }}>
          ⚠️ Contraindications: {treatment.contraindications.join(", ")}
        </div>
      )}
    </div>
  );
}
