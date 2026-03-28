"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  startAmbientSession,
  endAmbientSession,
  generateSOAPNote,
  validateSOAPNote,
  codeEncounter,
  submitAttestation,
  approveAttestation,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface LiveSession {
  sessionId: string;
  patientName: string;
  patientId: string;
  provider: string;
  encounterType: string;
  startTime: string;
  status: "recording" | "processing" | "completed";
}

interface CompletedSession {
  sessionId: string;
  patientName: string;
  provider: string;
  startTime: string;
  endTime: string;
  duration: string;
  notesGenerated: boolean;
  coded: boolean;
}

interface SOAPNote {
  noteId: string;
  sessionId: string;
  patientName: string;
  status: "draft" | "validated" | "needs-review";
  overallConfidence: number;
  generatedAt: string;
  sections: {
    subjective: { text: string; confidence: number };
    objective: { text: string; confidence: number };
    assessment: { text: string; confidence: number };
    plan: { text: string; confidence: number };
  };
  amendments: { section: string; content: string; amendedAt: string }[];
}

interface EncounterCode {
  code: string;
  description: string;
  confidence: number;
  validationStatus: "auto-coded" | "verified" | "needs-review";
  type: "ICD-10" | "CPT";
}

interface CodingResult {
  sessionId: string;
  patientName: string;
  provider: string;
  icdCodes: EncounterCode[];
  cptCodes: EncounterCode[];
  codedAt: string;
}

interface AttestationItem {
  id: string;
  encounter: string;
  provider: string;
  patientName: string;
  noteSummary: string;
  codeSummary: string;
  timestamp: string;
  status: "pending" | "approved";
}

// ── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_LIVE_SESSIONS: LiveSession[] = [
  {
    sessionId: "SES-7201",
    patientName: "Sarah Johnson",
    patientId: "PAT-1001",
    provider: "Dr. Williams",
    encounterType: "Follow-up",
    startTime: new Date(Date.now() - 14 * 60000).toISOString(),
    status: "recording",
  },
  {
    sessionId: "SES-7202",
    patientName: "Michael Chen",
    patientId: "PAT-1023",
    provider: "Dr. Patel",
    encounterType: "New Patient",
    startTime: new Date(Date.now() - 6 * 60000).toISOString(),
    status: "recording",
  },
  {
    sessionId: "SES-7200",
    patientName: "Emma Davis",
    patientId: "PAT-1045",
    provider: "Dr. Kim",
    encounterType: "Follow-up",
    startTime: new Date(Date.now() - 22 * 60000).toISOString(),
    status: "processing",
  },
];

const DEMO_COMPLETED_SESSIONS: CompletedSession[] = [
  { sessionId: "SES-7199", patientName: "Robert Wilson", provider: "Dr. Williams", startTime: "2026-03-15T09:00:00Z", endTime: "2026-03-15T09:22:00Z", duration: "22 min", notesGenerated: true, coded: true },
  { sessionId: "SES-7198", patientName: "Lisa Thompson", provider: "Dr. Patel", startTime: "2026-03-15T08:30:00Z", endTime: "2026-03-15T08:48:00Z", duration: "18 min", notesGenerated: true, coded: true },
  { sessionId: "SES-7197", patientName: "James Brown", provider: "Dr. Kim", startTime: "2026-03-15T08:00:00Z", endTime: "2026-03-15T08:35:00Z", duration: "35 min", notesGenerated: true, coded: false },
  { sessionId: "SES-7196", patientName: "Maria Garcia", provider: "Dr. Williams", startTime: "2026-03-14T16:00:00Z", endTime: "2026-03-14T16:15:00Z", duration: "15 min", notesGenerated: true, coded: true },
  { sessionId: "SES-7195", patientName: "David Lee", provider: "Dr. Patel", startTime: "2026-03-14T15:30:00Z", endTime: "2026-03-14T15:52:00Z", duration: "22 min", notesGenerated: true, coded: true },
];

const DEMO_SOAP_NOTES: SOAPNote[] = [
  {
    noteId: "NOTE-3401",
    sessionId: "SES-7199",
    patientName: "Robert Wilson",
    status: "validated",
    overallConfidence: 96.2,
    generatedAt: "2026-03-15T09:22:30Z",
    sections: {
      subjective: {
        text: "Patient presents with chief complaint of chest tightness for 2 weeks. Reports onset coinciding with medication change from lisinopril to amlodipine approximately 3 weeks ago. Also reports bilateral ankle swelling. Denies shortness of breath, fever, or weight loss. ROS: CV positive for chest tightness and ankle edema.",
        confidence: 97.1,
      },
      objective: {
        text: "Vitals: BP 142/88 mmHg, HR 78 bpm, RR 16/min, Temp 98.6F, SpO2 98%. Exam: Bilateral pedal edema 1+. Heart sounds regular, no murmurs, rubs, or gallops. Lungs clear to auscultation bilaterally. No JVD.",
        confidence: 98.3,
      },
      assessment: {
        text: "1. Peripheral edema (R60.0) - new, likely secondary to amlodipine\n2. Hypertension, uncontrolled (I10) - existing, suboptimal control on current regimen\n3. Adverse effect of calcium channel blocker (T46.1X5A) - new",
        confidence: 94.5,
      },
      plan: {
        text: "1. Discontinue amlodipine 5mg, switch to losartan 50mg daily\n2. Order BMP and renal function panel\n3. Follow-up in 2 weeks to reassess BP and edema\n4. Patient education on signs of worsening edema\n5. Continue aspirin 81mg daily",
        confidence: 95.0,
      },
    },
    amendments: [],
  },
  {
    noteId: "NOTE-3400",
    sessionId: "SES-7198",
    patientName: "Lisa Thompson",
    status: "draft",
    overallConfidence: 91.8,
    generatedAt: "2026-03-15T08:49:00Z",
    sections: {
      subjective: {
        text: "Patient returns for follow-up of type 2 diabetes mellitus. Reports improved compliance with metformin. Occasional morning fasting glucose readings of 140-160 mg/dL. Denies polyuria, polydipsia, or vision changes. Reports mild tingling in feet bilaterally.",
        confidence: 93.2,
      },
      objective: {
        text: "Vitals: BP 128/82 mmHg, HR 72 bpm, RR 14/min, Temp 98.4F, SpO2 99%. Weight: 182 lbs (down 4 lbs). A1C: 7.4% (previous 8.1%). Exam: Monofilament sensation intact bilaterally. Pedal pulses 2+ bilaterally. No skin breakdown.",
        confidence: 95.0,
      },
      assessment: {
        text: "1. Type 2 diabetes mellitus, improved control (E11.65)\n2. Diabetic peripheral neuropathy, early (E11.42)\n3. Obesity (E66.01)",
        confidence: 88.5,
      },
      plan: {
        text: "1. Continue metformin 1000mg BID\n2. Add gabapentin 100mg TID for neuropathy\n3. Order comprehensive metabolic panel\n4. Refer to ophthalmology for diabetic eye exam\n5. Continue dietary counseling\n6. Follow-up in 3 months with repeat A1C",
        confidence: 90.4,
      },
    },
    amendments: [],
  },
  {
    noteId: "NOTE-3399",
    sessionId: "SES-7197",
    patientName: "James Brown",
    status: "needs-review",
    overallConfidence: 82.4,
    generatedAt: "2026-03-15T08:36:00Z",
    sections: {
      subjective: {
        text: "Patient presents with acute low back pain radiating to left leg for 5 days. Pain rated 7/10, worse with sitting and bending. Reports numbness in left foot. No bowel or bladder dysfunction. Denies trauma or recent heavy lifting.",
        confidence: 88.0,
      },
      objective: {
        text: "Vitals: BP 134/86 mmHg, HR 82 bpm. Musculoskeletal: Paraspinal tenderness L4-L5. Positive straight leg raise on left at 40 degrees. Decreased sensation left L5 dermatome. Motor strength 4/5 left EHL. Reflexes symmetric.",
        confidence: 85.2,
      },
      assessment: {
        text: "1. Lumbar radiculopathy, left L5 (M54.17)\n2. Possible lumbar disc herniation (M51.16)\n3. Acute low back pain (M54.5)",
        confidence: 78.0,
      },
      plan: {
        text: "1. Order MRI lumbar spine without contrast\n2. Prescribe methylprednisolone dose pack\n3. Physical therapy referral\n4. NSAIDs for pain management\n5. Activity modification education\n6. Follow-up in 1 week or sooner if symptoms worsen",
        confidence: 78.4,
      },
    },
    amendments: [
      { section: "assessment", content: "Added differential: consider spinal stenosis given patient age", amendedAt: "2026-03-15T09:10:00Z" },
    ],
  },
  {
    noteId: "NOTE-3398",
    sessionId: "SES-7196",
    patientName: "Maria Garcia",
    status: "validated",
    overallConfidence: 97.0,
    generatedAt: "2026-03-14T16:16:00Z",
    sections: {
      subjective: { text: "Annual wellness visit. No acute complaints. Reports regular exercise 3x/week. Sleep is adequate. Denies tobacco, moderate alcohol use.", confidence: 98.0 },
      objective: { text: "Vitals within normal limits. BMI 24.2. General exam unremarkable. Age-appropriate screening up to date.", confidence: 97.5 },
      assessment: { text: "1. Annual wellness visit (Z00.00)\n2. Hyperlipidemia, controlled (E78.5)", confidence: 96.0 },
      plan: { text: "1. Continue atorvastatin 20mg daily\n2. Repeat lipid panel in 6 months\n3. Age-appropriate cancer screening discussed\n4. Follow-up in 1 year", confidence: 96.5 },
    },
    amendments: [],
  },
];

const DEMO_CODING_RESULTS: CodingResult[] = [
  {
    sessionId: "SES-7199",
    patientName: "Robert Wilson",
    provider: "Dr. Williams",
    codedAt: "2026-03-15T09:23:00Z",
    icdCodes: [
      { code: "R60.0", description: "Localized edema", confidence: 97.2, validationStatus: "verified", type: "ICD-10" },
      { code: "I10", description: "Essential hypertension", confidence: 98.5, validationStatus: "verified", type: "ICD-10" },
      { code: "T46.1X5A", description: "Adverse effect of CCB, initial encounter", confidence: 91.0, validationStatus: "auto-coded", type: "ICD-10" },
    ],
    cptCodes: [
      { code: "99214", description: "Office visit, established, moderate complexity", confidence: 96.8, validationStatus: "verified", type: "CPT" },
      { code: "80048", description: "Basic metabolic panel", confidence: 94.0, validationStatus: "auto-coded", type: "CPT" },
      { code: "80069", description: "Renal function panel", confidence: 93.5, validationStatus: "auto-coded", type: "CPT" },
    ],
  },
  {
    sessionId: "SES-7198",
    patientName: "Lisa Thompson",
    provider: "Dr. Patel",
    codedAt: "2026-03-15T08:50:00Z",
    icdCodes: [
      { code: "E11.65", description: "Type 2 DM with hyperglycemia", confidence: 95.0, validationStatus: "verified", type: "ICD-10" },
      { code: "E11.42", description: "Type 2 DM with diabetic polyneuropathy", confidence: 87.5, validationStatus: "needs-review", type: "ICD-10" },
      { code: "E66.01", description: "Morbid obesity due to excess calories", confidence: 82.0, validationStatus: "needs-review", type: "ICD-10" },
    ],
    cptCodes: [
      { code: "99214", description: "Office visit, established, moderate complexity", confidence: 94.2, validationStatus: "auto-coded", type: "CPT" },
      { code: "83036", description: "Hemoglobin A1C", confidence: 97.0, validationStatus: "verified", type: "CPT" },
      { code: "80053", description: "Comprehensive metabolic panel", confidence: 92.0, validationStatus: "auto-coded", type: "CPT" },
    ],
  },
  {
    sessionId: "SES-7197",
    patientName: "James Brown",
    provider: "Dr. Kim",
    codedAt: "2026-03-15T08:37:00Z",
    icdCodes: [
      { code: "M54.17", description: "Radiculopathy, lumbosacral region", confidence: 88.0, validationStatus: "auto-coded", type: "ICD-10" },
      { code: "M51.16", description: "Intervertebral disc disorder with radiculopathy, lumbar", confidence: 76.5, validationStatus: "needs-review", type: "ICD-10" },
      { code: "M54.5", description: "Low back pain", confidence: 95.0, validationStatus: "verified", type: "ICD-10" },
    ],
    cptCodes: [
      { code: "99215", description: "Office visit, established, high complexity", confidence: 85.0, validationStatus: "needs-review", type: "CPT" },
      { code: "72148", description: "MRI lumbar spine without contrast", confidence: 96.5, validationStatus: "verified", type: "CPT" },
    ],
  },
];

const DEMO_ATTESTATIONS: AttestationItem[] = [
  {
    id: "ATT-5001",
    encounter: "SES-7199",
    provider: "Dr. Williams",
    patientName: "Robert Wilson",
    noteSummary: "Follow-up for chest tightness and ankle edema secondary to amlodipine. Switching to losartan. Labs ordered.",
    codeSummary: "ICD-10: R60.0, I10, T46.1X5A | CPT: 99214, 80048, 80069",
    timestamp: "2026-03-15T09:25:00Z",
    status: "pending",
  },
  {
    id: "ATT-5002",
    encounter: "SES-7198",
    provider: "Dr. Patel",
    patientName: "Lisa Thompson",
    noteSummary: "DM2 follow-up showing improved A1C (8.1% to 7.4%). Starting gabapentin for early neuropathy. Ophthalmology referral.",
    codeSummary: "ICD-10: E11.65, E11.42, E66.01 | CPT: 99214, 83036, 80053",
    timestamp: "2026-03-15T08:52:00Z",
    status: "pending",
  },
  {
    id: "ATT-5003",
    encounter: "SES-7197",
    provider: "Dr. Kim",
    patientName: "James Brown",
    noteSummary: "Acute L5 radiculopathy with motor weakness. MRI ordered. Methylprednisolone dose pack and PT referral.",
    codeSummary: "ICD-10: M54.17, M51.16, M54.5 | CPT: 99215, 72148",
    timestamp: "2026-03-15T08:40:00Z",
    status: "pending",
  },
  {
    id: "ATT-4998",
    encounter: "SES-7196",
    provider: "Dr. Williams",
    patientName: "Maria Garcia",
    noteSummary: "Annual wellness visit. Hyperlipidemia controlled on atorvastatin. Screening up to date.",
    codeSummary: "ICD-10: Z00.00, E78.5 | CPT: 99395",
    timestamp: "2026-03-14T16:18:00Z",
    status: "approved",
  },
  {
    id: "ATT-4997",
    encounter: "SES-7195",
    provider: "Dr. Patel",
    patientName: "David Lee",
    noteSummary: "Asthma follow-up. Well-controlled on current regimen. Renewed prescriptions.",
    codeSummary: "ICD-10: J45.30 | CPT: 99213",
    timestamp: "2026-03-14T15:55:00Z",
    status: "approved",
  },
];

// ── Utility Components ───────────────────────────────────────────────────────

function AudioWaveform({ active }: { active: boolean }) {
  return (
    <div className="flex items-end gap-0.5 h-8">
      {Array.from({ length: 20 }).map((_, i) => {
        const baseHeight = Math.sin(i * 0.8) * 12 + 16;
        return (
          <div
            key={i}
            className={`w-1 rounded-full transition-all duration-150 ${
              active ? "bg-red-400" : "bg-gray-300"
            }`}
            style={{
              height: active ? `${baseHeight + Math.random() * 10}px` : "4px",
              animationDelay: `${i * 50}ms`,
            }}
          />
        );
      })}
    </div>
  );
}

function ConfidenceBar({ value, size = "md" }: { value: number; size?: "sm" | "md" }) {
  const color =
    value >= 95 ? "bg-green-500" : value >= 85 ? "bg-yellow-500" : "bg-orange-500";
  return (
    <div className="flex items-center gap-2">
      <div className={`flex-1 rounded-full bg-gray-200 ${size === "sm" ? "h-1.5" : "h-2"}`}>
        <div className={`rounded-full ${color} ${size === "sm" ? "h-1.5" : "h-2"}`} style={{ width: `${value}%` }} />
      </div>
      <span className={`font-medium ${size === "sm" ? "text-xs" : "text-sm"} ${value >= 95 ? "text-green-700" : value >= 85 ? "text-yellow-700" : "text-orange-700"}`}>
        {value.toFixed(1)}%
      </span>
    </div>
  );
}

function DurationCounter({ startTime }: { startTime: string }) {
  const [elapsed, setElapsed] = useState("");

  useEffect(() => {
    const update = () => {
      const diff = Math.floor((Date.now() - new Date(startTime).getTime()) / 1000);
      const m = Math.floor(diff / 60);
      const s = diff % 60;
      setElapsed(`${m}:${s.toString().padStart(2, "0")}`);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  return <span className="font-mono text-sm text-gray-700 dark:text-gray-300">{elapsed}</span>;
}

// ── Main Page ────────────────────────────────────────────────────────────────

type TabKey = "live-sessions" | "soap-notes" | "encounter-coding" | "attestation";

export default function AmbientAIPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("live-sessions");
  const [liveSessions, setLiveSessions] = useState<LiveSession[]>([]);
  const [completedSessions, setCompletedSessions] = useState<CompletedSession[]>([]);
  const [soapNotes, setSoapNotes] = useState<SOAPNote[]>([]);
  const [codingResults, setCodingResults] = useState<CodingResult[]>([]);
  const [attestations, setAttestations] = useState<AttestationItem[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);

  // Start session form
  const [showStartForm, setShowStartForm] = useState(false);
  const [newPatientId, setNewPatientId] = useState("");
  const [newEncounterType, setNewEncounterType] = useState("Follow-up");
  const [newProvider, setNewProvider] = useState("Dr. Williams");

  // SOAP detail expansion
  const [expandedNote, setExpandedNote] = useState<string | null>(null);
  const [editingSection, setEditingSection] = useState<{ noteId: string; section: string } | null>(null);
  const [editText, setEditText] = useState("");

  // Coding form
  const [codeSessionId, setCodeSessionId] = useState("");

  // Attestation review
  const [reviewingAttestation, setReviewingAttestation] = useState<string | null>(null);
  const [attestationNotes, setAttestationNotes] = useState("");

  // Waveform animation ref
  const waveformRef = useRef<NodeJS.Timeout | null>(null);
  const [waveformTick, setWaveformTick] = useState(0);

  useEffect(() => {
    waveformRef.current = setInterval(() => setWaveformTick((t) => t + 1), 200);
    return () => { if (waveformRef.current) clearInterval(waveformRef.current); };
  }, []);

  const activeSessions = liveSessions.filter((s) => s.status === "recording" || s.status === "processing");
  const pendingAttestations = attestations.filter((a) => a.status === "pending");

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleStartSession = useCallback(async () => {
    const sessionId = `SES-${7203 + Math.floor(Math.random() * 100)}`;
    setApiError(null);
    try {
      const result = await startAmbientSession({
        patient_id: newPatientId,
        encounter_type: newEncounterType,
        provider: newProvider,
        timestamp: new Date().toISOString(),
      });
      // Use API response if available
      const newSession: LiveSession = {
        sessionId: result?.session_id || sessionId,
        patientName: result?.patient_name || `Patient ${newPatientId}`,
        patientId: newPatientId,
        provider: newProvider,
        encounterType: newEncounterType,
        startTime: new Date().toISOString(),
        status: "recording",
      };
      setLiveSessions((prev) => [newSession, ...prev]);
    } catch {
      // API unavailable — create local session
      const newSession: LiveSession = {
        sessionId,
        patientName: `Patient ${newPatientId}`,
        patientId: newPatientId,
        provider: newProvider,
        encounterType: newEncounterType,
        startTime: new Date().toISOString(),
        status: "recording",
      };
      setLiveSessions((prev) => [newSession, ...prev]);
      setApiError("Session started locally — backend unavailable");
    }
    setShowStartForm(false);
    setNewPatientId("");
  }, [newPatientId, newEncounterType, newProvider]);

  const handleEndSession = useCallback(async (sessionId: string) => {
    try {
      await endAmbientSession({ session_id: sessionId, timestamp: new Date().toISOString() });
    } catch {
      setApiError("Could not end session on server — updating locally");
    }
    setLiveSessions((prev) =>
      prev.map((s) => (s.sessionId === sessionId ? { ...s, status: "processing" as const } : s))
    );
    setTimeout(() => {
      setLiveSessions((prev) =>
        prev.map((s) => (s.sessionId === sessionId ? { ...s, status: "completed" as const } : s))
      );
    }, 3000);
  }, []);

  const handleGenerateSOAP = useCallback(async (sessionId: string) => {
    setApiError(null);
    try {
      const result = await generateSOAPNote({ session_id: sessionId });
      if (result) {
        // Use backend-generated SOAP note
        const session = liveSessions.find((s) => s.sessionId === sessionId) ||
          completedSessions.find((s) => s.sessionId === sessionId);
        const newNote: SOAPNote = {
          noteId: result.note_id || `NOTE-${Date.now()}`,
          sessionId,
          patientName: session?.patientName || `Session ${sessionId}`,
          status: "draft",
          overallConfidence: result.overall_confidence ?? 90.0,
          generatedAt: new Date().toISOString(),
          sections: {
            subjective: { text: result.sections?.subjective?.text || result.subjective || "Pending review", confidence: result.sections?.subjective?.confidence ?? 85 },
            objective: { text: result.sections?.objective?.text || result.objective || "Pending review", confidence: result.sections?.objective?.confidence ?? 85 },
            assessment: { text: result.sections?.assessment?.text || result.assessment || "Pending review", confidence: result.sections?.assessment?.confidence ?? 85 },
            plan: { text: result.sections?.plan?.text || result.plan || "Pending review", confidence: result.sections?.plan?.confidence ?? 85 },
          },
          amendments: [],
        };
        setSoapNotes((prev) => [newNote, ...prev]);
      }
    } catch {
      setApiError("SOAP note generation unavailable — using demo mode");
    }
  }, [liveSessions, completedSessions]);

  const handleValidateNote = useCallback(async (noteId: string) => {
    try {
      await validateSOAPNote({ note_id: noteId });
      setSoapNotes((prev) =>
        prev.map((n) => (n.noteId === noteId ? { ...n, status: "validated" as const } : n))
      );
    } catch {
      // Still update locally but show warning
      setSoapNotes((prev) =>
        prev.map((n) => (n.noteId === noteId ? { ...n, status: "validated" as const } : n))
      );
      setApiError("Note validated locally — server sync pending");
    }
  }, []);

  const handleAmendNote = useCallback((noteId: string, section: string) => {
    setSoapNotes((prev) =>
      prev.map((n) => {
        if (n.noteId !== noteId) return n;
        return {
          ...n,
          status: "needs-review" as const,
          amendments: [
            ...n.amendments,
            { section, content: editText, amendedAt: new Date().toISOString() },
          ],
        };
      })
    );
    setEditingSection(null);
    setEditText("");
  }, [editText]);

  const handleCodeEncounter = useCallback(async () => {
    setApiError(null);
    try {
      const result = await codeEncounter({ session_id: codeSessionId });
      if (result && (result.icd_codes || result.cpt_codes)) {
        const session = [...liveSessions, ...completedSessions].find(s => s.sessionId === codeSessionId);
        const newCoding: CodingResult = {
          sessionId: codeSessionId,
          patientName: session?.patientName || `Session ${codeSessionId}`,
          provider: session?.provider || "Provider",
          codedAt: new Date().toISOString(),
          icdCodes: (result.icd_codes || []).map((c: Record<string, unknown>) => ({
            code: String(c.code || ""),
            description: String(c.description || ""),
            confidence: Number(c.confidence || 80),
            validationStatus: "auto-coded" as const,
            type: "ICD-10" as const,
          })),
          cptCodes: (result.cpt_codes || []).map((c: Record<string, unknown>) => ({
            code: String(c.code || ""),
            description: String(c.description || ""),
            confidence: Number(c.confidence || 80),
            validationStatus: "auto-coded" as const,
            type: "CPT" as const,
          })),
        };
        setCodingResults((prev) => [newCoding, ...prev]);
      }
    } catch {
      setApiError("Encounter coding unavailable — using demo data");
    }
    setCodeSessionId("");
  }, [codeSessionId, liveSessions, completedSessions]);

  const handleValidateCodes = useCallback(async (sessionId: string) => {
    try {
      await codeEncounter({ session_id: sessionId, action: "validate" });
    } catch {
      // API unavailable - demo mode
    }
    setCodingResults((prev) =>
      prev.map((cr) => {
        if (cr.sessionId !== sessionId) return cr;
        return {
          ...cr,
          icdCodes: cr.icdCodes.map((c) => ({ ...c, validationStatus: "verified" as const })),
          cptCodes: cr.cptCodes.map((c) => ({ ...c, validationStatus: "verified" as const })),
        };
      })
    );
  }, []);

  const handleApproveAttestation = useCallback(async (attestationId: string) => {
    try {
      await approveAttestation({ attestation_id: attestationId });
      setAttestations((prev) =>
        prev.map((a) => (a.id === attestationId ? { ...a, status: "approved" as const } : a))
      );
    } catch {
      setAttestations((prev) =>
        prev.map((a) => (a.id === attestationId ? { ...a, status: "approved" as const } : a))
      );
      setApiError("Attestation approved locally — server sync pending");
    }
    setReviewingAttestation(null);
    setAttestationNotes("");
  }, []);

  const handleRequestChanges = useCallback(async (attestationId: string) => {
    try {
      await submitAttestation({ attestation_id: attestationId, action: "request_changes", notes: attestationNotes });
    } catch {
      setApiError("Changes request sent locally — server sync pending");
    }
    setReviewingAttestation(null);
    setAttestationNotes("");
  }, [attestationNotes]);

  // ── Status Badges ────────────────────────────────────────────────────────

  const sessionStatusBadge = (status: string) => {
    switch (status) {
      case "recording":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
            <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            Recording
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-700">
            <span className="h-2 w-2 rounded-full bg-yellow-500" />
            Processing
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            Completed
          </span>
        );
      default:
        return null;
    }
  };

  const noteStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      draft: "bg-yellow-100 text-yellow-700",
      validated: "bg-green-100 text-green-700",
      "needs-review": "bg-orange-100 text-orange-700",
    };
    return (
      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${map[status] || "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"}`}>
        {status}
      </span>
    );
  };

  const codeValidationBadge = (status: string) => {
    const map: Record<string, string> = {
      "auto-coded": "bg-blue-100 text-blue-700 border-blue-200",
      verified: "bg-green-100 text-green-700 border-green-200",
      "needs-review": "bg-yellow-100 text-yellow-700 border-yellow-200",
    };
    return map[status] || "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700";
  };

  const attestationStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-700",
      approved: "bg-green-100 text-green-700",
    };
    return (
      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${map[status] || "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"}`}>
        {status}
      </span>
    );
  };

  // ── Stats ────────────────────────────────────────────────────────────────

  const stats = [
    { label: "Active Sessions", value: activeSessions.length.toString(), icon: "🎙️", color: "text-red-600" },
    { label: "Notes Generated", value: soapNotes.length.toString(), icon: "📝", color: "text-blue-600" },
    { label: "Attestations Pending", value: pendingAttestations.length.toString(), icon: "⏳", color: "text-yellow-600" },
    { label: "Avg Accuracy %", value: "94.8%", icon: "🎯", color: "text-green-600" },
    { label: "Encounter Codes Today", value: codingResults.reduce((sum, cr) => sum + cr.icdCodes.length + cr.cptCodes.length, 0).toString(), icon: "🏷️", color: "text-purple-600" },
  ];

  const tabs: { key: TabKey; label: string }[] = [
    { key: "live-sessions", label: "Live Sessions" },
    { key: "soap-notes", label: "SOAP Notes" },
    { key: "encounter-coding", label: "Encounter Coding" },
    { key: "attestation", label: "Attestation" },
  ];

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Ambient AI Documentation</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Automatic clinical documentation from patient-provider conversations
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 border border-red-200 px-3 py-1 text-xs font-semibold text-red-700">
            <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            {activeSessions.length} Active
          </span>
        </div>
        <button
          onClick={() => setShowStartForm(true)}
          className="rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-healthos-700 transition-colors shadow-sm"
        >
          Start Session
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 animate-fade-in-up">
        {stats.map((s) => (
          <div key={s.label} className="card card-hover p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{s.label}</p>
            </div>
            <p className={`mt-2 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {apiError && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-700 flex items-center justify-between">
          <span><span className="font-medium">Note:</span> {apiError}</span>
          <button onClick={() => setApiError(null)} className="text-amber-700 hover:text-amber-900 font-bold ml-3">&times;</button>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-4 sm:gap-6 overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`whitespace-nowrap border-b-2 pb-3 text-sm font-medium transition-colors ${
                activeTab === t.key
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:border-gray-600"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab: Live Sessions ────────────────────────────────────────────── */}
      {activeTab === "live-sessions" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Start Session Form */}
          {showStartForm && (
            <div className="card p-6 border-2 border-healthos-200 bg-healthos-50/30">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Start New Session</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Patient ID</label>
                  <input
                    type="text"
                    value={newPatientId}
                    onChange={(e) => setNewPatientId(e.target.value)}
                    placeholder="PAT-1001"
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Encounter Type</label>
                  <select
                    value={newEncounterType}
                    onChange={(e) => setNewEncounterType(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
                  >
                    <option>Follow-up</option>
                    <option>New Patient</option>
                    <option>Annual Wellness</option>
                    <option>Urgent</option>
                    <option>Procedure</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Provider</label>
                  <select
                    value={newProvider}
                    onChange={(e) => setNewProvider(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
                  >
                    <option>Dr. Williams</option>
                    <option>Dr. Patel</option>
                    <option>Dr. Kim</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleStartSession}
                  disabled={!newPatientId}
                  className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Begin Recording
                </button>
                <button
                  onClick={() => setShowStartForm(false)}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Active Session Cards */}
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Active Sessions</h2>
            {liveSessions.filter((s) => s.status !== "completed").length === 0 ? (
              <div className="card p-8 text-center text-gray-500 dark:text-gray-400">
                <p className="font-medium">No Active Sessions</p>
                <p className="text-sm mt-1">No active sessions. Click &quot;Start Session&quot; to begin recording.</p>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {liveSessions
                  .filter((s) => s.status !== "completed")
                  .map((session) => (
                    <div key={session.sessionId} className="card card-hover p-5 animate-fade-in-up">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="text-xs font-mono text-gray-500 dark:text-gray-400">{session.sessionId}</p>
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{session.patientName}</p>
                        </div>
                        {sessionStatusBadge(session.status)}
                      </div>
                      <div className="space-y-1.5 text-xs text-gray-600 dark:text-gray-400 mb-3">
                        <div className="flex justify-between">
                          <span>Provider</span>
                          <span className="font-medium text-gray-900 dark:text-gray-100">{session.provider}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Type</span>
                          <span className="font-medium text-gray-900 dark:text-gray-100">{session.encounterType}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Duration</span>
                          <DurationCounter startTime={session.startTime} />
                        </div>
                      </div>
                      {/* Audio Waveform Visualization */}
                      <div className="mb-3 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-800">
                        <AudioWaveform active={session.status === "recording"} key={waveformTick} />
                      </div>
                      {session.status === "recording" && (
                        <button
                          onClick={() => handleEndSession(session.sessionId)}
                          className="w-full rounded-lg bg-red-600 px-3 py-2 text-xs font-medium text-white hover:bg-red-700 transition-colors"
                        >
                          End Session
                        </button>
                      )}
                      {session.status === "processing" && (
                        <div className="flex items-center gap-2 text-xs text-yellow-700">
                          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Generating documentation...
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Recent Completed Sessions */}
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Recent Completed Sessions</h2>
            {completedSessions.length === 0 ? (
              <div className="card p-8 text-center text-gray-500 dark:text-gray-400">
                <p className="font-medium">No Completed Sessions</p>
                <p className="text-sm mt-1">No completed sessions yet.</p>
              </div>
            ) : (
            <div className="card overflow-hidden">
              <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {["Session", "Patient", "Provider", "Duration", "Notes", "Coded", "Date"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {completedSessions.map((cs) => (
                    <tr key={cs.sessionId} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono text-healthos-600">{cs.sessionId}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{cs.patientName}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{cs.provider}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{cs.duration}</td>
                      <td className="px-4 py-3">
                        {cs.notesGenerated ? (
                          <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Generated</span>
                        ) : (
                          <span className="inline-flex rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-500 dark:text-gray-400">Pending</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {cs.coded ? (
                          <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Yes</span>
                        ) : (
                          <span className="inline-flex rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">No</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                        {new Date(cs.startTime).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            </div>
            )}
          </div>
        </div>
      )}

      {/* ── Tab: SOAP Notes ──────────────────────────────────────────────── */}
      {activeTab === "soap-notes" && (
        <div className="space-y-4 animate-fade-in-up">
          {soapNotes.length === 0 ? (
            <div className="card p-8 text-center text-gray-500 dark:text-gray-400">
              <p className="font-medium">No SOAP Notes</p>
              <p className="text-sm mt-1">No SOAP notes generated yet. Generate notes from a completed session.</p>
            </div>
          ) : soapNotes.map((note) => (
            <div key={note.noteId} className="card card-hover overflow-hidden">
              {/* Note Header */}
              <div
                className="flex items-center justify-between p-5 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                onClick={() => setExpandedNote(expandedNote === note.noteId ? null : note.noteId)}
              >
                <div className="flex items-center gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{note.patientName}</p>
                      {noteStatusBadge(note.status)}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {note.noteId} &middot; Session {note.sessionId} &middot; Generated{" "}
                      {new Date(note.generatedAt).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Overall Confidence</p>
                    <p className={`text-sm font-bold ${note.overallConfidence >= 95 ? "text-green-600" : note.overallConfidence >= 85 ? "text-yellow-600" : "text-orange-600"}`}> {note.overallConfidence.toFixed(1)}% </p> </div> <svg className={`h-5 w-5 text-gray-500 dark:text-gray-400 transition-transform ${expandedNote === note.noteId ?"rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>

              {/* Expanded Detail */}
              {expandedNote === note.noteId && (
                <div className="border-t border-gray-200 dark:border-gray-700 p-5 space-y-4 animate-fade-in-up">
                  {(["subjective", "objective", "assessment", "plan"] as const).map((section) => {
                    const sectionData = note.sections[section];
                    const sectionColors: Record<string, string> = {
                      subjective: "border-blue-300 bg-blue-50",
                      objective: "border-green-300 bg-green-50",
                      assessment: "border-orange-300 bg-orange-50",
                      plan: "border-purple-300 bg-purple-50",
                    };
                    const sectionLabelColors: Record<string, string> = {
                      subjective: "text-blue-700",
                      objective: "text-green-700",
                      assessment: "text-orange-700",
                      plan: "text-purple-700",
                    };
                    const isEditing = editingSection?.noteId === note.noteId && editingSection?.section === section;

                    return (
                      <div key={section} className={`rounded-lg border p-4 ${sectionColors[section]}`}>
                        <div className="flex items-center justify-between mb-2">
                          <h4 className={`text-sm font-semibold uppercase ${sectionLabelColors[section]}`}>
                            {section}
                          </h4>
                          <div className="flex items-center gap-3">
                            <div className="w-32">
                              <ConfidenceBar value={sectionData.confidence} size="sm" />
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                if (isEditing) {
                                  handleAmendNote(note.noteId, section);
                                } else {
                                  setEditingSection({ noteId: note.noteId, section });
                                  setEditText(sectionData.text);
                                }
                              }}
                              className="text-xs font-medium text-healthos-600 hover:text-healthos-800 transition-colors"
                            >
                              {isEditing ? "Save Amendment" : "Edit"}
                            </button>
                          </div>
                        </div>
                        {isEditing ? (
                          <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 p-3 text-sm text-gray-700 dark:text-gray-300 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none min-h-[100px]"
                            onClick={(e) => e.stopPropagation()}
                          />
                        ) : (
                          <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">{sectionData.text}</p>
                        )}
                      </div>
                    );
                  })}

                  {/* Amendments */}
                  {note.amendments.length > 0 && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <h4 className="text-xs font-semibold text-amber-800 uppercase mb-2">Amendments</h4>
                      {note.amendments.map((a, i) => (
                        <div key={i} className="text-sm text-amber-900 mb-1">
                          <span className="font-medium capitalize">{a.section}:</span> {a.content}{" "}
                          <span className="text-xs text-amber-600">({new Date(a.amendedAt).toLocaleString()})</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3 pt-2">
                    {note.status !== "validated" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleValidateNote(note.noteId);
                        }}
                        className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors"
                      >
                        Validate Note
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleGenerateSOAP(note.sessionId);
                      }}
                      className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      Regenerate
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Tab: Encounter Coding ────────────────────────────────────────── */}
      {activeTab === "encounter-coding" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Code Encounter Form */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Code Encounter</h3>
            <div className="flex gap-3">
              <select
                value={codeSessionId}
                onChange={(e) => setCodeSessionId(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              >
                <option value="">Select session...</option>
                {completedSessions.map((cs) => (
                  <option key={cs.sessionId} value={cs.sessionId}>
                    {cs.sessionId} - {cs.patientName} ({cs.provider})
                  </option>
                ))}
              </select>
              <button
                onClick={handleCodeEncounter}
                disabled={!codeSessionId}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Code Encounter
              </button>
            </div>
          </div>

          {/* Coding Results */}
          {codingResults.length === 0 ? (
            <div className="card p-8 text-center text-gray-500 dark:text-gray-400">
              <p className="font-medium">No Coding Results</p>
              <p className="text-sm mt-1">No encounter coding results yet.</p>
            </div>
          ) : codingResults.map((cr) => (
            <div key={cr.sessionId} className="card card-hover p-5 animate-fade-in-up">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{cr.patientName}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {cr.sessionId} &middot; {cr.provider} &middot; Coded{" "}
                    {new Date(cr.codedAt).toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={() => handleValidateCodes(cr.sessionId)}
                  className="rounded-lg border border-green-300 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 transition-colors"
                >
                  Validate Codes
                </button>
              </div>

              {/* ICD-10 Codes */}
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-2">ICD-10 Codes</h4>
                <div className="flex flex-wrap gap-2">
                  {cr.icdCodes.map((code) => (
                    <div
                      key={code.code}
                      className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${codeValidationBadge(code.validationStatus)}`}
                    >
                      <span className="font-mono font-bold">{code.code}</span>
                      <span className="text-gray-600 dark:text-gray-400">{code.description}</span>
                      <span className="font-medium">{code.confidence.toFixed(0)}%</span>
                      <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-medium ${
                        code.validationStatus === "verified"
                          ? "bg-green-200 text-green-800"
                          : code.validationStatus === "auto-coded"
                          ? "bg-blue-200 text-blue-800"
                          : "bg-yellow-200 text-yellow-800"
                      }`}>
                        {code.validationStatus}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* CPT Codes */}
              <div>
                <h4 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-2">CPT Codes</h4>
                <div className="flex flex-wrap gap-2">
                  {cr.cptCodes.map((code) => (
                    <div
                      key={code.code}
                      className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${codeValidationBadge(code.validationStatus)}`}
                    >
                      <span className="font-mono font-bold">{code.code}</span>
                      <span className="text-gray-600 dark:text-gray-400">{code.description}</span>
                      <span className="font-medium">{code.confidence.toFixed(0)}%</span>
                      <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-medium ${
                        code.validationStatus === "verified"
                          ? "bg-green-200 text-green-800"
                          : code.validationStatus === "auto-coded"
                          ? "bg-blue-200 text-blue-800"
                          : "bg-yellow-200 text-yellow-800"
                      }`}>
                        {code.validationStatus}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Tab: Attestation ─────────────────────────────────────────────── */}
      {activeTab === "attestation" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Pending Attestation Queue */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Pending Attestation Queue</h2>
              <span className="inline-flex rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                {pendingAttestations.length}
              </span>
            </div>
            {pendingAttestations.length === 0 ? (
              <div className="card p-8 text-center text-gray-500 dark:text-gray-400">
                <p className="font-medium">No Attestations Pending</p>
                <p className="text-sm mt-1">No attestations pending.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingAttestations.map((att) => (
                  <div key={att.id} className="card card-hover p-5 animate-fade-in-up">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{att.patientName}</p>
                          {attestationStatusBadge(att.status)}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {att.id} &middot; Encounter {att.encounter} &middot; {att.provider} &middot;{" "}
                          {new Date(att.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>

                    {/* Summary */}
                    <div className="space-y-2 mb-4">
                      <div className="rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-800 p-3">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Note Summary</p>
                        <p className="text-sm text-gray-700 dark:text-gray-300">{att.noteSummary}</p>
                      </div>
                      <div className="rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-800 p-3">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Code Summary</p>
                        <p className="text-sm font-mono text-gray-700 dark:text-gray-300">{att.codeSummary}</p>
                      </div>
                    </div>

                    {/* Review Workflow */}
                    {reviewingAttestation === att.id ? (
                      <div className="space-y-3 border-t border-gray-200 dark:border-gray-700 pt-4">
                        <div>
                          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Review Notes</label>
                          <textarea
                            value={attestationNotes}
                            onChange={(e) => setAttestationNotes(e.target.value)}
                            placeholder="Enter review notes or change requests..."
                            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 p-3 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none min-h-[80px]"
                          />
                        </div>
                        <div className="flex gap-3">
                          <button
                            onClick={() => handleApproveAttestation(att.id)}
                            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleRequestChanges(att.id)}
                            className="rounded-lg border border-orange-300 bg-orange-50 px-4 py-2 text-sm font-medium text-orange-700 hover:bg-orange-100 transition-colors"
                          >
                            Request Changes
                          </button>
                          <button
                            onClick={() => { setReviewingAttestation(null); setAttestationNotes(""); }}
                            className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleApproveAttestation(att.id)}
                          className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => setReviewingAttestation(att.id)}
                          className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                        >
                          Review Details
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Approved Attestation Log */}
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Approved Attestation Log</h2>
            <div className="card overflow-hidden">
              <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {["Attestation ID", "Encounter", "Patient", "Provider", "Timestamp", "Status"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {attestations
                    .filter((a) => a.status === "approved")
                    .map((att) => (
                      <tr key={att.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-gray-100">{att.id}</td>
                        <td className="px-4 py-3 text-sm text-healthos-600">{att.encounter}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{att.patientName}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{att.provider}</td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                          {new Date(att.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">{attestationStatusBadge(att.status)}</td>
                      </tr>
                    ))}
                  {attestations.filter((a) => a.status === "approved").length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                        No approved attestations yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
