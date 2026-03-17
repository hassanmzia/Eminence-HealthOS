"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  fetchImagingStudies,
  analyzeImage,
  fetchImagingWorklist,
  evaluateCriticalFinding,
} from "@/lib/api";

/* ─── Types ──────────────────────────────────────────────────────────────── */

type Modality = "CT" | "MRI" | "X-Ray" | "US" | "PET";
type StudyStatus = "scheduled" | "in-progress" | "completed" | "reported";
type Priority = "STAT" | "Urgent" | "Routine";
type Severity = "critical" | "moderate" | "mild" | "normal";
type CommStatus = "notified" | "pending" | "acknowledged";
type TabKey = "worklist" | "ai-analysis" | "studies-by-patient" | "critical-findings";

interface WorklistStudy {
  id: string;
  patient: string;
  modality: Modality;
  bodyPart: string;
  description: string;
  status: StudyStatus;
  date: string;
  radiologist: string;
  priority: Priority;
  slaMinutesRemaining: number;
}

interface AIFinding {
  id: string;
  studyId: string;
  description: string;
  confidence: number;
  severity: Severity;
  recommendedAction: string;
  model: string;
  bodyPart: string;
}

interface PatientStudy {
  id: string;
  patientId: string;
  patientName: string;
  modality: Modality;
  bodyPart: string;
  description: string;
  status: StudyStatus;
  date: string;
  reportText: string | null;
}

interface CriticalFinding {
  id: string;
  studyId: string;
  patient: string;
  description: string;
  severity: Severity;
  aiConfidence: number;
  timeDetected: string;
  commStatus: CommStatus;
  resolved: boolean;
}

/* ─── Demo Data ──────────────────────────────────────────────────────────── */

const DEMO_WORKLIST: WorklistStudy[] = [
  { id: "WL-001", patient: "Maria Garcia", modality: "CT", bodyPart: "Chest", description: "CT Chest w/ Contrast — PE Protocol", status: "in-progress", date: "2026-03-15 08:12", radiologist: "Dr. Rodriguez", priority: "STAT", slaMinutesRemaining: 14 },
  { id: "WL-002", patient: "James Wilson", modality: "MRI", bodyPart: "Brain", description: "MRI Brain w/o Contrast", status: "scheduled", date: "2026-03-15 09:00", radiologist: "Dr. Chen", priority: "Urgent", slaMinutesRemaining: 42 },
  { id: "WL-003", patient: "Emily Davis", modality: "X-Ray", bodyPart: "Chest", description: "PA & Lateral Chest X-ray", status: "completed", date: "2026-03-15 07:45", radiologist: "Dr. Kim", priority: "Routine", slaMinutesRemaining: 88 },
  { id: "WL-004", patient: "Robert Johnson", modality: "US", bodyPart: "Abdomen", description: "Abdominal Ultrasound — RUQ", status: "completed", date: "2026-03-15 06:30", radiologist: "Dr. Rodriguez", priority: "Routine", slaMinutesRemaining: 120 },
  { id: "WL-005", patient: "Sarah Chen", modality: "PET", bodyPart: "Whole Body", description: "PET/CT Oncology Restaging", status: "scheduled", date: "2026-03-15 10:30", radiologist: "Dr. Patel", priority: "Urgent", slaMinutesRemaining: 55 },
  { id: "WL-006", patient: "Michael Brown", modality: "CT", bodyPart: "Abdomen/Pelvis", description: "CT Abdomen & Pelvis w/ Contrast", status: "reported", date: "2026-03-15 05:15", radiologist: "Dr. Chen", priority: "Routine", slaMinutesRemaining: 0 },
  { id: "WL-007", patient: "Lisa Taylor", modality: "MRI", bodyPart: "Lumbar Spine", description: "MRI Lumbar Spine w/o Contrast", status: "in-progress", date: "2026-03-15 08:45", radiologist: "Dr. Kim", priority: "Urgent", slaMinutesRemaining: 28 },
  { id: "WL-008", patient: "David Martinez", modality: "X-Ray", bodyPart: "Left Ankle", description: "X-Ray Left Ankle 3-View", status: "completed", date: "2026-03-15 07:20", radiologist: "—", priority: "Routine", slaMinutesRemaining: 95 },
  { id: "WL-009", patient: "Karen White", modality: "CT", bodyPart: "Head", description: "CT Head w/o Contrast — Stroke Alert", status: "in-progress", date: "2026-03-15 08:55", radiologist: "Dr. Rodriguez", priority: "STAT", slaMinutesRemaining: 8 },
  { id: "WL-010", patient: "John Anderson", modality: "US", bodyPart: "Thyroid", description: "Thyroid Ultrasound w/ Doppler", status: "scheduled", date: "2026-03-15 11:00", radiologist: "Dr. Patel", priority: "Routine", slaMinutesRemaining: 145 },
];

const DEMO_AI_FINDINGS: AIFinding[] = [
  { id: "AI-001", studyId: "WL-001", description: "Filling defect in right main pulmonary artery consistent with pulmonary embolism", confidence: 0.94, severity: "critical", recommendedAction: "Immediate clinical correlation; recommend anticoagulation consult", model: "PEDetect-v3", bodyPart: "Chest" },
  { id: "AI-002", studyId: "WL-003", description: "Mild cardiomegaly with cardiothoracic ratio of 0.56", confidence: 0.88, severity: "moderate", recommendedAction: "Compare with prior studies; echocardiogram if new finding", model: "CheXNet-v2", bodyPart: "Chest" },
  { id: "AI-003", studyId: "WL-003", description: "No acute pulmonary infiltrate identified", confidence: 0.96, severity: "normal", recommendedAction: "No further imaging required", model: "CheXNet-v2", bodyPart: "Chest" },
  { id: "AI-004", studyId: "WL-004", description: "Gallbladder wall thickening with pericholecystic fluid", confidence: 0.72, severity: "moderate", recommendedAction: "Clinical correlation for acute cholecystitis; HIDA scan if equivocal", model: "AbdoScan-v1", bodyPart: "Abdomen" },
  { id: "AI-005", studyId: "WL-006", description: "3.2cm hypodense hepatic lesion in segment VII — indeterminate", confidence: 0.65, severity: "moderate", recommendedAction: "Recommend MRI liver with hepatocyte-specific contrast for characterization", model: "AbdoScan-v1", bodyPart: "Abdomen/Pelvis" },
  { id: "AI-006", studyId: "WL-009", description: "Hyperdense focus in left basal ganglia — possible acute hemorrhage", confidence: 0.91, severity: "critical", recommendedAction: "STAT neurosurgery consult; repeat imaging in 6 hours", model: "DeepBleed-v2", bodyPart: "Head" },
];

const DEMO_PATIENT_STUDIES: PatientStudy[] = [
  { id: "PS-001", patientId: "P-100", patientName: "Maria Garcia", modality: "CT", bodyPart: "Chest", description: "CT Chest w/ Contrast — PE Protocol", status: "in-progress", date: "2026-03-15", reportText: null },
  { id: "PS-002", patientId: "P-100", patientName: "Maria Garcia", modality: "X-Ray", bodyPart: "Chest", description: "PA & Lateral Chest", status: "reported", date: "2026-02-28", reportText: "FINDINGS: Heart size is mildly enlarged. Lungs are clear. No pleural effusion. No pneumothorax.\n\nIMPRESSION: Mild cardiomegaly, unchanged from prior. No acute cardiopulmonary process." },
  { id: "PS-003", patientId: "P-100", patientName: "Maria Garcia", modality: "CT", bodyPart: "Abdomen/Pelvis", description: "CT Abdomen & Pelvis w/ Contrast", status: "reported", date: "2026-01-10", reportText: "FINDINGS: Liver, spleen, pancreas, adrenals unremarkable. Kidneys enhance symmetrically without hydronephrosis. No free fluid. No lymphadenopathy.\n\nIMPRESSION: No acute intra-abdominal abnormality." },
  { id: "PS-004", patientId: "P-101", patientName: "James Wilson", modality: "MRI", bodyPart: "Brain", description: "MRI Brain w/o Contrast", status: "scheduled", date: "2026-03-15", reportText: null },
  { id: "PS-005", patientId: "P-101", patientName: "James Wilson", modality: "CT", bodyPart: "Head", description: "CT Head w/o Contrast", status: "reported", date: "2026-03-01", reportText: "FINDINGS: No intracranial hemorrhage, mass effect, or midline shift. Ventricles are normal in size. Gray-white matter differentiation is preserved.\n\nIMPRESSION: Normal non-contrast CT head." },
  { id: "PS-006", patientId: "P-102", patientName: "Emily Davis", modality: "X-Ray", bodyPart: "Chest", description: "PA & Lateral Chest X-ray", status: "completed", date: "2026-03-15", reportText: null },
  { id: "PS-007", patientId: "P-102", patientName: "Emily Davis", modality: "US", bodyPart: "Pelvis", description: "Pelvic Ultrasound", status: "reported", date: "2026-02-05", reportText: "FINDINGS: Uterus is anteverted and normal in size. Endometrial stripe measures 6mm. Ovaries are normal bilaterally. No adnexal mass or free fluid.\n\nIMPRESSION: Normal pelvic ultrasound." },
  { id: "PS-008", patientId: "P-103", patientName: "Robert Johnson", modality: "US", bodyPart: "Abdomen", description: "Abdominal Ultrasound — RUQ", status: "completed", date: "2026-03-15", reportText: null },
  { id: "PS-009", patientId: "P-103", patientName: "Robert Johnson", modality: "MRI", bodyPart: "Lumbar Spine", description: "MRI Lumbar Spine", status: "reported", date: "2025-12-20", reportText: "FINDINGS: L4-L5 disc desiccation with broad-based disc protrusion causing mild central canal narrowing. Facet arthropathy at L5-S1. No nerve root compression.\n\nIMPRESSION: L4-L5 disc protrusion with mild central canal stenosis. Facet arthropathy at L5-S1." },
  { id: "PS-010", patientId: "P-104", patientName: "Sarah Chen", modality: "PET", bodyPart: "Whole Body", description: "PET/CT Oncology Restaging", status: "scheduled", date: "2026-03-15", reportText: null },
  { id: "PS-011", patientId: "P-104", patientName: "Sarah Chen", modality: "CT", bodyPart: "Chest/Abdomen/Pelvis", description: "CT CAP w/ Contrast — Oncology", status: "reported", date: "2026-02-01", reportText: "FINDINGS: Known 1.8cm right lower lobe nodule stable compared to prior. No new pulmonary nodules. Mediastinal lymph nodes stable. Liver, spleen, adrenals unremarkable.\n\nIMPRESSION: Stable disease per RECIST criteria. No new metastatic disease." },
];

const DEMO_CRITICAL_FINDINGS: CriticalFinding[] = [
  { id: "CF-001", studyId: "WL-001", patient: "Maria Garcia", description: "Filling defect in right main pulmonary artery — acute PE", severity: "critical", aiConfidence: 0.94, timeDetected: "2026-03-15 08:18", commStatus: "notified", resolved: false },
  { id: "CF-002", studyId: "WL-009", patient: "Karen White", description: "Hyperdense focus in left basal ganglia — possible acute hemorrhage", severity: "critical", aiConfidence: 0.91, timeDetected: "2026-03-15 09:02", commStatus: "pending", resolved: false },
  { id: "CF-003", studyId: "STD-220", patient: "Thomas Lee", description: "Large left-sided pneumothorax with mediastinal shift", severity: "critical", aiConfidence: 0.97, timeDetected: "2026-03-14 22:45", commStatus: "acknowledged", resolved: false },
  { id: "CF-004", studyId: "STD-198", patient: "Jane Smith", description: "Intracranial hemorrhage — right temporal lobe", severity: "critical", aiConfidence: 0.93, timeDetected: "2026-03-14 14:22", commStatus: "acknowledged", resolved: true },
  { id: "CF-005", studyId: "STD-185", patient: "Bob Wilson", description: "Saddle pulmonary embolism with right heart strain", severity: "critical", aiConfidence: 0.96, timeDetected: "2026-03-13 03:45", commStatus: "acknowledged", resolved: true },
  { id: "CF-006", studyId: "STD-172", patient: "Alice Park", description: "Aortic dissection — Stanford Type B", severity: "critical", aiConfidence: 0.89, timeDetected: "2026-03-12 19:30", commStatus: "acknowledged", resolved: true },
];

/* ─── Helper Functions ───────────────────────────────────────────────────── */

const TABS: { key: TabKey; label: string }[] = [
  { key: "worklist", label: "Worklist" },
  { key: "ai-analysis", label: "AI Analysis" },
  { key: "studies-by-patient", label: "Studies by Patient" },
  { key: "critical-findings", label: "Critical Findings" },
];

function modalityBadge(m: Modality) {
  const map: Record<Modality, string> = {
    CT: "bg-blue-100 text-blue-800 border-blue-200",
    MRI: "bg-purple-100 text-purple-800 border-purple-200",
    "X-Ray": "bg-green-100 text-green-800 border-green-200",
    US: "bg-teal-100 text-teal-800 border-teal-200",
    PET: "bg-orange-100 text-orange-800 border-orange-200",
  };
  return map[m] ?? "bg-gray-100 text-gray-800 border-gray-200";
}

function modalityIcon(m: Modality) {
  const map: Record<Modality, string> = {
    CT: "🔵",
    MRI: "🟣",
    "X-Ray": "🟢",
    US: "🔷",
    PET: "🟠",
  };
  return map[m] ?? "⚪";
}

function statusBadge(s: StudyStatus) {
  const map: Record<StudyStatus, string> = {
    scheduled: "bg-gray-100 text-gray-700 border-gray-200",
    "in-progress": "bg-blue-100 text-blue-700 border-blue-200",
    completed: "bg-yellow-100 text-yellow-700 border-yellow-200",
    reported: "bg-green-100 text-green-700 border-green-200",
  };
  return map[s] ?? "bg-gray-100 text-gray-700 border-gray-200";
}

function priorityBadge(p: Priority) {
  const map: Record<Priority, string> = {
    STAT: "bg-red-100 text-red-800 border-red-300",
    Urgent: "bg-orange-100 text-orange-800 border-orange-300",
    Routine: "bg-gray-100 text-gray-600 border-gray-200",
  };
  return map[p] ?? "bg-gray-100 text-gray-600 border-gray-200";
}

function severityBadge(s: Severity) {
  const map: Record<Severity, string> = {
    critical: "bg-red-100 text-red-800 border-red-300",
    moderate: "bg-orange-100 text-orange-800 border-orange-300",
    mild: "bg-yellow-100 text-yellow-800 border-yellow-300",
    normal: "bg-green-100 text-green-800 border-green-300",
  };
  return map[s] ?? "bg-gray-100 text-gray-700 border-gray-200";
}

function commStatusBadge(c: CommStatus) {
  const map: Record<CommStatus, string> = {
    notified: "bg-blue-100 text-blue-800",
    pending: "bg-yellow-100 text-yellow-800",
    acknowledged: "bg-green-100 text-green-800",
  };
  return map[c] ?? "bg-gray-100 text-gray-700";
}

function confidenceColor(c: number): string {
  if (c >= 0.9) return "bg-green-500";
  if (c >= 0.7) return "bg-yellow-500";
  return "bg-red-500";
}

function confidenceTextColor(c: number): string {
  if (c >= 0.9) return "text-green-700";
  if (c >= 0.7) return "text-yellow-700";
  return "text-red-700";
}

function slaColor(minutes: number): string {
  if (minutes <= 0) return "text-gray-400";
  if (minutes <= 15) return "text-red-600";
  if (minutes <= 30) return "text-orange-500";
  return "text-green-600";
}

function formatSLA(minutes: number): string {
  if (minutes <= 0) return "Reported";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

/* ─── Main Page Component ────────────────────────────────────────────────── */

export default function ImagingPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("worklist");
  const [worklist, setWorklist] = useState<WorklistStudy[]>(DEMO_WORKLIST);
  const [aiFindings, setAiFindings] = useState<AIFinding[]>(DEMO_AI_FINDINGS);
  const [patientStudies, setPatientStudies] = useState<PatientStudy[]>(DEMO_PATIENT_STUDIES);
  const [criticalFindings, setCriticalFindings] = useState<CriticalFinding[]>(DEMO_CRITICAL_FINDINGS);

  // AI Analysis tab state
  const [selectedStudyForAI, setSelectedStudyForAI] = useState<string>("");
  const [aiAnalysisRunning, setAiAnalysisRunning] = useState(false);
  const [showCompare, setShowCompare] = useState(false);

  // Studies by Patient tab state
  const [patientSearch, setPatientSearch] = useState("");
  const [expandedReport, setExpandedReport] = useState<string | null>(null);

  // Critical findings state
  const [criticalActionLog, setCriticalActionLog] = useState<string[]>([]);

  // Fetch from API with demo data fallback
  useEffect(() => {
    fetchImagingWorklist()
      .then((data) => {
        if (data && Array.isArray((data as Record<string, unknown>).studies)) {
          setWorklist((data as Record<string, unknown>).studies as WorklistStudy[]);
        }
      })
      .catch(() => {/* use demo data */});

    fetchImagingStudies("all")
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setPatientStudies(data as unknown as PatientStudy[]);
        }
      })
      .catch(() => {/* use demo data */});
  }, []);

  // Computed stats
  const stats = useMemo(() => {
    const today = worklist.filter((s) => s.date.startsWith("2026-03-15"));
    const pending = worklist.filter((s) => s.status === "completed" || s.status === "in-progress");
    const aiAnalyzed = aiFindings.length;
    const critical = criticalFindings.filter((c) => !c.resolved).length;
    return {
      studiesToday: today.length,
      pendingRead: pending.length,
      aiAnalyzed,
      criticalCount: critical,
      avgReportTime: "18 min",
    };
  }, [worklist, aiFindings, criticalFindings]);

  const worklistCount = worklist.length;

  // AI analysis handler
  const handleRunAIAnalysis = useCallback(async () => {
    if (!selectedStudyForAI) return;
    setAiAnalysisRunning(true);
    try {
      const result = await analyzeImage({ study_id: selectedStudyForAI });
      if (result) {
        setAiFindings((prev) => [
          ...prev,
          {
            id: `AI-${Date.now()}`,
            studyId: selectedStudyForAI,
            description: (result as Record<string, unknown>).finding as string || "Analysis complete",
            confidence: (result as Record<string, unknown>).confidence as number || 0.85,
            severity: ((result as Record<string, unknown>).severity as Severity) || "normal",
            recommendedAction: (result as Record<string, unknown>).action as string || "Review findings",
            model: (result as Record<string, unknown>).model as string || "HealthOS-AI",
            bodyPart: "—",
          },
        ]);
      }
    } catch {
      // Demo mode — simulated result
      setAiFindings((prev) => [
        ...prev,
        {
          id: `AI-${Date.now()}`,
          studyId: selectedStudyForAI,
          description: "No significant abnormality detected (simulated)",
          confidence: 0.92,
          severity: "normal",
          recommendedAction: "No action required",
          model: "HealthOS-AI-v1",
          bodyPart: "—",
        },
      ]);
    } finally {
      setAiAnalysisRunning(false);
    }
  }, [selectedStudyForAI]);

  // Critical finding handlers
  const handleEscalate = useCallback(async (findingId: string) => {
    try {
      await evaluateCriticalFinding({ finding_id: findingId, action: "escalate" });
    } catch {
      // demo mode
    }
    setCriticalFindings((prev) =>
      prev.map((f) => (f.id === findingId ? { ...f, commStatus: "notified" as CommStatus } : f))
    );
    setCriticalActionLog((prev) => [`${new Date().toLocaleTimeString()} — Escalated ${findingId}`, ...prev]);
  }, []);

  const handleAcknowledge = useCallback(async (findingId: string) => {
    try {
      await evaluateCriticalFinding({ finding_id: findingId, action: "acknowledge" });
    } catch {
      // demo mode
    }
    setCriticalFindings((prev) =>
      prev.map((f) => (f.id === findingId ? { ...f, commStatus: "acknowledged" as CommStatus } : f))
    );
    setCriticalActionLog((prev) => [`${new Date().toLocaleTimeString()} — Acknowledged ${findingId}`, ...prev]);
  }, []);

  // Patient filtering
  const filteredPatients = useMemo(() => {
    const q = patientSearch.toLowerCase().trim();
    if (!q) return patientStudies;
    return patientStudies.filter(
      (s) =>
        s.patientName.toLowerCase().includes(q) ||
        s.patientId.toLowerCase().includes(q)
    );
  }, [patientSearch, patientStudies]);

  const groupedByPatient = useMemo(() => {
    const map = new Map<string, PatientStudy[]>();
    filteredPatients.forEach((s) => {
      const key = `${s.patientId}|${s.patientName}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    });
    // Sort each group by date descending
    map.forEach((studies) => studies.sort((a, b) => b.date.localeCompare(a.date)));
    return map;
  }, [filteredPatients]);

  const activeCritical = criticalFindings.filter((c) => !c.resolved);
  const resolvedCritical = criticalFindings.filter((c) => c.resolved);

  /* ─── Render ─────────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">Imaging &amp; Radiology</h1>
            <span className="inline-flex items-center rounded-full bg-healthos-100 px-2.5 py-0.5 text-xs font-semibold text-healthos-800 border border-healthos-200">
              {worklistCount} in worklist
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            DICOM worklist management, AI-powered image analysis, patient study history, and critical finding alerts
          </p>
        </div>
        <button
          onClick={() => setActiveTab("ai-analysis")}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-healthos-700 focus:outline-none focus:ring-2 focus:ring-healthos-500 focus:ring-offset-2"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
          AI Analysis
        </button>
      </div>

      {/* ── Stats Bar ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 animate-fade-in-up">
        {[
          { label: "Studies Today", value: String(stats.studiesToday), icon: (
            <svg className="h-5 w-5 text-healthos-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" /><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" /></svg>
          ), sub: "all modalities" },
          { label: "Pending Read", value: String(stats.pendingRead), icon: (
            <svg className="h-5 w-5 text-yellow-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          ), sub: "awaiting radiologist" },
          { label: "AI Analyzed", value: String(stats.aiAnalyzed), icon: (
            <svg className="h-5 w-5 text-purple-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>
          ), sub: "AI-assisted reads" },
          { label: "Critical Findings", value: String(stats.criticalCount), icon: (
            <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
          ), sub: "active alerts" },
          { label: "Avg Report Time", value: stats.avgReportTime, icon: (
            <svg className="h-5 w-5 text-teal-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>
          ), sub: "turnaround" },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover rounded-xl p-4 animate-fade-in-up">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{kpi.label}</p>
              {kpi.icon}
            </div>
            <p className="mt-2 text-2xl font-bold text-gray-900">{kpi.value}</p>
            <p className="mt-0.5 text-xs text-gray-400">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* ── Tabs ────────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                activeTab === t.key
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {t.label}
              {t.key === "critical-findings" && activeCritical.length > 0 && (
                <span className="ml-1.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                  {activeCritical.length}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ──────────────────────────────────────────────────────────────── */}
      {/* TAB 1: Worklist                                                 */}
      {/* ──────────────────────────────────────────────────────────────── */}
      {activeTab === "worklist" && (
        <div className="space-y-4 animate-fade-in-up">
          {worklist.map((study) => (
            <div
              key={study.id}
              className={`card card-hover rounded-xl p-5 transition-all ${
                study.priority === "STAT" ? "border-l-4 border-l-red-500" : study.priority === "Urgent" ? "border-l-4 border-l-orange-400" : ""
              }`}
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                {/* Left section */}
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">{study.patient}</span>
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${modalityBadge(study.modality)}`}>
                      {study.modality}
                    </span>
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${priorityBadge(study.priority)}`}>
                      {study.priority}
                    </span>
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusBadge(study.status)}`}>
                      {study.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">{study.description}</p>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                    <span>Body Part: <span className="font-medium text-gray-700">{study.bodyPart}</span></span>
                    <span>Radiologist: <span className="font-medium text-gray-700">{study.radiologist}</span></span>
                    <span>ID: <span className="font-mono text-gray-400">{study.id}</span></span>
                  </div>
                </div>

                {/* Right section — SLA timer & date */}
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className="text-xs text-gray-400">{study.date}</span>
                  <div className={`flex items-center gap-1.5 text-sm font-semibold ${slaColor(study.slaMinutesRemaining)}`}>
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{formatSLA(study.slaMinutesRemaining)}</span>
                  </div>
                  {study.slaMinutesRemaining > 0 && study.slaMinutesRemaining <= 15 && (
                    <span className="text-[10px] font-medium text-red-500 uppercase tracking-wide">SLA at risk</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────── */}
      {/* TAB 2: AI Analysis                                              */}
      {/* ──────────────────────────────────────────────────────────────── */}
      {activeTab === "ai-analysis" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Upload / Select Section */}
          <div className="card rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Run AI Analysis</h3>
            <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 mb-1">Select Study</label>
                <select
                  value={selectedStudyForAI}
                  onChange={(e) => setSelectedStudyForAI(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Choose a study from the worklist...</option>
                  {worklist.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.id} — {s.patient} — {s.modality} {s.bodyPart}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleRunAIAnalysis}
                disabled={!selectedStudyForAI || aiAnalysisRunning}
                className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-healthos-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {aiAnalysisRunning ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>
                    Analyze with AI
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Simulated Image Placeholder with Annotations */}
          <div className="card rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-4">Image Viewer</h3>
            <div className="relative mx-auto aspect-square max-w-md rounded-lg bg-gray-900 overflow-hidden">
              {/* Simulated DICOM background */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <svg className="mx-auto h-16 w-16 text-gray-600" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" /></svg>
                  <p className="mt-2 text-sm text-gray-500">DICOM Image Placeholder</p>
                  <p className="text-xs text-gray-600">Select a study and run AI analysis to view annotations</p>
                </div>
              </div>
              {/* Annotation overlays */}
              {selectedStudyForAI && aiFindings.filter((f) => f.studyId === selectedStudyForAI).length > 0 && (
                <>
                  <div className="absolute top-4 right-4 rounded bg-black/60 px-2 py-1 text-xs text-green-400 font-mono">
                    AI Annotations Active
                  </div>
                  {/* Simulated annotation boxes */}
                  <div className="absolute top-[30%] left-[25%] h-[30%] w-[40%] rounded border-2 border-red-500 border-dashed opacity-70" />
                  <div className="absolute top-[28%] left-[25%] rounded bg-red-500/80 px-1.5 py-0.5 text-[10px] text-white font-semibold">
                    Finding Detected
                  </div>
                  <div className="absolute bottom-[20%] right-[20%] h-[15%] w-[25%] rounded border-2 border-yellow-400 border-dashed opacity-60" />
                  <div className="absolute bottom-[18%] right-[20%] rounded bg-yellow-500/80 px-1.5 py-0.5 text-[10px] text-white font-semibold">
                    Region of Interest
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Compare with Priors */}
          <div className="card rounded-xl p-6">
            <button
              onClick={() => setShowCompare(!showCompare)}
              className="flex w-full items-center justify-between text-sm font-semibold text-gray-900 uppercase tracking-wide"
            >
              <span>Compare with Priors</span>
              <svg className={`h-5 w-5 text-gray-400 transition-transform ${showCompare ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
            </button>
            {showCompare && (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
                  <p className="text-xs font-medium text-gray-500 mb-2">Current Study (2026-03-15)</p>
                  <div className="aspect-video rounded bg-gray-800 flex items-center justify-center">
                    <span className="text-xs text-gray-500">Current Image</span>
                  </div>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
                  <p className="text-xs font-medium text-gray-500 mb-2">Prior Study (2026-02-28)</p>
                  <div className="aspect-video rounded bg-gray-800 flex items-center justify-center">
                    <span className="text-xs text-gray-500">Prior Image</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* AI Findings Results */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">AI Findings ({aiFindings.length})</h3>
            {aiFindings.map((finding) => (
              <div key={finding.id} className="card card-hover rounded-xl p-5 animate-fade-in-up">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-gray-400">{finding.studyId}</span>
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${severityBadge(finding.severity)}`}>
                      {finding.severity}
                    </span>
                    <span className="text-xs text-gray-400">Model: {finding.model}</span>
                  </div>
                  <p className="text-sm font-medium text-gray-900">{finding.description}</p>

                  {/* Confidence bar */}
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-20 shrink-0">Confidence</span>
                    <div className="flex-1 h-2.5 rounded-full bg-gray-200 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${confidenceColor(finding.confidence)}`}
                        style={{ width: `${finding.confidence * 100}%` }}
                      />
                    </div>
                    <span className={`text-xs font-semibold tabular-nums ${confidenceTextColor(finding.confidence)}`}>
                      {(finding.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs font-medium text-gray-500 mb-0.5">Recommended Action</p>
                    <p className="text-sm text-gray-700">{finding.recommendedAction}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────── */}
      {/* TAB 3: Studies by Patient                                       */}
      {/* ──────────────────────────────────────────────────────────────── */}
      {activeTab === "studies-by-patient" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Search */}
          <div className="card rounded-xl p-4">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>
              <input
                type="text"
                placeholder="Search by patient name or ID..."
                value={patientSearch}
                onChange={(e) => setPatientSearch(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm text-gray-900 placeholder-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
            </div>
          </div>

          {/* Patient groups */}
          {Array.from(groupedByPatient.entries()).map(([key, studies]) => {
            const [patientId, patientName] = key.split("|");
            return (
              <div key={key} className="card rounded-xl overflow-hidden animate-fade-in-up">
                <div className="bg-gray-50 border-b border-gray-200 px-5 py-3 flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-healthos-100 text-healthos-700 text-sm font-bold">
                    {patientName.charAt(0)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{patientName}</p>
                    <p className="text-xs text-gray-400">{patientId} — {studies.length} {studies.length === 1 ? "study" : "studies"}</p>
                  </div>
                </div>
                <div className="divide-y divide-gray-100">
                  {studies.map((study) => (
                    <div key={`${study.patientId}-${study.id}`} className="px-5 py-4">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 text-lg">{modalityIcon(study.modality)}</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${modalityBadge(study.modality)}`}>
                              {study.modality}
                            </span>
                            <span className="text-xs font-medium text-gray-700">{study.bodyPart}</span>
                            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusBadge(study.status)}`}>
                              {study.status}
                            </span>
                            <span className="text-xs text-gray-400">{study.date}</span>
                          </div>
                          <p className="mt-1 text-sm text-gray-600">{study.description}</p>

                          {study.reportText && (
                            <div className="mt-2">
                              <button
                                onClick={() => setExpandedReport(expandedReport === study.id ? null : study.id)}
                                className="inline-flex items-center gap-1 text-xs font-medium text-healthos-600 hover:text-healthos-700"
                              >
                                {expandedReport === study.id ? "Hide Report" : "View Report"}
                                <svg className={`h-3.5 w-3.5 transition-transform ${expandedReport === study.id ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
                              </button>
                              {expandedReport === study.id && (
                                <div className="mt-2 rounded-lg bg-gray-50 border border-gray-200 p-4 animate-fade-in-up">
                                  <p className="whitespace-pre-wrap text-xs text-gray-700 font-mono leading-relaxed">
                                    {study.reportText}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                          {!study.reportText && (
                            <p className="mt-1 text-xs text-gray-400 italic">Report not yet available</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {groupedByPatient.size === 0 && (
            <div className="card rounded-xl p-12 text-center">
              <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>
              <p className="mt-3 text-sm text-gray-500">No patients match your search.</p>
            </div>
          )}
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────── */}
      {/* TAB 4: Critical Findings                                        */}
      {/* ──────────────────────────────────────────────────────────────── */}
      {activeTab === "critical-findings" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Active Critical Findings */}
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
            Active Critical Findings ({activeCritical.length})
          </h3>
          {activeCritical.length === 0 && (
            <div className="card rounded-xl p-8 text-center">
              <svg className="mx-auto h-10 w-10 text-green-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <p className="mt-3 text-sm text-gray-500">No active critical findings. All clear.</p>
            </div>
          )}
          {activeCritical.map((finding) => (
            <div
              key={finding.id}
              className="card card-hover rounded-xl border-l-4 border-l-red-500 p-5 animate-fade-in-up"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
                    <span className="text-sm font-semibold text-gray-900">{finding.patient}</span>
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${severityBadge(finding.severity)}`}>
                      {finding.severity}
                    </span>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${commStatusBadge(finding.commStatus)}`}>
                      {finding.commStatus}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">{finding.description}</p>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                    <span>Study: <span className="font-mono text-gray-400">{finding.studyId}</span></span>
                    <span>Detected: <span className="font-medium text-gray-600">{finding.timeDetected}</span></span>
                    <span className="flex items-center gap-1">
                      AI Confidence:
                      <span className={`font-semibold ${confidenceTextColor(finding.aiConfidence)}`}>
                        {(finding.aiConfidence * 100).toFixed(0)}%
                      </span>
                    </span>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  {finding.commStatus !== "acknowledged" && (
                    <>
                      <button
                        onClick={() => handleEscalate(finding.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-100"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" /></svg>
                        Escalate
                      </button>
                      <button
                        onClick={() => handleAcknowledge(finding.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-green-300 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 transition-colors hover:bg-green-100"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                        Acknowledge
                      </button>
                    </>
                  )}
                  {finding.commStatus === "acknowledged" && (
                    <span className="inline-flex items-center gap-1 text-xs text-green-600 font-medium">
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      Acknowledged
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Action Log */}
          {criticalActionLog.length > 0 && (
            <div className="card rounded-xl p-5">
              <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Action Log</h4>
              <div className="space-y-1">
                {criticalActionLog.map((entry, i) => (
                  <p key={i} className="text-xs text-gray-500 font-mono">{entry}</p>
                ))}
              </div>
            </div>
          )}

          {/* Resolved Critical Findings */}
          {resolvedCritical.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide pt-2">
                Resolved Critical Findings ({resolvedCritical.length})
              </h3>
              {resolvedCritical.map((finding) => (
                <div
                  key={finding.id}
                  className="card rounded-xl p-5 opacity-70 animate-fade-in-up"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <span className="text-sm font-medium text-gray-700">{finding.patient}</span>
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-medium text-green-700">
                          Resolved
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">{finding.description}</p>
                      <div className="flex flex-wrap gap-4 text-xs text-gray-400">
                        <span>Study: <span className="font-mono">{finding.studyId}</span></span>
                        <span>Detected: {finding.timeDetected}</span>
                        <span>AI Confidence: {(finding.aiConfidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
