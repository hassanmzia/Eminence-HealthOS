"use client";

import { useState, useCallback } from "react";
import {
  runClinicalAssessment,
  fetchLLMStatus,
  submitPhysicianReview,
  generateClinicalDocument,
  downloadClinicalDocument,
  createEHROrders,
  type ClinicalAssessmentResponse,
  type ClinicalAssessmentResult,
  type ClinicalFinding,
  type AIDiagnosisRecommendation,
  type AITreatmentRecommendation,
  type PhysicianReviewResult,
  type ClinicalDocumentResult,
  type EHROrderResult,
  type LLMStatusResponse,
  type PatientData,
  type DiagnosisResponse,
  type AllergyResponse,
  type MedicalHistoryResponse,
  type FamilyHistoryResponse,
  type PrescriptionResponse,
} from "@/lib/platform-api";
import { type PatientData as CorePatientData } from "@/lib/api";

// ── Props ────────────────────────────────────────────────────────────────────
interface AIAssessmentPanelProps {
  patient: CorePatientData;
  fhirId?: string;
  allergies?: AllergyResponse[];
  medications?: PrescriptionResponse[];
  diagnoses?: DiagnosisResponse[];
  medicalHistory?: MedicalHistoryResponse[];
  familyHistory?: FamilyHistoryResponse[];
}

// ── Internal State Types ─────────────────────────────────────────────────────
interface ReviewState {
  approvedDiagnoses: Set<number>;
  approvedTreatments: Set<number>;
  physicianNotes: string;
  reviewStatus: "pending" | "approved" | "rejected" | "modified";
  submittedReview?: PhysicianReviewResult;
  generatedDocument?: ClinicalDocumentResult;
  ehrOrders?: EHROrderResult[];
}

// ── Main Component ───────────────────────────────────────────────────────────
export function AIAssessmentPanel({
  patient,
  fhirId,
  allergies = [],
  medications = [],
  diagnoses = [],
  medicalHistory = [],
  familyHistory = [],
}: AIAssessmentPanelProps) {
  const [assessment, setAssessment] = useState<ClinicalAssessmentResponse | null>(null);
  const [llmStatus, setLlmStatus] = useState<LLMStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showReasoning, setShowReasoning] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewStartedAt, setReviewStartedAt] = useState<string | null>(null);
  const [reviewState, setReviewState] = useState<ReviewState>({
    approvedDiagnoses: new Set(),
    approvedTreatments: new Set(),
    physicianNotes: "",
    reviewStatus: "pending",
  });

  const d = patient.demographics as Record<string, unknown>;

  // Fetch LLM status on mount
  const loadLLMStatus = useCallback(async () => {
    try { setLlmStatus(await fetchLLMStatus()); } catch {}
  }, []);

  // Run assessment
  const handleRunAssessment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await loadLLMStatus();
      const data = await runClinicalAssessment(patient.id, fhirId);
      setAssessment(data);
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
    } catch (err) {
      setError((err as Error).message);
    }
    setLoading(false);
  }, [patient.id, fhirId, loadLLMStatus]);

  // HITL Handlers
  const handleStartReview = () => { setIsReviewing(true); setReviewStartedAt(new Date().toISOString()); };

  const toggleDiagnosis = (i: number) => {
    setReviewState(prev => {
      const s = new Set(prev.approvedDiagnoses);
      s.has(i) ? s.delete(i) : s.add(i);
      return { ...prev, approvedDiagnoses: s };
    });
  };

  const toggleTreatment = (i: number) => {
    setReviewState(prev => {
      const s = new Set(prev.approvedTreatments);
      s.has(i) ? s.delete(i) : s.add(i);
      return { ...prev, approvedTreatments: s };
    });
  };

  const handleSubmitReview = async (status: "approved" | "rejected" | "modified") => {
    const a = assessment?.assessment;
    if (!a?.persisted_recommendation_id) {
      setReviewState(prev => ({ ...prev, reviewStatus: status }));
      setIsReviewing(false);
      return;
    }
    setIsSubmittingReview(true);
    const allDx = reviewState.approvedDiagnoses.size === a.diagnoses.length;
    const allTx = reviewState.approvedTreatments.size === a.treatments.length;
    const decision = status === "rejected" ? "rejected" : (status === "approved" && allDx && allTx) ? "approved" : "approved_modified";
    try {
      const result = await submitPhysicianReview({
        assessment_id: a.assessment_id || String(a.persisted_recommendation_id),
        physician_id: "physician-001",
        physician_name: "Dr. Review Physician",
        physician_npi: "1234567890",
        physician_specialty: "Internal Medicine",
        decision,
        approved_diagnoses: Array.from(reviewState.approvedDiagnoses),
        rejected_diagnoses: a.diagnoses.map((_, i) => i).filter(i => !reviewState.approvedDiagnoses.has(i)),
        approved_treatments: Array.from(reviewState.approvedTreatments),
        rejected_treatments: a.treatments.map((_, i) => i).filter(i => !reviewState.approvedTreatments.has(i)),
        physician_notes: reviewState.physicianNotes || undefined,
        clinical_rationale: reviewState.physicianNotes || undefined,
        rejection_reason: status === "rejected" ? reviewState.physicianNotes : undefined,
        attest: true,
        review_started_at: reviewStartedAt || undefined,
      });
      setReviewState(prev => ({ ...prev, submittedReview: result, reviewStatus: status }));
      setIsReviewing(false);
    } catch (err) {
      alert(`Failed to submit review: ${(err as Error).message}`);
    }
    setIsSubmittingReview(false);
  };

  const handleGenerateDocument = async () => {
    const a = assessment?.assessment;
    const id = a?.assessment_id || a?.persisted_recommendation_id;
    if (!id) return;
    try {
      const doc = await generateClinicalDocument(String(id), reviewState.submittedReview?.id, "assessment_summary", "html", true);
      setReviewState(prev => ({ ...prev, generatedDocument: doc }));
    } catch (err) { alert(`Failed to generate document: ${(err as Error).message}`); }
  };

  const handleCreateOrders = async () => {
    const a = assessment?.assessment;
    const id = a?.assessment_id || a?.persisted_recommendation_id;
    if (!id || !reviewState.submittedReview?.id) return;
    const indices = Array.from(reviewState.approvedTreatments);
    if (indices.length === 0) { alert("No treatments approved."); return; }
    try {
      const res = await createEHROrders(String(id), reviewState.submittedReview.id, indices, "physician-001", "Dr. Review Physician", "1234567890");
      setReviewState(prev => ({ ...prev, ehrOrders: res.orders }));
    } catch (err) { alert(`Failed to create EHR orders: ${(err as Error).message}`); }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-5">
      {/* Report Header */}
      <ReportHeader
        patient={patient}
        llmStatus={llmStatus}
        loading={loading}
        fhirId={fhirId}
        onRun={handleRunAssessment}
      />

      {/* Error */}
      {error && (
        <div className="rounded-lg border-2 border-red-300 dark:border-red-800 overflow-hidden">
          <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-xs font-bold uppercase tracking-wider text-red-700 dark:text-red-400 border-b border-red-200 dark:border-red-800">Assessment Failed</div>
          <div className="px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</div>
        </div>
      )}

      {/* Patient Info (shown after assessment runs) */}
      {assessment?.success && assessment.assessment && (
        <PatientInfoSection
          patient={patient}
          allergies={allergies}
          medications={medications}
          diagnoses={diagnoses}
          medicalHistory={medicalHistory}
          familyHistory={familyHistory}
        />
      )}

      {/* Assessment Results */}
      {assessment?.success && assessment.assessment && (
        <AssessmentResultsSection
          assessment={assessment.assessment}
          llmProvider={assessment.llm_provider}
          showReasoning={showReasoning}
          onToggleReasoning={() => setShowReasoning(!showReasoning)}
          reviewState={reviewState}
          isReviewing={isReviewing}
          isSubmittingReview={isSubmittingReview}
          onStartReview={handleStartReview}
          onToggleDiagnosis={toggleDiagnosis}
          onToggleTreatment={toggleTreatment}
          onSubmitReview={handleSubmitReview}
          onNotesChange={(n) => setReviewState(prev => ({ ...prev, physicianNotes: n }))}
          onGenerateDocument={handleGenerateDocument}
          onCreateOrders={handleCreateOrders}
        />
      )}

      {assessment && !assessment.success && (
        <div className="rounded-lg border-2 border-red-300 dark:border-red-800 overflow-hidden">
          <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-xs font-bold uppercase tracking-wider text-red-700 dark:text-red-400 border-b border-red-200 dark:border-red-800">Assessment Error</div>
          <div className="px-4 py-3 text-sm text-red-700 dark:text-red-300">{assessment.error}</div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// SUB-COMPONENTS (Report Header)
// ══════════════════════════════════════════════════════════════════════════════

function ReportHeader({ patient, llmStatus, loading, fhirId, onRun }: {
  patient: CorePatientData;
  llmStatus: LLMStatusResponse | null;
  loading: boolean;
  fhirId?: string;
  onRun: () => void;
}) {
  const d = patient.demographics as Record<string, unknown>;
  return (
    <div className="rounded-xl bg-gradient-to-br from-slate-900 to-blue-900 p-5 text-white">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.15em] text-white/60 mb-1">Eminence HealthOS</p>
          <h3 className="text-lg font-bold leading-tight">AI Clinical Decision Support Report</h3>
          <p className="text-xs text-white/70 mt-1">Multi-agent clinical analysis with physician Human-in-the-Loop (HITL) approval</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <button
            onClick={onRun}
            disabled={loading || !fhirId}
            className="px-5 py-2.5 rounded-md border-2 border-white/30 bg-white/10 text-white text-xs font-bold backdrop-blur-sm hover:bg-white/20 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Analyzing Patient Data..." : "Run AI Assessment"}
          </button>
          {llmStatus && (
            <p className="text-[10px] text-white/50">
              AI: {llmStatus.primary_provider || "N/A"}
              {llmStatus.config && ` / ${llmStatus.config.claude_model || llmStatus.config.ollama_model}`}
            </p>
          )}
        </div>
      </div>

      {/* Patient Quick Banner */}
      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 rounded-md bg-white/10 px-4 py-2.5 text-xs">
        <span><strong>Patient:</strong> {d?.first_name ? `${d.first_name} ${d.last_name || ""}` : d?.name || patient.id}</span>
        <span><strong>MRN:</strong> {patient.mrn || "—"}</span>
        <span><strong>DOB:</strong> {(d?.date_of_birth as string) || (d?.dob as string) || "—"}</span>
        <span><strong>Sex:</strong> {(d?.gender as string) || (d?.sex as string) || "—"}</span>
        {d?.blood_type && <span><strong>Blood Type:</strong> {d.blood_type as string}</span>}
      </div>

      {!fhirId && (
        <div className="mt-3 rounded-md bg-yellow-500/20 px-3 py-2 text-[11px] text-yellow-200">
          Patient must be synced to FHIR to run clinical assessment
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// SUB-COMPONENTS (Patient Info Section)
// ══════════════════════════════════════════════════════════════════════════════

function PatientInfoSection({ patient, allergies, medications, diagnoses, medicalHistory, familyHistory }: {
  patient: CorePatientData;
  allergies: AllergyResponse[];
  medications: PrescriptionResponse[];
  diagnoses: DiagnosisResponse[];
  medicalHistory: MedicalHistoryResponse[];
  familyHistory: FamilyHistoryResponse[];
}) {
  const d = patient.demographics as Record<string, unknown>;
  return (
    <Section title="Patient Information Summary">
      {/* Demographics Row */}
      <div className="grid grid-cols-3 gap-5 mb-4">
        <div>
          <SectionLabel>Demographics</SectionLabel>
          <div className="text-xs space-y-0.5">
            <p><strong>Full Name:</strong> {d?.first_name ? `${d.first_name} ${d.last_name || ""}` : d?.name || "—"}</p>
            <p><strong>DOB:</strong> {(d?.date_of_birth as string) || (d?.dob as string) || "—"}</p>
            <p><strong>Sex:</strong> {(d?.gender as string) || (d?.sex as string) || "—"}</p>
            {d?.race && <p><strong>Race:</strong> {d.race as string}</p>}
            {d?.blood_type && <p><strong>Blood Type:</strong> {d.blood_type as string}</p>}
          </div>
        </div>
        <div>
          <SectionLabel>Contact</SectionLabel>
          <div className="text-xs space-y-0.5">
            <p><strong>Phone:</strong> {(d?.phone as string) || "—"}</p>
            <p><strong>Email:</strong> {(d?.email as string) || "—"}</p>
            {d?.address_line1 && <p><strong>Address:</strong> {[d.address_line1, d.city, d.state, d.postal_code].filter(Boolean).join(", ")}</p>}
          </div>
        </div>
        <div>
          <SectionLabel>Emergency & Insurance</SectionLabel>
          <div className="text-xs space-y-0.5">
            {d?.emergency_contact_name && <p><strong>Emergency:</strong> {d.emergency_contact_name as string}</p>}
            {d?.emergency_contact_phone && <p><strong>Phone:</strong> {d.emergency_contact_phone as string}</p>}
            {d?.insurance_provider && <p><strong>Insurance:</strong> {d.insurance_provider as string}</p>}
            {d?.insurance_member_id && <p><strong>Member ID:</strong> {d.insurance_member_id as string}</p>}
          </div>
        </div>
      </div>

      {/* Allergies / Medications / Conditions */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4 grid grid-cols-3 gap-5">
        <div>
          <SectionLabel>Allergies</SectionLabel>
          {allergies.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {allergies.map((a, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400 text-[11px] font-medium">
                  {a.allergen}
                </span>
              ))}
            </div>
          ) : <p className="text-[11px] text-gray-400">NKDA</p>}
        </div>
        <div>
          <SectionLabel>Current Medications</SectionLabel>
          {medications.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {medications.filter(m => m.status === "Active").map((m, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 text-[11px] font-medium">
                  {m.medication_name}
                </span>
              ))}
            </div>
          ) : <p className="text-[11px] text-gray-400">None reported</p>}
        </div>
        <div>
          <SectionLabel>Active Diagnoses</SectionLabel>
          {diagnoses.filter(dx => dx.status === "Active").length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {diagnoses.filter(dx => dx.status === "Active").map((dx, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400 text-[11px] font-medium">
                  {dx.icd10_code}: {dx.description}
                </span>
              ))}
            </div>
          ) : <p className="text-[11px] text-gray-400">None active</p>}
        </div>
      </div>

      {/* Family History */}
      {familyHistory.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
          <SectionLabel>Family History</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {familyHistory.map((fh, i) => (
              <span key={i} className="px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-400 text-[11px] font-medium">
                {fh.relationship}: {fh.condition}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Medical History */}
      {medicalHistory.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
          <SectionLabel>Medical History</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {medicalHistory.map((mh, i) => (
              <span key={i} className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-[11px] font-medium">
                {mh.condition} ({mh.status})
              </span>
            ))}
          </div>
        </div>
      )}
    </Section>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// PLACEHOLDER: Assessment Results (will be filled in next parts)
// ══════════════════════════════════════════════════════════════════════════════

function AssessmentResultsSection({
  assessment, llmProvider, showReasoning, onToggleReasoning,
  reviewState, isReviewing, isSubmittingReview,
  onStartReview, onToggleDiagnosis, onToggleTreatment, onSubmitReview,
  onNotesChange, onGenerateDocument, onCreateOrders,
}: {
  assessment: ClinicalAssessmentResult;
  llmProvider?: string;
  showReasoning: boolean;
  onToggleReasoning: () => void;
  reviewState: ReviewState;
  isReviewing: boolean;
  isSubmittingReview: boolean;
  onStartReview: () => void;
  onToggleDiagnosis: (i: number) => void;
  onToggleTreatment: (i: number) => void;
  onSubmitReview: (s: "approved" | "rejected" | "modified") => void;
  onNotesChange: (n: string) => void;
  onGenerateDocument: () => void;
  onCreateOrders: () => void;
}) {
  const statusCfg = {
    pending: { border: "border-amber-400", bg: "bg-amber-50 dark:bg-amber-900/20", text: "text-amber-800 dark:text-amber-400", label: "PENDING PHYSICIAN REVIEW", dot: "bg-amber-500" },
    approved: { border: "border-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-900/20", text: "text-emerald-800 dark:text-emerald-400", label: "PHYSICIAN APPROVED", dot: "bg-emerald-500" },
    rejected: { border: "border-red-400", bg: "bg-red-50 dark:bg-red-900/20", text: "text-red-700 dark:text-red-400", label: "PHYSICIAN REJECTED", dot: "bg-red-500" },
    modified: { border: "border-blue-400", bg: "bg-blue-50 dark:bg-blue-900/20", text: "text-blue-800 dark:text-blue-400", label: "APPROVED WITH MODIFICATIONS", dot: "bg-blue-500" },
  };
  const st = statusCfg[reviewState.reviewStatus];

  return (
    <div className="space-y-5">
      {/* Status Banner */}
      <div className={`rounded-lg border-2 ${st.border} overflow-hidden`}>
        <div className={`px-5 py-4 ${st.bg} flex items-center justify-between`}>
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-full ${st.dot} flex items-center justify-center text-white text-base font-bold`}>
              {reviewState.reviewStatus === "approved" ? "\u2713" : reviewState.reviewStatus === "rejected" ? "\u2717" : reviewState.reviewStatus === "modified" ? "\u270E" : "!"}
            </div>
            <div>
              <p className={`font-bold text-sm ${st.text}`}>{st.label}</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                AI Confidence: <strong>{(assessment.confidence * 100).toFixed(0)}%</strong>
                {llmProvider && <> &middot; Engine: {llmProvider}</>}
                {assessment.assessment_id && <> &middot; ID: {assessment.assessment_id}</>}
              </p>
            </div>
          </div>
          {reviewState.reviewStatus === "pending" && (
            <button
              onClick={onStartReview}
              disabled={isReviewing}
              className={`px-5 py-2 rounded-md text-xs font-bold text-white shadow-sm transition ${
                isReviewing ? "bg-gray-400 cursor-not-allowed" : assessment.requires_human_review ? "bg-red-600 hover:bg-red-700" : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              {isReviewing ? "Review in Progress..." : assessment.requires_human_review ? "REVIEW REQUIRED" : "Begin Physician Review"}
            </button>
          )}
        </div>
        {(assessment.review_reason || assessment.warnings.length > 0) && (
          <div className="px-5 py-3 space-y-2 border-t border-gray-200/50 dark:border-gray-700/50">
            {assessment.review_reason && (
              <div className="px-3 py-2 rounded bg-yellow-100 dark:bg-yellow-900/20 text-xs text-amber-800 dark:text-amber-300 font-medium">
                Review Reason: {assessment.review_reason}
              </div>
            )}
            {assessment.warnings.map((w, i) => (
              <div key={i} className="px-3 py-2 rounded bg-red-100 dark:bg-red-900/20 text-xs text-red-700 dark:text-red-400">
                <strong>WARNING:</strong> {w}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* HITL Review Panel */}
      {isReviewing && (
        <HITLReviewPanel
          assessment={assessment}
          reviewState={reviewState}
          isSubmitting={isSubmittingReview}
          onToggleDiagnosis={onToggleDiagnosis}
          onToggleTreatment={onToggleTreatment}
          onSubmitReview={onSubmitReview}
          onNotesChange={onNotesChange}
        />
      )}

      {/* Post-Review Panel */}
      {reviewState.submittedReview && (
        <PostReviewPanel
          review={reviewState.submittedReview}
          document={reviewState.generatedDocument}
          ehrOrders={reviewState.ehrOrders}
          onGenerateDocument={onGenerateDocument}
          onCreateOrders={onCreateOrders}
        />
      )}

      {/* Critical Findings */}
      {assessment.critical_findings.length > 0 && (
        <div className="rounded-lg border-2 border-red-500 dark:border-red-700 overflow-hidden">
          <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-300 dark:border-red-700 flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-red-700 dark:text-red-400">Critical Findings</span>
            <span className="px-2 py-0.5 rounded-full bg-red-600 text-white text-[10px] font-bold">{assessment.critical_findings.length}</span>
          </div>
          <div className="p-4 space-y-2">
            {assessment.critical_findings.map((f, i) => <FindingCard key={i} finding={f} />)}
          </div>
        </div>
      )}

      {/* Diagnoses */}
      <Section title={`AI-Generated Diagnoses (${assessment.diagnoses.length})`}>
        {assessment.diagnoses.length > 0 ? (
          <div className="space-y-3">
            {assessment.diagnoses.map((dx, i) => <DiagnosisCard key={i} diagnosis={dx} index={i + 1} />)}
          </div>
        ) : <p className="text-center text-xs text-gray-400 py-5">No diagnoses identified from available clinical data</p>}
      </Section>

      {/* Treatments */}
      <Section title={`Treatment Recommendations (${assessment.treatments.length})`}>
        {assessment.treatments.length > 0 ? (
          <div className="space-y-3">
            {assessment.treatments.map((tx, i) => <TreatmentCard key={i} treatment={tx} index={i + 1} />)}
          </div>
        ) : <p className="text-center text-xs text-gray-400 py-5">No specific treatments recommended</p>}
      </Section>

      {/* Clinical Codes */}
      <Section title="Clinical Billing Codes">
        <div className="grid grid-cols-2 gap-5">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-400 mb-2">ICD-10 Diagnosis Codes</p>
            {assessment.icd10_codes.length > 0 ? (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-1.5 px-2 text-gray-500 font-semibold">Code</th>
                    <th className="text-left py-1.5 px-2 text-gray-500 font-semibold">Description</th>
                    <th className="text-right py-1.5 px-2 text-gray-500 font-semibold">Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {assessment.icd10_codes.map((c, i) => (
                    <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-1.5 px-2 font-semibold text-blue-700 dark:text-blue-400">{c.code}</td>
                      <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{c.description}</td>
                      <td className="py-1.5 px-2 text-right text-gray-500">{(c.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-[11px] text-gray-400">No ICD-10 codes suggested</p>}
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-2">CPT Procedure Codes</p>
            {assessment.cpt_codes.length > 0 ? (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-1.5 px-2 text-gray-500 font-semibold">Code</th>
                    <th className="text-left py-1.5 px-2 text-gray-500 font-semibold">Description</th>
                    <th className="text-left py-1.5 px-2 text-gray-500 font-semibold">Category</th>
                  </tr>
                </thead>
                <tbody>
                  {assessment.cpt_codes.map((c, i) => (
                    <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-1.5 px-2 font-semibold text-emerald-700 dark:text-emerald-400">{c.code}</td>
                      <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{c.description}</td>
                      <td className="py-1.5 px-2 text-gray-500 capitalize">{c.category}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="text-[11px] text-gray-400">No CPT codes suggested</p>}
          </div>
        </div>
      </Section>

      {/* Clinical Findings Grid */}
      {assessment.findings.length > 0 && (
        <Section title={`Clinical Findings (${assessment.findings.length})`}>
          <div className="grid grid-cols-3 gap-2">
            {assessment.findings.map((f, i) => <FindingCard key={i} finding={f} compact />)}
          </div>
        </Section>
      )}

      {/* AI Reasoning */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div
          className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between cursor-pointer"
          onClick={onToggleReasoning}
        >
          <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
            AI Clinical Reasoning ({assessment.reasoning.length} steps)
          </span>
          <span className="text-[10px] text-gray-400">{showReasoning ? "Click to collapse" : "Click to expand"}</span>
        </div>
        {showReasoning && (
          <div className="max-h-96 overflow-auto">
            {assessment.reasoning.map((step, i) => (
              <div key={i} className={`flex gap-3 px-4 py-2.5 text-xs font-mono leading-relaxed whitespace-pre-wrap ${i % 2 === 0 ? "bg-gray-50/50 dark:bg-gray-800/30" : ""} border-b border-gray-100 dark:border-gray-800`}>
                <span className="text-gray-400 font-semibold min-w-[20px] text-right">{i + 1}.</span>
                <span className="text-gray-700 dark:text-gray-300">{step}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// HITL Review Panel
// ══════════════════════════════════════════════════════════════════════════════

function HITLReviewPanel({ assessment, reviewState, isSubmitting, onToggleDiagnosis, onToggleTreatment, onSubmitReview, onNotesChange }: {
  assessment: ClinicalAssessmentResult;
  reviewState: ReviewState;
  isSubmitting: boolean;
  onToggleDiagnosis: (i: number) => void;
  onToggleTreatment: (i: number) => void;
  onSubmitReview: (s: "approved" | "rejected" | "modified") => void;
  onNotesChange: (n: string) => void;
}) {
  return (
    <div className="rounded-lg border-2 border-blue-500 dark:border-blue-700 overflow-hidden">
      <div className="px-4 py-3 bg-gradient-to-r from-slate-800 to-blue-800 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b border-blue-600">
        <span className="w-5 h-5 rounded-full bg-white/20 inline-flex items-center justify-center text-sm">&#9745;</span>
        Human-in-the-Loop (HITL) Physician Review
      </div>
      <div className="p-4 space-y-5">
        {/* Info Banner */}
        <div className="rounded-md bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 px-3 py-2.5 text-[11px] text-blue-800 dark:text-blue-300 leading-relaxed">
          <strong>Physician Attestation Required:</strong> You are responsible for evaluating each AI-generated recommendation. Toggle items to approve or reject. Your clinical judgment supersedes AI recommendations.
        </div>

        {/* Diagnoses Review */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Review AI Diagnoses</p>
            <p className="text-[10px] text-gray-500">{reviewState.approvedDiagnoses.size} of {assessment.diagnoses.length} approved</p>
          </div>
          <div className="space-y-1.5">
            {assessment.diagnoses.map((dx, i) => {
              const ok = reviewState.approvedDiagnoses.has(i);
              return (
                <label key={i} className={`flex items-center gap-3 rounded-md px-3 py-2.5 cursor-pointer border transition ${ok ? "bg-emerald-50 dark:bg-emerald-900/15 border-emerald-300 dark:border-emerald-700" : "bg-red-50 dark:bg-red-900/15 border-red-300 dark:border-red-700"}`}>
                  <input type="checkbox" checked={ok} onChange={() => onToggleDiagnosis(i)} className="h-4 w-4 rounded" style={{ accentColor: ok ? "#059669" : "#dc2626" }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-gray-900 dark:text-gray-100">{dx.diagnosis}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">ICD-10: <strong>{dx.icd10_code}</strong> &middot; AI Confidence: {(dx.confidence * 100).toFixed(0)}%</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded text-[10px] font-bold text-white min-w-[64px] text-center ${ok ? "bg-emerald-600" : "bg-red-600"}`}>
                    {ok ? "APPROVED" : "REJECTED"}
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Treatments Review */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Review Treatment Recommendations</p>
            <p className="text-[10px] text-gray-500">{reviewState.approvedTreatments.size} of {assessment.treatments.length} approved</p>
          </div>
          <div className="space-y-1.5">
            {assessment.treatments.map((tx, i) => {
              const ok = reviewState.approvedTreatments.has(i);
              return (
                <label key={i} className={`flex items-center gap-3 rounded-md px-3 py-2.5 cursor-pointer border transition ${ok ? "bg-emerald-50 dark:bg-emerald-900/15 border-emerald-300 dark:border-emerald-700" : "bg-red-50 dark:bg-red-900/15 border-red-300 dark:border-red-700"}`}>
                  <input type="checkbox" checked={ok} onChange={() => onToggleTreatment(i)} className="h-4 w-4 rounded" style={{ accentColor: ok ? "#059669" : "#dc2626" }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-gray-900 dark:text-gray-100">{tx.description}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">Type: {tx.treatment_type} &middot; Priority: <strong className="capitalize">{tx.priority}</strong>{tx.cpt_code && <> &middot; CPT: {tx.cpt_code}</>}</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded text-[10px] font-bold text-white min-w-[64px] text-center ${ok ? "bg-emerald-600" : "bg-red-600"}`}>
                    {ok ? "APPROVED" : "REJECTED"}
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Notes */}
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 mb-1.5">Physician Clinical Notes & Rationale</p>
          <textarea
            value={reviewState.physicianNotes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder="Document your clinical rationale, modifications, or rejection reason. This note is part of the permanent record."
            className="w-full min-h-[80px] rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-xs text-gray-900 dark:text-gray-100 resize-y focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
          />
        </div>

        {/* Attestation + Buttons */}
        <div className="rounded-md bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 px-4 py-3">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">
            By submitting this review, I attest that I have personally reviewed the AI-generated clinical assessment, including all diagnoses, treatment recommendations, and supporting evidence. My decisions reflect my independent clinical judgment.
          </p>
          <div className="flex gap-3 justify-end">
            <button onClick={() => onSubmitReview("rejected")} disabled={isSubmitting} className="px-5 py-2 rounded-md bg-red-600 text-white text-xs font-bold shadow-sm hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
              {isSubmitting ? "Submitting..." : "Reject Assessment"}
            </button>
            <button onClick={() => onSubmitReview("modified")} disabled={isSubmitting} className="px-5 py-2 rounded-md bg-blue-700 text-white text-xs font-bold shadow-sm hover:bg-blue-800 transition disabled:opacity-50 disabled:cursor-not-allowed">
              {isSubmitting ? "Submitting..." : "Approve with Modifications"}
            </button>
            <button onClick={() => onSubmitReview("approved")} disabled={isSubmitting} className="px-5 py-2 rounded-md bg-emerald-600 text-white text-xs font-bold shadow-sm hover:bg-emerald-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
              {isSubmitting ? "Submitting..." : "Approve All & Attest"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Post-Review Panel
// ══════════════════════════════════════════════════════════════════════════════

function PostReviewPanel({ review, document: doc, ehrOrders, onGenerateDocument, onCreateOrders }: {
  review: PhysicianReviewResult;
  document?: ClinicalDocumentResult;
  ehrOrders?: EHROrderResult[];
  onGenerateDocument: () => void;
  onCreateOrders: () => void;
}) {
  return (
    <div className="rounded-lg border-2 border-emerald-400 dark:border-emerald-700 overflow-hidden">
      <div className="px-4 py-3 bg-gradient-to-r from-emerald-800 to-green-700 text-white text-xs font-bold uppercase tracking-wider flex items-center justify-between border-b border-emerald-600">
        <span className="flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-white/20 inline-flex items-center justify-center text-sm">{"\u2713"}</span>
          Physician Review Completed
        </span>
        <span className="font-normal text-[10px] opacity-80">
          {review.review_completed_at ? new Date(review.review_completed_at).toLocaleString() : new Date(review.created_at).toLocaleString()}
        </span>
      </div>
      <div className="p-4 space-y-4">
        {/* Summary Grid */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Review ID", value: review.id.length > 12 ? review.id.slice(0, 12) + "..." : review.id },
            { label: "Decision", value: review.decision.replace("_", " ").toUpperCase(), color: review.decision === "approved" ? "text-emerald-600" : review.decision === "rejected" ? "text-red-600" : "text-blue-600" },
            { label: "Attested", value: review.attested ? "YES" : "NO", color: review.attested ? "text-emerald-600" : "text-red-600" },
            { label: "Review Time", value: review.time_spent_seconds > 0 ? `${Math.floor(review.time_spent_seconds / 60)}m ${review.time_spent_seconds % 60}s` : "N/A" },
          ].map((item, i) => (
            <div key={i} className="text-center rounded-md bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 px-3 py-2.5">
              <p className="text-[10px] uppercase text-gray-500 mb-0.5">{item.label}</p>
              <p className={`text-xs font-bold font-mono ${(item as { color?: string }).color || "text-gray-900 dark:text-gray-100"}`}>{item.value}</p>
            </div>
          ))}
        </div>

        {/* Signature */}
        {review.signature_datetime && (
          <div className="rounded-md bg-emerald-50 dark:bg-emerald-900/15 border border-emerald-200 dark:border-emerald-800 px-3 py-2 text-[11px] text-emerald-800 dark:text-emerald-300">
            <strong>Electronically signed</strong> by {review.physician_name}
            {review.physician_npi && <> (NPI: {review.physician_npi})</>}
            {review.physician_specialty && <> &middot; {review.physician_specialty}</>}
            {" on "}{new Date(review.signature_datetime).toLocaleString()}
          </div>
        )}

        {/* Final Codes */}
        {(review.final_icd10_codes?.length > 0 || review.final_cpt_codes?.length > 0) && (
          <div className="grid grid-cols-2 gap-4">
            {review.final_icd10_codes?.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-400 mb-1.5">Final ICD-10</p>
                <div className="flex flex-wrap gap-1">{review.final_icd10_codes.map((c, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 text-[10px] font-semibold border border-blue-200 dark:border-blue-700">{c.code}</span>
                ))}</div>
              </div>
            )}
            {review.final_cpt_codes?.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-1.5">Final CPT</p>
                <div className="flex flex-wrap gap-1">{review.final_cpt_codes.map((c, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-400 text-[10px] font-semibold border border-emerald-200 dark:border-emerald-700">{c.code}</span>
                ))}</div>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <button onClick={onGenerateDocument} className="px-4 py-2 rounded-md bg-indigo-600 text-white text-xs font-bold shadow-sm hover:bg-indigo-700 transition">
            Generate Clinical Document
          </button>
          <button onClick={onCreateOrders} disabled={review.decision === "rejected"} className="px-4 py-2 rounded-md bg-cyan-600 text-white text-xs font-bold shadow-sm hover:bg-cyan-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
            Create EHR Orders
          </button>
        </div>

        {/* Generated Document */}
        {doc && (
          <div className="rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700">
              <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">{doc.title}</p>
              <div className="flex gap-2 items-center">
                <button onClick={async () => { try { await downloadClinicalDocument(doc.id, doc.title, "pdf"); } catch { alert("PDF download failed"); } }} className="px-2 py-0.5 rounded bg-red-600 text-white text-[10px] font-bold">PDF</button>
                <button onClick={async () => { try { await downloadClinicalDocument(doc.id, doc.title, "html"); } catch { alert("HTML download failed"); } }} className="px-2 py-0.5 rounded bg-blue-600 text-white text-[10px] font-bold">HTML</button>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${doc.status === "final" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{doc.status.toUpperCase()}</span>
              </div>
            </div>
            <div className="max-h-72 overflow-auto p-4 text-xs" dangerouslySetInnerHTML={{ __html: doc.content }} />
          </div>
        )}

        {/* EHR Orders */}
        {ehrOrders && ehrOrders.length > 0 && (
          <div className="rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-3 py-2 bg-sky-50 dark:bg-sky-900/20 border-b border-gray-200 dark:border-gray-700 text-xs font-semibold text-sky-800 dark:text-sky-400">
              EHR Orders Created ({ehrOrders.length})
            </div>
            <div className="p-3 space-y-1.5">
              {ehrOrders.map((o, i) => (
                <div key={i} className="flex items-center justify-between rounded bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-700 px-3 py-2">
                  <div>
                    <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">{o.description}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">Type: {o.order_type}{o.cpt_code && <> &middot; CPT: <strong>{o.cpt_code}</strong></>}{o.ehr_order_id && <> &middot; EHR: {o.ehr_order_id}</>}</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${o.status === "submitted" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{o.status.toUpperCase()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Card Components
// ══════════════════════════════════════════════════════════════════════════════

function FindingCard({ finding, compact }: { finding: ClinicalFinding; compact?: boolean }) {
  const cfg = {
    normal: { bg: "bg-emerald-50 dark:bg-emerald-900/15", border: "border-emerald-200 dark:border-emerald-800", text: "text-emerald-700 dark:text-emerald-400", badge: "bg-emerald-600" },
    abnormal: { bg: "bg-amber-50 dark:bg-amber-900/15", border: "border-amber-200 dark:border-amber-800", text: "text-amber-700 dark:text-amber-400", badge: "bg-amber-600" },
    critical: { bg: "bg-red-50 dark:bg-red-900/15", border: "border-red-200 dark:border-red-800", text: "text-red-700 dark:text-red-400", badge: "bg-red-600" },
  };
  const c = cfg[finding.status] || cfg.normal;

  if (compact) {
    return (
      <div className={`rounded-md ${c.bg} border ${c.border} px-2.5 py-2`}>
        <p className={`text-[11px] font-semibold ${c.text}`}>{finding.name}</p>
        <p className="text-[10px] text-gray-500">{finding.value} {finding.unit || ""}</p>
      </div>
    );
  }

  return (
    <div className={`rounded-md ${c.bg} border ${c.border} p-3`}>
      <div className="flex items-start justify-between">
        <div>
          <p className={`text-xs font-bold ${c.text}`}>{finding.name}</p>
          <p className="text-base font-bold text-gray-900 dark:text-gray-100 mt-1">{finding.value} {finding.unit || ""}</p>
        </div>
        <span className={`${c.badge} text-white px-2 py-0.5 rounded text-[9px] font-bold uppercase`}>{finding.status}</span>
      </div>
      <p className="text-[11px] text-gray-600 dark:text-gray-400 mt-2">{finding.interpretation}</p>
      {finding.reference_range && <p className="text-[10px] text-gray-400 mt-1">Ref: {finding.reference_range}</p>}
    </div>
  );
}

function DiagnosisCard({ diagnosis, index }: { diagnosis: AIDiagnosisRecommendation; index: number }) {
  const [open, setOpen] = useState(false);
  const confColor = diagnosis.confidence >= 0.8 ? "text-emerald-600" : diagnosis.confidence >= 0.5 ? "text-amber-600" : "text-red-600";

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
      <div className="flex items-center gap-3 px-4 py-3 cursor-pointer bg-gray-50/50 dark:bg-gray-800/30 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition" onClick={() => setOpen(!open)}>
        <span className="w-7 h-7 rounded-full bg-blue-800 text-white text-[11px] font-bold flex items-center justify-center shrink-0">{index}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{diagnosis.diagnosis}</p>
          <div className="flex gap-4 mt-1 text-[11px] text-gray-500">
            <span>ICD-10: <strong className="text-blue-700 dark:text-blue-400">{diagnosis.icd10_code}</strong></span>
            <span>Confidence: <strong className={confColor}>{(diagnosis.confidence * 100).toFixed(0)}%</strong></span>
          </div>
        </div>
        <span className="text-gray-400 text-xs">{open ? "\u25BC" : "\u25B6"}</span>
      </div>
      {open && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 space-y-3 text-xs">
          <div>
            <SectionLabel>Clinical Rationale</SectionLabel>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{diagnosis.rationale}</p>
          </div>
          {diagnosis.supporting_findings?.length > 0 && (
            <div>
              <SectionLabel>Supporting Findings</SectionLabel>
              <div className="flex flex-wrap gap-1">{diagnosis.supporting_findings.map((f, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-[10px]">{f.name}: {f.value} {f.unit || ""}</span>
              ))}</div>
            </div>
          )}
          {diagnosis.differential_diagnoses?.length > 0 && (
            <div>
              <SectionLabel>Differential Diagnoses</SectionLabel>
              <table className="w-full text-[11px]"><tbody>
                {diagnosis.differential_diagnoses.map((dd, i) => (
                  <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-1 text-gray-700 dark:text-gray-300">{dd.diagnosis}</td>
                    <td className="py-1 px-2 font-semibold text-blue-700 dark:text-blue-400">{dd.icd10}</td>
                    <td className="py-1 text-right text-gray-500">{(dd.confidence * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody></table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TreatmentCard({ treatment, index }: { treatment: AITreatmentRecommendation; index: number }) {
  const pCfg: Record<string, string> = { immediate: "bg-red-600", urgent: "bg-amber-600", routine: "bg-blue-600", elective: "bg-purple-600" };
  const pBg = pCfg[treatment.priority] || pCfg.routine;

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
      <div className="flex items-start gap-3 px-4 py-3">
        <span className="w-7 h-7 rounded-full bg-emerald-700 text-white text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5">{index}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className={`${pBg} text-white px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide`}>{treatment.priority}</span>
            <span className="text-[10px] text-gray-500 capitalize font-medium">{treatment.treatment_type}</span>
            {treatment.cpt_code && <span className="ml-auto px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-semibold">CPT: {treatment.cpt_code}</span>}
          </div>
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{treatment.description}</p>
          <p className="text-[11px] text-gray-500 mt-1 leading-relaxed">{treatment.rationale}</p>
          {treatment.contraindications?.length > 0 && (
            <div className="mt-2 rounded bg-red-50 dark:bg-red-900/15 border border-red-200 dark:border-red-800 px-2.5 py-1.5 text-[11px]">
              <strong className="text-red-700 dark:text-red-400">Contraindications:</strong> <span className="text-red-600 dark:text-red-300">{treatment.contraindications.join("; ")}</span>
            </div>
          )}
          {treatment.monitoring?.length > 0 && (
            <div className="mt-1.5 rounded bg-sky-50 dark:bg-sky-900/15 border border-sky-200 dark:border-sky-800 px-2.5 py-1.5 text-[11px]">
              <strong className="text-sky-700 dark:text-sky-400">Monitoring:</strong> <span className="text-sky-600 dark:text-sky-300">{treatment.monitoring.join("; ")}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Shared tiny helpers
// ══════════════════════════════════════════════════════════════════════════════

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
        {title}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5">{children}</p>;
}
