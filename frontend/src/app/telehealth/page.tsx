"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchTelehealthSessions,
  fetchTelehealthSession,
  createTelehealthSession,
  prepareVisit,
  startVideoSession,
  generateClinicalNote,
  fetchClinicalNotes,
  signClinicalNote,
  amendClinicalNote,
  endVideoSession,
  type TelehealthSession,
  type ClinicalNote,
} from "@/lib/api";

// ── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_SESSIONS: TelehealthSession[] = [
  {
    session_id: "ts-001",
    patient_id: "p-101",
    patient_name: "Maria Garcia",
    visit_type: "urgent",
    urgency: "high",
    status: "waiting",
    estimated_wait_minutes: 3,
    chief_complaint: "Severe chest pain radiating to left arm, onset 45 minutes ago",
    created_at: new Date(Date.now() - 45 * 60000).toISOString(),
  },
  {
    session_id: "ts-002",
    patient_id: "p-102",
    patient_name: "James Thompson",
    visit_type: "follow-up",
    urgency: "medium",
    status: "in-progress",
    estimated_wait_minutes: 0,
    chief_complaint: "Post-surgical follow-up for knee replacement — Day 14",
    created_at: new Date(Date.now() - 25 * 60000).toISOString(),
  },
  {
    session_id: "ts-003",
    patient_id: "p-103",
    patient_name: "Aisha Patel",
    visit_type: "mental-health",
    urgency: "medium",
    status: "waiting",
    estimated_wait_minutes: 8,
    chief_complaint: "Increased anxiety, difficulty sleeping, requests medication review",
    created_at: new Date(Date.now() - 18 * 60000).toISOString(),
  },
  {
    session_id: "ts-004",
    patient_id: "p-104",
    patient_name: "Robert Chen",
    visit_type: "new",
    urgency: "low",
    status: "waiting",
    estimated_wait_minutes: 15,
    chief_complaint: "Persistent lower back pain for 2 weeks, no prior treatment",
    created_at: new Date(Date.now() - 12 * 60000).toISOString(),
  },
  {
    session_id: "ts-005",
    patient_id: "p-105",
    patient_name: "Elena Vasquez",
    visit_type: "follow-up",
    urgency: "low",
    status: "completed",
    estimated_wait_minutes: 0,
    chief_complaint: "Diabetes management check — A1C review",
    created_at: new Date(Date.now() - 90 * 60000).toISOString(),
  },
  {
    session_id: "ts-006",
    patient_id: "p-106",
    patient_name: "David Kim",
    visit_type: "urgent",
    urgency: "high",
    status: "in-progress",
    estimated_wait_minutes: 0,
    chief_complaint: "Acute migraine with visual disturbances, nausea",
    created_at: new Date(Date.now() - 10 * 60000).toISOString(),
  },
  {
    session_id: "ts-007",
    patient_id: "p-107",
    patient_name: "Sarah Williams",
    visit_type: "new",
    urgency: "low",
    status: "completed",
    estimated_wait_minutes: 0,
    chief_complaint: "Annual wellness visit — preventive care screening",
    created_at: new Date(Date.now() - 120 * 60000).toISOString(),
  },
  {
    session_id: "ts-008",
    patient_id: "p-108",
    patient_name: "Michael Brown",
    visit_type: "mental-health",
    urgency: "high",
    status: "waiting",
    estimated_wait_minutes: 5,
    chief_complaint: "Worsening depression symptoms, PHQ-9 score 18",
    created_at: new Date(Date.now() - 8 * 60000).toISOString(),
  },
];

const DEMO_NOTES: ClinicalNote[] = [
  {
    note_id: "cn-001",
    session_id: "ts-002",
    status: "draft",
    sections: [
      { section: "Chief Complaint", content: "Post-surgical follow-up for knee replacement — Day 14. Patient reports moderate pain 4/10.", confidence: 0.95 },
      { section: "History of Present Illness", content: "Patient underwent right total knee arthroplasty 14 days ago. Reports improving range of motion, moderate swelling, and pain managed with prescribed analgesics.", confidence: 0.91 },
      { section: "Assessment", content: "Post-op recovery progressing as expected. Wound healing well, no signs of infection. ROM improving.", confidence: 0.88 },
      { section: "Plan", content: "Continue current medication regimen. Increase physical therapy to 3x/week. Follow-up in 2 weeks. Contact if fever >101F or increasing swelling.", confidence: 0.85 },
    ],
    generated_at: new Date(Date.now() - 20 * 60000).toISOString(),
    generated_by: "AI Clinical Scribe",
    overall_confidence: 0.9,
  },
  {
    note_id: "cn-002",
    session_id: "ts-005",
    status: "pending_review",
    sections: [
      { section: "Chief Complaint", content: "Diabetes management check — A1C review. Patient concerned about recent glucose variability.", confidence: 0.97 },
      { section: "History of Present Illness", content: "Type 2 diabetes diagnosed 5 years ago. Current A1C 7.2%, down from 7.8% three months ago. Reports improved dietary adherence.", confidence: 0.93 },
      { section: "Assessment", content: "T2DM with improving glycemic control. A1C trending toward target. Hyperlipidemia well-controlled.", confidence: 0.92 },
      { section: "Plan", content: "Continue metformin 1000mg BID. Repeat A1C in 3 months. Referral to nutritionist for meal planning optimization. Annual eye exam due.", confidence: 0.89 },
    ],
    generated_at: new Date(Date.now() - 85 * 60000).toISOString(),
    generated_by: "AI Clinical Scribe",
    overall_confidence: 0.93,
  },
  {
    note_id: "cn-003",
    session_id: "ts-007",
    status: "signed",
    sections: [
      { section: "Chief Complaint", content: "Annual wellness visit — preventive care screening.", confidence: 0.98 },
      { section: "Review of Systems", content: "No acute complaints. Denies chest pain, SOB, abdominal pain. Reports occasional tension headaches relieved with OTC analgesics.", confidence: 0.94 },
      { section: "Assessment", content: "Healthy adult female. Up to date on vaccinations. BMI 24.3 (normal). BP 118/76.", confidence: 0.96 },
      { section: "Plan", content: "Age-appropriate cancer screenings ordered. Flu vaccine administered. Continue current exercise regimen. Return in 12 months.", confidence: 0.95 },
    ],
    generated_at: new Date(Date.now() - 110 * 60000).toISOString(),
    generated_by: "AI Clinical Scribe",
    signed_at: new Date(Date.now() - 100 * 60000).toISOString(),
    signed_by: "Dr. Sarah Mitchell",
    overall_confidence: 0.96,
  },
];

const HISTORY_ENTRIES = [
  { date: "2026-03-15", patient: "Maria Garcia", visitType: "urgent", duration: "—", status: "waiting", noteStatus: "—" },
  { date: "2026-03-15", patient: "James Thompson", visitType: "follow-up", duration: "22 min", status: "in-progress", noteStatus: "draft" },
  { date: "2026-03-15", patient: "David Kim", visitType: "urgent", duration: "18 min", status: "in-progress", noteStatus: "—" },
  { date: "2026-03-15", patient: "Elena Vasquez", visitType: "follow-up", duration: "28 min", status: "completed", noteStatus: "pending_review" },
  { date: "2026-03-15", patient: "Sarah Williams", visitType: "new", duration: "35 min", status: "completed", noteStatus: "signed" },
  { date: "2026-03-14", patient: "John Davis", visitType: "follow-up", duration: "20 min", status: "completed", noteStatus: "signed" },
  { date: "2026-03-14", patient: "Lisa Martinez", visitType: "mental-health", duration: "45 min", status: "completed", noteStatus: "signed" },
  { date: "2026-03-14", patient: "Kevin Nguyen", visitType: "urgent", duration: "15 min", status: "completed", noteStatus: "signed" },
  { date: "2026-03-13", patient: "Angela Foster", visitType: "new", duration: "32 min", status: "completed", noteStatus: "signed" },
  { date: "2026-03-13", patient: "Thomas Wright", visitType: "follow-up", duration: "18 min", status: "completed", noteStatus: "pending_review" },
];

// ── Helper Components ────────────────────────────────────────────────────────

function visitTypeBadge(type: string) {
  const map: Record<string, string> = {
    urgent: "bg-red-100 text-red-700 border-red-200",
    "follow-up": "bg-blue-100 text-blue-700 border-blue-200",
    new: "bg-green-100 text-green-700 border-green-200",
    "mental-health": "bg-purple-100 text-purple-700 border-purple-200",
  };
  return map[type] || "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700";
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    waiting: "bg-amber-100 text-amber-700",
    "in-progress": "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
  };
  return map[status] || "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300";
}

function noteStatusBadge(status: string) {
  const map: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-700 border-yellow-200",
    pending_review: "bg-blue-100 text-blue-700 border-blue-200",
    signed: "bg-green-100 text-green-700 border-green-200",
  };
  return map[status] || "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700";
}

function urgencyColor(urgency: string) {
  const map: Record<string, string> = {
    high: "border-l-red-500",
    medium: "border-l-amber-500",
    low: "border-l-green-500",
  };
  return map[urgency] || "border-l-gray-300";
}

function urgencyDot(urgency: string) {
  const map: Record<string, string> = {
    high: "bg-red-500",
    medium: "bg-amber-500",
    low: "bg-green-500",
  };
  return map[urgency] || "bg-gray-400";
}

function confidenceBarColor(score: number) {
  if (score >= 0.9) return "bg-green-500";
  if (score >= 0.75) return "bg-blue-500";
  if (score >= 0.6) return "bg-amber-500";
  return "bg-red-500";
}

function formatTimeSince(isoDate: string) {
  const mins = Math.round((Date.now() - new Date(isoDate).getTime()) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ${mins % 60}m ago`;
}

function LoadingSpinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

// ── Video Session Overlay ────────────────────────────────────────────────────

function VideoSessionUI({
  session,
  onEnd,
}: {
  session: TelehealthSession;
  onEnd: () => void;
}) {
  const [elapsed, setElapsed] = useState(0);
  const [muted, setMuted] = useState(false);
  const [cameraOff, setCameraOff] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [ending, setEnding] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const handleEnd = async () => {
    setEnding(true);
    try {
      await endVideoSession(session.session_id);
    } catch {
      // proceed to close
    }
    setEnding(false);
    onEnd();
  };

  return (
    <div className="fixed inset-0 z-50 bg-gray-900 flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 bg-gray-800 text-white">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
          <span className="font-semibold">LIVE</span>
          <span className="text-gray-500 dark:text-gray-400">|</span>
          <span className="text-sm text-gray-300">{session.patient_name}</span>
          <span className="inline-block rounded-full px-2 py-0.5 text-xs font-medium border ${visitTypeBadge(session.visit_type)}">{session.visit_type.replace("-", " ")}</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="font-mono text-lg tabular-nums">{formatElapsed(elapsed)}</span>
        </div>
      </div>

      {/* Video area */}
      <div className="flex-1 flex items-center justify-center relative">
        <div className="grid grid-cols-2 gap-4 w-full max-w-5xl px-8">
          {/* Patient camera */}
          <div className="relative rounded-2xl bg-gray-800 aspect-video flex items-center justify-center overflow-hidden border border-gray-700">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-healthos-600 flex items-center justify-center mx-auto mb-3">
                <span className="text-3xl font-bold text-white">
                  {session.patient_name?.split(" ").map((n) => n[0]).join("") || "P"}
                </span>
              </div>
              <p className="text-gray-500 dark:text-gray-400 text-sm">{session.patient_name}</p>
              <p className="text-gray-500 dark:text-gray-400 text-xs mt-1">Patient Camera</p>
            </div>
            <div className="absolute top-3 left-3 flex items-center gap-2">
              <span className="inline-block rounded-full bg-green-500/20 px-2 py-0.5 text-xs text-green-400 font-medium">Connected</span>
            </div>
          </div>

          {/* Provider camera */}
          <div className="relative rounded-2xl bg-gray-800 aspect-video flex items-center justify-center overflow-hidden border border-gray-700">
            {cameraOff ? (
              <div className="text-center">
                <div className="w-20 h-20 rounded-full bg-gray-600 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-8 h-8 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M12 18.75H4.5a2.25 2.25 0 01-2.25-2.25V7.5A2.25 2.25 0 014.5 5.25h7.5" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3l18 18" />
                  </svg>
                </div>
                <p className="text-gray-500 dark:text-gray-400 text-sm">Camera Off</p>
              </div>
            ) : (
              <div className="text-center">
                <div className="w-20 h-20 rounded-full bg-healthos-700 flex items-center justify-center mx-auto mb-3">
                  <span className="text-3xl font-bold text-white">Dr</span>
                </div>
                <p className="text-gray-500 dark:text-gray-400 text-sm">You (Provider)</p>
              </div>
            )}
            <div className="absolute top-3 left-3">
              <span className="inline-block rounded-full bg-blue-500/20 px-2 py-0.5 text-xs text-blue-400 font-medium">
                {screenSharing ? "Sharing Screen" : "Your Camera"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom controls */}
      <div className="flex items-center justify-center gap-4 py-6 bg-gray-800">
        <button
          onClick={() => setMuted(!muted)}
          className={`flex items-center justify-center w-14 h-14 rounded-full transition-colors ${muted ? "bg-red-500 hover:bg-red-600" : "bg-gray-600 hover:bg-gray-500"}`}
          title={muted ? "Unmute" : "Mute"}
        >
          {muted ? (
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
            </svg>
          ) : (
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          )}
        </button>

        <button
          onClick={() => setCameraOff(!cameraOff)}
          className={`flex items-center justify-center w-14 h-14 rounded-full transition-colors ${cameraOff ? "bg-red-500 hover:bg-red-600" : "bg-gray-600 hover:bg-gray-500"}`}
          title={cameraOff ? "Turn Camera On" : "Turn Camera Off"}
        >
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            {cameraOff && <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3l18 18" />}
          </svg>
        </button>

        <button
          onClick={() => setScreenSharing(!screenSharing)}
          className={`flex items-center justify-center w-14 h-14 rounded-full transition-colors ${screenSharing ? "bg-green-500 hover:bg-green-600" : "bg-gray-600 hover:bg-gray-500"}`}
          title={screenSharing ? "Stop Sharing" : "Share Screen"}
        >
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </button>

        <button
          onClick={handleEnd}
          disabled={ending}
          className="flex items-center justify-center w-14 h-14 rounded-full bg-red-600 hover:bg-red-700 transition-colors disabled:opacity-50"
          title="End Call"
        >
          {ending ? (
            <LoadingSpinner />
          ) : (
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

type TabKey = "active" | "waiting" | "notes" | "history";

export default function TelehealthPage() {
  const [sessions, setSessions] = useState<TelehealthSession[]>(DEMO_SESSIONS);
  const [notes, setNotes] = useState<ClinicalNote[]>(DEMO_NOTES);
  const [activeTab, setActiveTab] = useState<TabKey>("active");
  const [showNewSession, setShowNewSession] = useState(false);
  const [creating, setCreating] = useState(false);
  const [sessionForm, setSessionForm] = useState({
    patientName: "",
    reason: "",
    sessionType: "video",
    visitType: "new",
    urgency: "low",
  });
  const [loadingActions, setLoadingActions] = useState<Record<string, string>>({});
  const [videoSession, setVideoSession] = useState<TelehealthSession | null>(null);
  const [expandedNote, setExpandedNote] = useState<string | null>(null);
  const [amendingNote, setAmendingNote] = useState<string | null>(null);
  const [amendText, setAmendText] = useState("");
  const [dateFilter, setDateFilter] = useState({ from: "2026-03-13", to: "2026-03-15" });

  // Load sessions from API on mount (fall back to demo data)
  useEffect(() => {
    fetchTelehealthSessions()
      .then((data) => {
        if (data.sessions && data.sessions.length > 0) {
          setSessions(data.sessions);
        }
      })
      .catch(() => {
        // Keep demo data
      });
  }, []);

  // Derived stats
  const activeSessions = sessions.filter((s) => s.status === "in-progress");
  const waitingSessions = sessions.filter((s) => s.status === "waiting");
  const completedToday = sessions.filter((s) => s.status === "completed");
  const avgWait = waitingSessions.length
    ? Math.round(waitingSessions.reduce((sum, s) => sum + (s.estimated_wait_minutes || 0), 0) / waitingSessions.length)
    : 0;
  const liveCount = activeSessions.length + waitingSessions.length;

  // Action helpers
  const setActionLoading = (sessionId: string, action: string) =>
    setLoadingActions((prev) => ({ ...prev, [sessionId]: action }));
  const clearActionLoading = (sessionId: string) =>
    setLoadingActions((prev) => {
      const next = { ...prev };
      delete next[sessionId];
      return next;
    });

  const handlePrepareVisit = useCallback(async (sessionId: string) => {
    setActionLoading(sessionId, "prepare");
    try {
      await prepareVisit(sessionId);
    } catch {
      // Demo mode — show success anyway
    }
    clearActionLoading(sessionId);
  }, []);

  const handleStartVideo = useCallback(
    async (session: TelehealthSession) => {
      setActionLoading(session.session_id, "video");
      try {
        await startVideoSession(session.session_id);
      } catch {
        // Demo mode
      }
      clearActionLoading(session.session_id);
      setVideoSession(session);
    },
    []
  );

  const handleGenerateNote = useCallback(async (sessionId: string) => {
    setActionLoading(sessionId, "note");
    try {
      await generateClinicalNote(sessionId, { auto_generate: true });
    } catch {
      // Demo mode — add a demo note
      const session = sessions.find((s) => s.session_id === sessionId);
      if (session) {
        const newNote: ClinicalNote = {
          note_id: `cn-${Date.now()}`,
          session_id: sessionId,
          status: "draft",
          sections: [
            { section: "Chief Complaint", content: session.chief_complaint || "Not specified", confidence: 0.92 },
            { section: "Assessment", content: "AI-generated assessment pending physician review.", confidence: 0.85 },
            { section: "Plan", content: "AI-generated plan pending physician review.", confidence: 0.82 },
          ],
          generated_at: new Date().toISOString(),
          generated_by: "AI Clinical Scribe",
          overall_confidence: 0.86,
        };
        setNotes((prev) => [newNote, ...prev]);
      }
    }
    clearActionLoading(sessionId);
  }, [sessions]);

  const handleSignNote = useCallback(async (note: ClinicalNote) => {
    setActionLoading(note.note_id, "sign");
    try {
      await signClinicalNote(note.session_id, note.note_id);
    } catch {
      // Demo mode
    }
    setNotes((prev) =>
      prev.map((n) =>
        n.note_id === note.note_id
          ? { ...n, status: "signed" as const, signed_at: new Date().toISOString(), signed_by: "Dr. Provider" }
          : n
      )
    );
    clearActionLoading(note.note_id);
  }, []);

  const handleAmendNote = useCallback(
    async (note: ClinicalNote) => {
      if (!amendText.trim()) return;
      setActionLoading(note.note_id, "amend");
      try {
        await amendClinicalNote(note.session_id, note.note_id, [
          { section: "Amendment", content: amendText },
        ]);
      } catch {
        // Demo mode
      }
      setNotes((prev) =>
        prev.map((n) =>
          n.note_id === note.note_id
            ? {
                ...n,
                amendments: [
                  ...(n.amendments || []),
                  { section: "Amendment", content: amendText, amended_at: new Date().toISOString() },
                ],
              }
            : n
        )
      );
      setAmendText("");
      setAmendingNote(null);
      clearActionLoading(note.note_id);
    },
    [amendText]
  );

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const session = await createTelehealthSession({
        patient_name: sessionForm.patientName,
        reason: sessionForm.reason,
        session_type: sessionForm.sessionType,
        visit_type: sessionForm.visitType,
        urgency: sessionForm.urgency,
      });
      setSessions((prev) => [session, ...prev]);
    } catch {
      // Demo fallback — add locally
      const demoSession: TelehealthSession = {
        session_id: `ts-${Date.now()}`,
        patient_id: `p-${Date.now()}`,
        patient_name: sessionForm.patientName,
        visit_type: sessionForm.visitType,
        urgency: sessionForm.urgency,
        status: "waiting",
        estimated_wait_minutes: Math.floor(Math.random() * 15) + 3,
        chief_complaint: sessionForm.reason,
        created_at: new Date().toISOString(),
      };
      setSessions((prev) => [demoSession, ...prev]);
    }
    setShowNewSession(false);
    setSessionForm({ patientName: "", reason: "", sessionType: "video", visitType: "new", urgency: "low" });
    setCreating(false);
  };

  const handleEndVideo = useCallback(() => {
    if (videoSession) {
      setSessions((prev) =>
        prev.map((s) =>
          s.session_id === videoSession.session_id ? { ...s, status: "completed" } : s
        )
      );
    }
    setVideoSession(null);
  }, [videoSession]);

  // Filtered history entries
  const filteredHistory = HISTORY_ENTRIES.filter(
    (h) => h.date >= dateFilter.from && h.date <= dateFilter.to
  );

  // ── Tab definitions ──
  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: "active", label: "Active Sessions", count: activeSessions.length + waitingSessions.length },
    { key: "waiting", label: "Waiting Room", count: waitingSessions.length },
    { key: "notes", label: "Clinical Notes", count: notes.length },
    { key: "history", label: "Session History" },
  ];

  // ── Video session overlay ──
  if (videoSession) {
    return <VideoSessionUI session={videoSession} onEnd={handleEndVideo} />;
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Telehealth Command Center</h1>
            <span className="relative flex items-center gap-1.5 rounded-full bg-healthos-100 px-3 py-1 text-sm font-semibold text-healthos-700">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-healthos-500 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-healthos-600" />
              </span>
              {liveCount} Live
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor sessions, manage the waiting room, review clinical notes, and conduct video visits.
          </p>
        </div>
        <button
          onClick={() => setShowNewSession(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Session
        </button>
      </div>

      {/* ── Stats Bar ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {[
          {
            label: "Active Sessions",
            value: activeSessions.length,
            icon: (
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            ),
            bg: "bg-blue-50",
          },
          {
            label: "Waiting Room",
            value: waitingSessions.length,
            icon: (
              <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ),
            bg: "bg-amber-50",
          },
          {
            label: "Avg Wait Time",
            value: `${avgWait}m`,
            icon: (
              <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            ),
            bg: "bg-purple-50",
          },
          {
            label: "Completed Today",
            value: completedToday.length,
            icon: (
              <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ),
            bg: "bg-green-50",
          },
          {
            label: "Patient Satisfaction",
            value: "4.8/5",
            icon: (
              <svg className="w-5 h-5 text-healthos-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            ),
            bg: "bg-healthos-50",
          },
        ].map((stat) => (
          <div key={stat.label} className="card card-hover p-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <div className={`flex items-center justify-center w-10 h-10 rounded-lg ${stat.bg}`}>
                {stat.icon}
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stat.value}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{stat.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Tabs ── */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-6" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`relative pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "text-healthos-600 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-healthos-600"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className={`ml-2 inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs font-medium ${
                    activeTab === tab.key
                      ? "bg-healthos-100 text-healthos-700"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab Content ── */}
      <div className="animate-fade-in-up">
        {/* ─── Active Sessions ─── */}
        {activeTab === "active" && (
          <div className="space-y-4">
            {sessions.filter((s) => s.status !== "completed").length === 0 ? (
              <div className="card p-12 text-center">
                <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p className="text-gray-500 dark:text-gray-400 font-medium">No active sessions</p>
                <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Create a new session to get started.</p>
              </div>
            ) : (
              sessions
                .filter((s) => s.status !== "completed")
                .sort((a, b) => {
                  const urgencyOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
                  return (urgencyOrder[a.urgency] ?? 2) - (urgencyOrder[b.urgency] ?? 2);
                })
                .map((session) => (
                  <div
                    key={session.session_id}
                    className={`card card-hover border-l-4 ${urgencyColor(session.urgency)} p-5 animate-fade-in-up`}
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{session.patient_name}</h3>
                          <span
                            className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${visitTypeBadge(session.visit_type)}`}
                          >
                            {session.visit_type.replace("-", " ")}
                          </span>
                          <span
                            className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadge(session.status)}`}
                          >
                            {session.status.replace("-", " ")}
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                          <span className="flex items-center gap-1.5">
                            <span className={`inline-block h-2 w-2 rounded-full ${urgencyDot(session.urgency)}`} />
                            Urgency: <span className="font-medium text-gray-700 dark:text-gray-300 capitalize">{session.urgency}</span>
                          </span>
                          {session.estimated_wait_minutes !== undefined && session.estimated_wait_minutes > 0 && (
                            <span className="flex items-center gap-1">
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              Est. wait: {session.estimated_wait_minutes}m
                            </span>
                          )}
                          <span>Joined {formatTimeSince(session.created_at)}</span>
                        </div>

                        {session.chief_complaint && (
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            <span className="font-medium text-gray-700 dark:text-gray-300">Chief Complaint: </span>
                            {session.chief_complaint}
                          </p>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-2 shrink-0">
                        <button
                          onClick={() => handlePrepareVisit(session.session_id)}
                          disabled={loadingActions[session.session_id] === "prepare"}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
                        >
                          {loadingActions[session.session_id] === "prepare" ? (
                            <LoadingSpinner />
                          ) : (
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                            </svg>
                          )}
                          Prepare Visit
                        </button>
                        <button
                          onClick={() => handleStartVideo(session)}
                          disabled={loadingActions[session.session_id] === "video"}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-healthos-600 px-3 py-2 text-xs font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                        >
                          {loadingActions[session.session_id] === "video" ? (
                            <LoadingSpinner />
                          ) : (
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          )}
                          Start Video
                        </button>
                        <button
                          onClick={() => handleGenerateNote(session.session_id)}
                          disabled={loadingActions[session.session_id] === "note"}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-healthos-300 bg-healthos-50 px-3 py-2 text-xs font-medium text-healthos-700 hover:bg-healthos-100 disabled:opacity-50 transition-colors"
                        >
                          {loadingActions[session.session_id] === "note" ? (
                            <LoadingSpinner />
                          ) : (
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          )}
                          Generate Note
                        </button>
                      </div>
                    </div>
                  </div>
                ))
            )}
          </div>
        )}

        {/* ─── Waiting Room ─── */}
        {activeTab === "waiting" && (
          <div className="space-y-4">
            {waitingSessions.length === 0 ? (
              <div className="card p-12 text-center">
                <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-gray-500 dark:text-gray-400 font-medium">Waiting room is empty</p>
                <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">All patients have been seen. Great work!</p>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {waitingSessions.length} patient{waitingSessions.length !== 1 ? "s" : ""} waiting
                  </p>
                  <button
                    onClick={() => {
                      const next = waitingSessions.sort((a, b) => {
                        const urgencyOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
                        return (urgencyOrder[a.urgency] ?? 2) - (urgencyOrder[b.urgency] ?? 2);
                      })[0];
                      if (next) handleStartVideo(next);
                    }}
                    className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                    Call Next Patient
                  </button>
                </div>
                {waitingSessions
                  .sort((a, b) => {
                    const urgencyOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
                    return (urgencyOrder[a.urgency] ?? 2) - (urgencyOrder[b.urgency] ?? 2);
                  })
                  .map((session, index) => (
                    <div
                      key={session.session_id}
                      className={`card card-hover border-l-4 ${urgencyColor(session.urgency)} p-5 animate-fade-in-up`}
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex items-start gap-4">
                          <div className="flex flex-col items-center">
                            <span className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-800 text-lg font-bold text-gray-600 dark:text-gray-400">
                              {index + 1}
                            </span>
                            <span className="mt-1 text-xs text-gray-500 dark:text-gray-400">Position</span>
                          </div>
                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="font-semibold text-gray-900 dark:text-gray-100">{session.patient_name}</h3>
                              <span
                                className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${visitTypeBadge(session.visit_type)}`}
                              >
                                {session.visit_type.replace("-", " ")}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                              <span className="flex items-center gap-1.5">
                                <span className={`inline-block h-2 w-2 rounded-full ${urgencyDot(session.urgency)}`} />
                                <span className="capitalize">{session.urgency} urgency</span>
                              </span>
                              <span>Waiting {formatTimeSince(session.created_at)}</span>
                              {session.estimated_wait_minutes !== undefined && (
                                <span>Est. {session.estimated_wait_minutes}m</span>
                              )}
                            </div>
                            {session.chief_complaint && (
                              <p className="text-sm text-gray-600 dark:text-gray-400">{session.chief_complaint}</p>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={() => handleStartVideo(session)}
                          disabled={!!loadingActions[session.session_id]}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors shrink-0"
                        >
                          {loadingActions[session.session_id] === "video" ? (
                            <LoadingSpinner />
                          ) : (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          )}
                          Start Visit
                        </button>
                      </div>
                    </div>
                  ))}
              </>
            )}
          </div>
        )}

        {/* ─── Clinical Notes ─── */}
        {activeTab === "notes" && (
          <div className="space-y-4">
            {notes.length === 0 ? (
              <div className="card p-12 text-center">
                <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-gray-500 dark:text-gray-400 font-medium">No clinical notes yet</p>
                <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Generate a note from an active session.</p>
              </div>
            ) : (
              notes.map((note) => {
                const session = sessions.find((s) => s.session_id === note.session_id);
                const isExpanded = expandedNote === note.note_id;
                return (
                  <div key={note.note_id} className="card card-hover p-5 animate-fade-in-up">
                    <div className="flex flex-col gap-3">
                      {/* Header */}
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                            {session?.patient_name || `Session ${note.session_id}`}
                          </h3>
                          <span
                            className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${noteStatusBadge(note.status)}`}
                          >
                            {note.status.replace("_", " ")}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            Generated {formatTimeSince(note.generated_at)} by {note.generated_by}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {note.status !== "signed" && (
                            <button
                              onClick={() => handleSignNote(note)}
                              disabled={loadingActions[note.note_id] === "sign"}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
                            >
                              {loadingActions[note.note_id] === "sign" ? (
                                <LoadingSpinner />
                              ) : (
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                              Sign Note
                            </button>
                          )}
                          <button
                            onClick={() => {
                              setAmendingNote(amendingNote === note.note_id ? null : note.note_id);
                              setAmendText("");
                            }}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Amend
                          </button>
                          <button
                            onClick={() => setExpandedNote(isExpanded ? null : note.note_id)}
                            className="inline-flex items-center gap-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                          >
                            {isExpanded ? "Collapse" : "Expand"}
                            <svg
                              className={`w-3.5 h-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                        </div>
                      </div>

                      {/* Confidence bar */}
                      {note.overall_confidence !== undefined && (
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">Overall Confidence</span>
                          <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${confidenceBarColor(note.overall_confidence)}`}
                              style={{ width: `${note.overall_confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-12 text-right">
                            {Math.round(note.overall_confidence * 100)}%
                          </span>
                        </div>
                      )}

                      {/* Sections preview (collapsed = first two, expanded = all) */}
                      <div className="space-y-2">
                        {(isExpanded ? note.sections : note.sections.slice(0, 2)).map((section) => (
                          <div key={section.section} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                                {section.section}
                              </span>
                              {section.confidence !== undefined && (
                                <div className="flex items-center gap-1.5">
                                  <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${confidenceBarColor(section.confidence)}`}
                                      style={{ width: `${section.confidence * 100}%` }}
                                    />
                                  </div>
                                  <span className="text-[11px] text-gray-500 dark:text-gray-400">{Math.round(section.confidence * 100)}%</span>
                                </div>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400">{section.content}</p>
                          </div>
                        ))}
                        {!isExpanded && note.sections.length > 2 && (
                          <button
                            onClick={() => setExpandedNote(note.note_id)}
                            className="text-xs text-healthos-600 hover:text-healthos-700 font-medium"
                          >
                            + {note.sections.length - 2} more section{note.sections.length - 2 > 1 ? "s" : ""}
                          </button>
                        )}
                      </div>

                      {/* Amendments */}
                      {isExpanded && note.amendments && note.amendments.length > 0 && (
                        <div className="space-y-2 border-t border-gray-100 dark:border-gray-800 pt-3">
                          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Amendments</span>
                          {note.amendments.map((a, i) => (
                            <div key={i} className="rounded-lg bg-amber-50 border border-amber-100 p-3">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-medium text-amber-700">{a.section}</span>
                                <span className="text-[11px] text-amber-500">{formatTimeSince(a.amended_at)}</span>
                              </div>
                              <p className="text-sm text-amber-800">{a.content}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Signed info */}
                      {note.signed_at && note.signed_by && (
                        <div className="flex items-center gap-2 text-xs text-green-600 pt-1">
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                          </svg>
                          Signed by {note.signed_by} {formatTimeSince(note.signed_at)}
                        </div>
                      )}

                      {/* Amend input */}
                      {amendingNote === note.note_id && (
                        <div className="border-t border-gray-100 dark:border-gray-800 pt-3 space-y-2">
                          <textarea
                            value={amendText}
                            onChange={(e) => setAmendText(e.target.value)}
                            placeholder="Enter amendment text..."
                            rows={3}
                            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                          />
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => {
                                setAmendingNote(null);
                                setAmendText("");
                              }}
                              className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleAmendNote(note)}
                              disabled={!amendText.trim() || loadingActions[note.note_id] === "amend"}
                              className="inline-flex items-center gap-1.5 rounded-lg bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                            >
                              {loadingActions[note.note_id] === "amend" ? <LoadingSpinner /> : null}
                              Submit Amendment
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* ─── Session History ─── */}
        {activeTab === "history" && (
          <div className="space-y-4">
            {/* Date filter */}
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">From</label>
              <input
                type="date"
                value={dateFilter.from}
                onChange={(e) => setDateFilter((f) => ({ ...f, from: e.target.value }))}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">To</label>
              <input
                type="date"
                value={dateFilter.to}
                onChange={(e) => setDateFilter((f) => ({ ...f, to: e.target.value }))}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
            </div>

            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                      <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Date</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Patient</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Visit Type</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Duration</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Status</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Notes</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {filteredHistory.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                          No sessions found for the selected date range.
                        </td>
                      </tr>
                    ) : (
                      filteredHistory.map((entry, idx) => (
                        <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">{entry.date}</td>
                          <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">{entry.patient}</td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${visitTypeBadge(entry.visitType)}`}
                            >
                              {entry.visitType.replace("-", " ")}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">{entry.duration}</td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusBadge(entry.status)}`}
                            >
                              {entry.status.replace("-", " ")}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            {entry.noteStatus === "—" ? (
                              <span className="text-gray-500 dark:text-gray-400">—</span>
                            ) : (
                              <span
                                className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${noteStatusBadge(entry.noteStatus)}`}
                              >
                                {entry.noteStatus.replace("_", " ")}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <button className="text-xs text-healthos-600 hover:text-healthos-700 font-medium">
                              View Details
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── New Session Modal ── */}
      {showNewSession && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4"
          onClick={() => setShowNewSession(false)}
        >
          <div
            className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-gray-900 p-4 sm:p-6 shadow-2xl animate-fade-in-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">New Telehealth Session</h2>
              <button
                onClick={() => setShowNewSession(false)}
                className="text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:text-gray-400 text-xl leading-none"
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Patient Name *</label>
                <input
                  required
                  value={sessionForm.patientName}
                  onChange={(e) => setSessionForm({ ...sessionForm, patientName: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  placeholder="e.g. Maria Garcia"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Visit Type *</label>
                  <select
                    required
                    value={sessionForm.visitType}
                    onChange={(e) => setSessionForm({ ...sessionForm, visitType: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="new">New Patient</option>
                    <option value="follow-up">Follow-Up</option>
                    <option value="urgent">Urgent</option>
                    <option value="mental-health">Mental Health</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Urgency *</label>
                  <select
                    required
                    value={sessionForm.urgency}
                    onChange={(e) => setSessionForm({ ...sessionForm, urgency: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Session Type</label>
                <select
                  value={sessionForm.sessionType}
                  onChange={(e) => setSessionForm({ ...sessionForm, sessionType: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="video">Video Call</option>
                  <option value="audio">Audio Only</option>
                  <option value="chat">Chat</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Chief Complaint / Reason</label>
                <textarea
                  value={sessionForm.reason}
                  onChange={(e) => setSessionForm({ ...sessionForm, reason: e.target.value })}
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  placeholder="e.g. Follow-up on blood pressure medication"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewSession(false)}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50"
                >
                  {creating && <LoadingSpinner />}
                  {creating ? "Creating..." : "Create Session"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
