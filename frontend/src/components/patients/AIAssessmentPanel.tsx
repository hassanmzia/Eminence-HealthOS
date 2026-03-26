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
