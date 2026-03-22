"use client";

import { useState, useCallback } from "react";
import {
  submitPHQ9Screening,
  submitGAD7Screening,
  detectCrisis,
  submitTherapeuticEngagement,
  createSafetyPlan,
} from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════════════════
   DEMO DATA
   ═══════════════════════════════════════════════════════════════════════════ */

const STATS = [
  { label: "Active Patients", value: "128", icon: "👤", delta: "+12", up: true },
  { label: "Screenings Today", value: "34", icon: "📋", delta: "+8", up: true },
  { label: "Crisis Alerts", value: "3", icon: "🚨", delta: "-2", up: false },
  { label: "Avg PHQ-9 Score", value: "8.4", icon: "📊", delta: "-1.2", up: false },
  { label: "Engagement Rate", value: "76%", icon: "💬", delta: "+4%", up: true },
];

const SCREENING_TOOLS = [
  {
    id: "phq9",
    name: "PHQ-9",
    category: "Depression",
    description: "Patient Health Questionnaire — screens for depression severity over the last 2 weeks.",
    questions: 9,
    color: "bg-blue-500",
    bgLight: "bg-blue-50",
    textColor: "text-blue-700",
  },
  {
    id: "gad7",
    name: "GAD-7",
    category: "Anxiety",
    description: "Generalized Anxiety Disorder scale — measures anxiety symptom severity.",
    questions: 7,
    color: "bg-purple-500",
    bgLight: "bg-purple-50",
    textColor: "text-purple-700",
  },
  {
    id: "auditc",
    name: "AUDIT-C",
    category: "Substance",
    description: "Alcohol Use Disorders Identification Test — brief screening for hazardous drinking.",
    questions: 3,
    color: "bg-amber-500",
    bgLight: "bg-amber-50",
    textColor: "text-amber-700",
  },
];

const PHQ9_QUESTIONS = [
  "Little interest or pleasure in doing things",
  "Feeling down, depressed, or hopeless",
  "Trouble falling or staying asleep, or sleeping too much",
  "Feeling tired or having little energy",
  "Poor appetite or overeating",
  "Feeling bad about yourself — or that you are a failure",
  "Trouble concentrating on things",
  "Moving or speaking so slowly that other people could have noticed",
  "Thoughts that you would be better off dead, or of hurting yourself",
];

const GAD7_QUESTIONS = [
  "Feeling nervous, anxious, or on edge",
  "Not being able to stop or control worrying",
  "Worrying too much about different things",
  "Trouble relaxing",
  "Being so restless that it is hard to sit still",
  "Becoming easily annoyed or irritable",
  "Feeling afraid, as if something awful might happen",
];

const AUDITC_QUESTIONS = [
  "How often do you have a drink containing alcohol?",
  "How many drinks containing alcohol do you have on a typical day when you are drinking?",
  "How often do you have 6 or more drinks on one occasion?",
];

const RECENT_SCREENINGS = [
  { id: "S-001", patient: "Emily Davis", tool: "PHQ-9", score: 16, date: "2026-03-14", trend: "down" },
  { id: "S-002", patient: "Anna Rodriguez", tool: "GAD-7", score: 14, date: "2026-03-14", trend: "up" },
  { id: "S-003", patient: "Michael Brown", tool: "PHQ-9", score: 8, date: "2026-03-13", trend: "down" },
  { id: "S-004", patient: "Lisa Park", tool: "AUDIT-C", score: 5, date: "2026-03-13", trend: "same" },
  { id: "S-005", patient: "David Wilson", tool: "GAD-7", score: 4, date: "2026-03-12", trend: "down" },
  { id: "S-006", patient: "Sarah Kim", tool: "PHQ-9", score: 21, date: "2026-03-12", trend: "up" },
];

const CRISIS_CASES = [
  {
    id: "CR-001",
    patient: "Sarah Kim",
    age: 29,
    riskLevel: "critical" as const,
    riskFactors: ["Active suicidal ideation", "Recent loss of employment", "History of attempts"],
    lastAssessment: "2026-03-15 08:30",
    assignedTo: "Dr. Maria Gonzalez, LCSW",
    recommendedActions: ["Immediate safety assessment", "Emergency contact notification", "24-hour monitoring"],
    status: "active",
  },
  {
    id: "CR-002",
    patient: "James Taylor",
    age: 42,
    riskLevel: "high" as const,
    riskFactors: ["Substance relapse", "Social isolation", "Non-adherence to meds"],
    lastAssessment: "2026-03-15 09:15",
    assignedTo: "Dr. James Lee, MD",
    recommendedActions: ["Urgent outreach", "Substance use reassessment", "Family engagement"],
    status: "active",
  },
  {
    id: "CR-003",
    patient: "Emily Davis",
    age: 34,
    riskLevel: "moderate" as const,
    riskFactors: ["Worsening PHQ-9 trend", "Sleep disruption", "Increased irritability"],
    lastAssessment: "2026-03-14 16:00",
    assignedTo: "Dr. Sarah Kim, PsyD",
    recommendedActions: ["Schedule follow-up within 48h", "Adjust treatment plan", "Coping skills review"],
    status: "active",
  },
];

const PATIENT_LIST = [
  "Emily Davis",
  "Anna Rodriguez",
  "Michael Brown",
  "Lisa Park",
  "David Wilson",
  "Sarah Kim",
  "James Taylor",
];

const PROGRESS_DATA = [
  {
    patient: "Emily Davis",
    screenings: [
      { date: "Jan", tool: "PHQ-9", score: 18 },
      { date: "Feb", tool: "PHQ-9", score: 16 },
      { date: "Mar", tool: "PHQ-9", score: 14 },
    ],
    engagement: { checkins: 85, exercises: 72, attendance: 95 },
    adherence: 88,
    notes: [
      { date: "2026-03-10", author: "Dr. Sarah Kim", text: "Patient showing steady improvement. Continue CBT weekly." },
      { date: "2026-02-24", author: "Dr. Sarah Kim", text: "Adjusted medication dosage. Monitor for side effects." },
    ],
  },
  {
    patient: "Anna Rodriguez",
    screenings: [
      { date: "Jan", tool: "GAD-7", score: 15 },
      { date: "Feb", tool: "GAD-7", score: 18 },
      { date: "Mar", tool: "GAD-7", score: 14 },
    ],
    engagement: { checkins: 60, exercises: 45, attendance: 90 },
    adherence: 72,
    notes: [
      { date: "2026-03-08", author: "Dr. James Lee", text: "Anxiety still elevated. Adding mindfulness component." },
    ],
  },
  {
    patient: "Michael Brown",
    screenings: [
      { date: "Jan", tool: "PHQ-9", score: 14 },
      { date: "Feb", tool: "PHQ-9", score: 10 },
      { date: "Mar", tool: "PHQ-9", score: 8 },
    ],
    engagement: { checkins: 90, exercises: 80, attendance: 100 },
    adherence: 95,
    notes: [
      { date: "2026-03-12", author: "Dr. Maria Gonzalez", text: "Excellent progress with EMDR. Reducing session frequency." },
    ],
  },
];

/* ═══════════════════════════════════════════════════════════════════════════
   HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */

type Tab = "screenings" | "crisis" | "therapeutic" | "progress";

type RiskLevel = "low" | "moderate" | "high" | "critical";

function severityFromScore(tool: string, score: number): { label: string; color: string } {
  if (tool === "PHQ-9") {
    if (score >= 20) return { label: "Severe", color: "bg-red-100 text-red-700" };
    if (score >= 15) return { label: "Moderate-Severe", color: "bg-orange-100 text-orange-700" };
    if (score >= 10) return { label: "Moderate", color: "bg-yellow-100 text-yellow-700" };
    if (score >= 5) return { label: "Mild", color: "bg-green-100 text-green-700" };
    return { label: "Minimal", color: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400" };
  }
  if (tool === "GAD-7") {
    if (score >= 15) return { label: "Severe", color: "bg-red-100 text-red-700" };
    if (score >= 10) return { label: "Moderate", color: "bg-orange-100 text-orange-700" };
    if (score >= 5) return { label: "Mild", color: "bg-yellow-100 text-yellow-700" };
    return { label: "Minimal", color: "bg-green-100 text-green-700" };
  }
  // AUDIT-C
  if (score >= 8) return { label: "Severe", color: "bg-red-100 text-red-700" };
  if (score >= 4) return { label: "Moderate", color: "bg-orange-100 text-orange-700" };
  if (score >= 3) return { label: "Mild", color: "bg-yellow-100 text-yellow-700" };
  return { label: "Minimal", color: "bg-green-100 text-green-700" };
}

function riskCircleColor(level: RiskLevel) {
  switch (level) {
    case "critical": return "bg-red-500";
    case "high": return "bg-orange-500";
    case "moderate": return "bg-yellow-500";
    case "low": return "bg-green-500";
  }
}

function riskBorderColor(level: RiskLevel) {
  switch (level) {
    case "critical": return "border-red-400";
    case "high": return "border-orange-400";
    case "moderate": return "border-yellow-400";
    case "low": return "border-green-400";
  }
}

function trendArrow(trend: string) {
  if (trend === "down") return <span className="text-green-600">&#9660;</span>;
  if (trend === "up") return <span className="text-red-600">&#9650;</span>;
  return <span className="text-gray-500 dark:text-gray-400">&#9644;</span>;
}

function barWidth(score: number, max: number) {
  return `${Math.min((score / max) * 100, 100)}%`;
}

function barColor(score: number, max: number) {
  const pct = score / max;
  if (pct >= 0.75) return "bg-red-500";
  if (pct >= 0.5) return "bg-orange-500";
  if (pct >= 0.25) return "bg-yellow-500";
  return "bg-green-500";
}

/* ═══════════════════════════════════════════════════════════════════════════
   COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */

export default function MentalHealthPage() {
  const [tab, setTab] = useState<Tab>("screenings");

  // Screening state
  const [activeScreening, setActiveScreening] = useState<string | null>(null);
  const [screeningAnswers, setScreeningAnswers] = useState<number[]>([]);
  const [screeningPatient, setScreeningPatient] = useState("");
  const [screeningSubmitting, setScreeningSubmitting] = useState(false);
  const [screeningResult, setScreeningResult] = useState<{ score: number; tool: string } | null>(null);
  const [showNewScreening, setShowNewScreening] = useState(false);

  // Crisis state
  const [crisisPatient, setCrisisPatient] = useState("");
  const [crisisRisk, setCrisisRisk] = useState<RiskLevel>("low");
  const [crisisAssessing, setCrisisAssessing] = useState(false);
  const [showSafetyPlan, setShowSafetyPlan] = useState(false);
  const [safetyPlanData, setSafetyPlanData] = useState({
    warningSigns: "",
    copingStrategies: "",
    supportContacts: "",
    professionalContacts: "",
    safeEnvironment: "",
    reasonsForLiving: "",
  });
  const [safetyPlanSubmitting, setSafetyPlanSubmitting] = useState(false);

  // Therapeutic state
  const [selectedMood, setSelectedMood] = useState<number | null>(null);
  const [moodNote, setMoodNote] = useState("");
  const [cbtSituation, setCbtSituation] = useState("");
  const [cbtThought, setCbtThought] = useState("");
  const [cbtEmotion, setCbtEmotion] = useState("");
  const [cbtAlternative, setCbtAlternative] = useState("");
  const [mindfulnessTimer, setMindfulnessTimer] = useState(0);
  const [mindfulnessRunning, setMindfulnessRunning] = useState(false);
  const [engagementSubmitting, setEngagementSubmitting] = useState(false);

  // Progress state
  const [progressSearch, setProgressSearch] = useState("");
  const [selectedPatientProgress, setSelectedPatientProgress] = useState<string | null>(null);
  const [newNote, setNewNote] = useState("");

  /* ─── Screening logic ─────────────────────────────────────────────────── */

  const questionsFor = (toolId: string) => {
    if (toolId === "phq9") return PHQ9_QUESTIONS;
    if (toolId === "gad7") return GAD7_QUESTIONS;
    return AUDITC_QUESTIONS;
  };

  const startScreening = (toolId: string) => {
    setActiveScreening(toolId);
    setScreeningAnswers(new Array(questionsFor(toolId).length).fill(-1));
    setScreeningResult(null);
    if (!screeningPatient) setScreeningPatient(PATIENT_LIST[0]);
  };

  const handleAnswerChange = (qi: number, value: number) => {
    setScreeningAnswers((prev) => {
      const copy = [...prev];
      copy[qi] = value;
      return copy;
    });
  };

  const submitScreening = useCallback(async () => {
    if (!activeScreening) return;
    setScreeningSubmitting(true);
    const score = screeningAnswers.reduce((a, b) => a + (b >= 0 ? b : 0), 0);
    const toolName = activeScreening === "phq9" ? "PHQ-9" : activeScreening === "gad7" ? "GAD-7" : "AUDIT-C";
    try {
      if (activeScreening === "phq9") {
        await submitPHQ9Screening({ patient_name: screeningPatient, answers: screeningAnswers, score });
      } else if (activeScreening === "gad7") {
        await submitGAD7Screening({ patient_name: screeningPatient, answers: screeningAnswers, score });
      }
    } catch {
      // API unavailable — fall back to demo
    }
    setScreeningResult({ score, tool: toolName });
    setScreeningSubmitting(false);
  }, [activeScreening, screeningAnswers, screeningPatient]);

  /* ─── Crisis logic ────────────────────────────────────────────────────── */

  const assessCrisis = useCallback(async () => {
    if (!crisisPatient) return;
    setCrisisAssessing(true);
    try {
      await detectCrisis({ patient_name: crisisPatient, action: "assess" });
    } catch {
      // demo fallback
    }
    // simulate a result
    const levels: RiskLevel[] = ["low", "moderate", "high", "critical"];
    setCrisisRisk(levels[Math.floor(Math.random() * levels.length)]);
    setCrisisAssessing(false);
  }, [crisisPatient]);

  const submitSafetyPlan = useCallback(async () => {
    setSafetyPlanSubmitting(true);
    try {
      await createSafetyPlan({ patient_name: crisisPatient, ...safetyPlanData });
    } catch {
      // demo fallback
    }
    setSafetyPlanSubmitting(false);
    setShowSafetyPlan(false);
    setSafetyPlanData({ warningSigns: "", copingStrategies: "", supportContacts: "", professionalContacts: "", safeEnvironment: "", reasonsForLiving: "" });
  }, [crisisPatient, safetyPlanData]);

  const resolveCrisis = useCallback(async (caseId: string) => {
    try {
      await detectCrisis({ case_id: caseId, action: "resolve" });
    } catch {
      // demo
    }
  }, []);

  /* ─── Therapeutic logic ───────────────────────────────────────────────── */

  const submitMoodCheckin = useCallback(async () => {
    if (selectedMood === null) return;
    setEngagementSubmitting(true);
    try {
      await submitTherapeuticEngagement({ type: "mood_checkin", mood: selectedMood, note: moodNote });
    } catch {
      // demo
    }
    setEngagementSubmitting(false);
    setSelectedMood(null);
    setMoodNote("");
  }, [selectedMood, moodNote]);

  const submitCBT = useCallback(async () => {
    setEngagementSubmitting(true);
    try {
      await submitTherapeuticEngagement({
        type: "cbt_thought_record",
        situation: cbtSituation,
        thought: cbtThought,
        emotion: cbtEmotion,
        alternative: cbtAlternative,
      });
    } catch {
      // demo
    }
    setEngagementSubmitting(false);
    setCbtSituation("");
    setCbtThought("");
    setCbtEmotion("");
    setCbtAlternative("");
  }, [cbtSituation, cbtThought, cbtEmotion, cbtAlternative]);

  const toggleMindfulness = useCallback(() => {
    if (mindfulnessRunning) {
      setMindfulnessRunning(false);
      return;
    }
    setMindfulnessTimer(0);
    setMindfulnessRunning(true);
    const interval = setInterval(() => {
      setMindfulnessTimer((prev) => {
        if (prev >= 300) {
          clearInterval(interval);
          setMindfulnessRunning(false);
          return 300;
        }
        return prev + 1;
      });
    }, 1000);
  }, [mindfulnessRunning]);

  /* ─── Progress logic ──────────────────────────────────────────────────── */

  const filteredProgress = PROGRESS_DATA.filter((p) =>
    p.patient.toLowerCase().includes(progressSearch.toLowerCase())
  );

  const currentProgress = selectedPatientProgress
    ? PROGRESS_DATA.find((p) => p.patient === selectedPatientProgress)
    : null;

  /* ═══════════════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════════════ */

  const MOODS = [
    { emoji: "😞", label: "Very Low", value: 1 },
    { emoji: "😟", label: "Low", value: 2 },
    { emoji: "😐", label: "Neutral", value: 3 },
    { emoji: "🙂", label: "Good", value: 4 },
    { emoji: "😊", label: "Great", value: 5 },
  ];

  const TABS: { key: Tab; label: string }[] = [
    { key: "screenings", label: "Screenings" },
    { key: "crisis", label: "Crisis Management" },
    { key: "therapeutic", label: "Therapeutic Tools" },
    { key: "progress", label: "Patient Progress" },
  ];

  return (
    <div className="space-y-6">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in-up">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Mental Health &amp; Behavioral Care</h1>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-healthos-100 px-3 py-1 text-xs font-semibold text-healthos-700">
              <span className="h-2 w-2 rounded-full bg-healthos-500 animate-pulse" />
              {RECENT_SCREENINGS.length} Active Screenings
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Comprehensive screening, crisis intervention, therapeutic engagement, and longitudinal outcome tracking
          </p>
        </div>
        <button
          onClick={() => setShowNewScreening(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Screening
        </button>
      </div>

      {/* ── Stats Bar ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 animate-fade-in-up">
        {STATS.map((s, i) => (
          <div
            key={s.label}
            className="card card-hover text-center"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{s.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{s.value}</p>
            <p className={`mt-1 text-xs font-semibold ${s.label === "Crisis Alerts" ? (s.up ? "text-red-600" : "text-green-600") : s.up ? "text-green-600" : "text-green-600"}`}>
              {s.delta} vs last week
            </p>
          </div>
        ))}
      </div>

      {/* ── Crisis Resources Banner ────────────────────────────────────────── */}
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 animate-fade-in-up">
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-800">Crisis Resources Always Available</p>
            <p className="text-xs text-red-600">988 Suicide &amp; Crisis Lifeline &bull; Crisis Text Line: Text HOME to 741741 &bull; Emergency: 911</p>
          </div>
        </div>
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────────────── */}
      <div className="flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5 overflow-x-auto w-fit animate-fade-in-up">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
         TAB 1: SCREENINGS
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "screenings" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* New Screening Modal */}
          {showNewScreening && (
            <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4" onClick={() => setShowNewScreening(false)}>
              <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-gray-900 p-4 sm:p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">New Screening</h2>
                  <button onClick={() => setShowNewScreening(false)} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Patient</label>
                    <select
                      value={screeningPatient}
                      onChange={(e) => setScreeningPatient(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                    >
                      <option value="">Select patient...</option>
                      {PATIENT_LIST.map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Choose a screening tool below to begin:</p>
                  <div className="grid gap-2">
                    {SCREENING_TOOLS.map((tool) => (
                      <button
                        key={tool.id}
                        onClick={() => { setShowNewScreening(false); startScreening(tool.id); }}
                        disabled={!screeningPatient}
                        className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
                      >
                        <span className={`h-3 w-3 rounded-full ${tool.color}`} />
                        <div>
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{tool.name}</span>
                          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">({tool.category})</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Active Questionnaire */}
          {activeScreening && !screeningResult && (
            <div className="card border-2 border-healthos-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {activeScreening === "phq9" ? "PHQ-9" : activeScreening === "gad7" ? "GAD-7" : "AUDIT-C"} Screening
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Patient: {screeningPatient}</p>
                </div>
                <button
                  onClick={() => { setActiveScreening(null); setScreeningAnswers([]); }}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-600"
                >
                  Cancel
                </button>
              </div>
              {activeScreening !== "auditc" && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  Over the last 2 weeks, how often have you been bothered by the following problems?
                  <br />0 = Not at all &bull; 1 = Several days &bull; 2 = More than half the days &bull; 3 = Nearly every day
                </p>
              )}
              <div className="space-y-4">
                {questionsFor(activeScreening).map((q, qi) => (
                  <div key={qi} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
                      {qi + 1}. {q}
                    </p>
                    <div className="flex gap-2">
                      {(activeScreening === "auditc" ? [0, 1, 2, 3, 4] : [0, 1, 2, 3]).map((val) => (
                        <button
                          key={val}
                          onClick={() => handleAnswerChange(qi, val)}
                          className={`h-9 w-9 rounded-lg text-sm font-medium transition-colors ${
                            screeningAnswers[qi] === val
                              ? "bg-healthos-600 text-white shadow-sm"
                              : "bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-healthos-400"
                          }`}
                        >
                          {val}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex items-center justify-between">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Answered: {screeningAnswers.filter((a) => a >= 0).length} / {screeningAnswers.length}
                </p>
                <button
                  onClick={submitScreening}
                  disabled={screeningAnswers.some((a) => a < 0) || screeningSubmitting}
                  className="rounded-lg bg-healthos-600 px-6 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                >
                  {screeningSubmitting ? "Submitting..." : "Submit Screening"}
                </button>
              </div>
            </div>
          )}

          {/* Screening Result */}
          {screeningResult && (
            <div className="card border-2 border-healthos-200 animate-fade-in-up">
              <div className="text-center py-4">
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Screening Complete</h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{screeningResult.tool} for {screeningPatient}</p>
                <div className="mt-4">
                  <span className="text-2xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100">{screeningResult.score}</span>
                  <span className={`ml-3 inline-block rounded-full px-3 py-1 text-sm font-medium ${severityFromScore(screeningResult.tool, screeningResult.score).color}`}>
                    {severityFromScore(screeningResult.tool, screeningResult.score).label}
                  </span>
                </div>
                <button
                  onClick={() => { setActiveScreening(null); setScreeningResult(null); setScreeningAnswers([]); }}
                  className="mt-4 rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700"
                >
                  Done
                </button>
              </div>
            </div>
          )}

          {/* Screening Tool Cards */}
          {!activeScreening && !screeningResult && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Screening Tools</h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  {SCREENING_TOOLS.map((tool) => (
                    <div key={tool.id} className="card card-hover">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`h-3 w-3 rounded-full ${tool.color}`} />
                        <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">{tool.name}</h4>
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tool.bgLight} ${tool.textColor}`}>
                          {tool.category}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">{tool.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500 dark:text-gray-400">{tool.questions} questions</span>
                        <button
                          onClick={() => startScreening(tool.id)}
                          className="rounded-lg bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700 transition-colors"
                        >
                          Start Screening
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Results Table */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Recent Screening Results</h3>
                <div className="card overflow-hidden p-0">
                  <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 dark:border-gray-800 bg-gray-50/50">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400">Patient</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400">Tool</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400">Score</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400">Severity</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400">Date</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400">Trend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {RECENT_SCREENINGS.map((s) => {
                        const sev = severityFromScore(s.tool, s.score);
                        return (
                          <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                            <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{s.patient}</td>
                            <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{s.tool}</td>
                            <td className="px-4 py-3 font-semibold text-gray-900 dark:text-gray-100">{s.score}</td>
                            <td className="px-4 py-3">
                              <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${sev.color}`}>
                                {sev.label}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{s.date}</td>
                            <td className="px-4 py-3">{trendArrow(s.trend)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table></div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
         TAB 2: CRISIS MANAGEMENT
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "crisis" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Crisis Assessment Panel */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Crisis Assessment</h3>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient</label>
                <select
                  value={crisisPatient}
                  onChange={(e) => setCrisisPatient(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Select patient...</option>
                  {PATIENT_LIST.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-4">
                {/* Risk level indicator */}
                <div className="flex flex-col items-center gap-1">
                  <div className={`h-16 w-16 rounded-full ${riskCircleColor(crisisRisk)} ${crisisRisk === "critical" ? "animate-pulse" : ""} flex items-center justify-center shadow-lg`}>
                    <span className="text-xs font-bold text-white uppercase">{crisisRisk}</span>
                  </div>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400">Risk Level</span>
                </div>
                <button
                  onClick={assessCrisis}
                  disabled={!crisisPatient || crisisAssessing}
                  className="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {crisisAssessing ? "Assessing..." : "Assess Risk"}
                </button>
                <button
                  onClick={() => setShowSafetyPlan(true)}
                  disabled={!crisisPatient}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
                >
                  Create Safety Plan
                </button>
              </div>
            </div>
          </div>

          {/* Safety Plan Form */}
          {showSafetyPlan && (
            <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4" onClick={() => setShowSafetyPlan(false)}>
              <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-900 p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Create Safety Plan</h2>
                  <button onClick={() => setShowSafetyPlan(false)} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">Patient: {crisisPatient || "Not selected"}</p>
                <div className="space-y-4">
                  {([
                    { key: "warningSigns", label: "Warning Signs", placeholder: "What thoughts, moods, situations, or behaviors indicate a crisis may be developing?" },
                    { key: "copingStrategies", label: "Coping Strategies", placeholder: "Things I can do to take my mind off my problems without contacting another person..." },
                    { key: "supportContacts", label: "People I Can Contact for Support", placeholder: "Name and phone number of people who can help distract me..." },
                    { key: "professionalContacts", label: "Professional Contacts", placeholder: "Therapist, psychiatrist, crisis line numbers..." },
                    { key: "safeEnvironment", label: "Making the Environment Safe", placeholder: "Steps to remove or secure means..." },
                    { key: "reasonsForLiving", label: "Reasons for Living", placeholder: "The most important things to me that are worth living for..." },
                  ] as const).map((field) => (
                    <div key={field.key}>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{field.label}</label>
                      <textarea
                        value={safetyPlanData[field.key]}
                        onChange={(e) => setSafetyPlanData({ ...safetyPlanData, [field.key]: e.target.value })}
                        rows={2}
                        placeholder={field.placeholder}
                        className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                      />
                    </div>
                  ))}
                </div>
                <div className="mt-6 flex justify-end gap-3">
                  <button onClick={() => setShowSafetyPlan(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
                    Cancel
                  </button>
                  <button
                    onClick={submitSafetyPlan}
                    disabled={safetyPlanSubmitting}
                    className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50"
                  >
                    {safetyPlanSubmitting ? "Saving..." : "Save Safety Plan"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Active Crisis Cases */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Active Crisis Cases</h3>
            <div className="space-y-4">
              {CRISIS_CASES.map((c) => (
                <div
                  key={c.id}
                  className={`card border-2 ${riskBorderColor(c.riskLevel)} ${c.riskLevel === "critical" ? "animate-pulse" : ""}`}
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`h-10 w-10 rounded-full ${riskCircleColor(c.riskLevel)} ${c.riskLevel === "critical" ? "animate-pulse" : ""} flex items-center justify-center shadow-md`}>
                          <span className="text-[11px] font-bold text-white uppercase">{c.riskLevel}</span>
                        </div>
                        <div>
                          <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{c.patient}</span>
                          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">Age {c.age}</span>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Assigned to: {c.assignedTo}</p>
                        </div>
                      </div>

                      <div className="mb-2">
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Risk Factors:</p>
                        <div className="flex flex-wrap gap-1">
                          {c.riskFactors.map((f, i) => (
                            <span key={i} className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-medium text-red-700 border border-red-200">
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Recommended Actions:</p>
                        <ul className="space-y-0.5">
                          {c.recommendedActions.map((a, i) => (
                            <li key={i} className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                              <span className="h-1 w-1 rounded-full bg-gray-400" />
                              {a}
                            </li>
                          ))}
                        </ul>
                      </div>

                      <p className="mt-2 text-[11px] text-gray-500 dark:text-gray-400">Last assessment: {c.lastAssessment}</p>
                    </div>

                    <div className="flex flex-col gap-2 sm:items-end">
                      <button
                        onClick={() => resolveCrisis(c.id)}
                        className="rounded-lg bg-green-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-green-700 transition-colors"
                      >
                        Resolve
                      </button>
                      <button className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        Escalate
                      </button>
                      <button
                        onClick={() => { setCrisisPatient(c.patient); setShowSafetyPlan(true); }}
                        className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        Safety Plan
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
         TAB 3: THERAPEUTIC TOOLS
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "therapeutic" && (
        <div className="space-y-6 animate-fade-in-up">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Mood Check-in */}
            <div className="card card-hover">
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">Mood Check-in</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">How are you feeling right now?</p>
              <div className="flex justify-between mb-4">
                {MOODS.map((m) => (
                  <button
                    key={m.value}
                    onClick={() => setSelectedMood(m.value)}
                    className={`flex flex-col items-center gap-1 rounded-lg p-2 transition-all ${
                      selectedMood === m.value
                        ? "bg-healthos-100 ring-2 ring-healthos-400 scale-110"
                        : "hover:bg-gray-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    <span className="text-2xl">{m.emoji}</span>
                    <span className="text-[11px] text-gray-500 dark:text-gray-400">{m.label}</span>
                  </button>
                ))}
              </div>
              <textarea
                value={moodNote}
                onChange={(e) => setMoodNote(e.target.value)}
                rows={2}
                placeholder="Optional note about how you are feeling..."
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500 mb-3"
              />
              <button
                onClick={submitMoodCheckin}
                disabled={selectedMood === null || engagementSubmitting}
                className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
              >
                Submit Check-in
              </button>
            </div>

            {/* CBT Exercise */}
            <div className="card card-hover">
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">CBT Thought Record</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Challenge negative thinking patterns</p>
              <div className="space-y-2">
                <div>
                  <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-0.5">Situation</label>
                  <input
                    value={cbtSituation}
                    onChange={(e) => setCbtSituation(e.target.value)}
                    placeholder="What happened?"
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-0.5">Automatic Thought</label>
                  <input
                    value={cbtThought}
                    onChange={(e) => setCbtThought(e.target.value)}
                    placeholder="What went through your mind?"
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-0.5">Emotion</label>
                  <input
                    value={cbtEmotion}
                    onChange={(e) => setCbtEmotion(e.target.value)}
                    placeholder="What did you feel? (0-100%)"
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-0.5">Alternative Thought</label>
                  <input
                    value={cbtAlternative}
                    onChange={(e) => setCbtAlternative(e.target.value)}
                    placeholder="A more balanced perspective..."
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
              </div>
              <button
                onClick={submitCBT}
                disabled={!cbtSituation || !cbtThought || engagementSubmitting}
                className="mt-3 w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
              >
                Submit Thought Record
              </button>
            </div>

            {/* Mindfulness */}
            <div className="card card-hover">
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">Mindfulness Session</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">5-minute guided breathing exercise</p>
              <div className="flex flex-col items-center py-4">
                <div className={`h-28 w-28 rounded-full flex items-center justify-center mb-4 transition-all ${
                  mindfulnessRunning
                    ? "bg-healthos-100 ring-4 ring-healthos-300 animate-pulse"
                    : "bg-gray-100 dark:bg-gray-800"
                }`}>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {Math.floor(mindfulnessTimer / 60)}:{String(mindfulnessTimer % 60).padStart(2, "0")}
                    </p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400">
                      {mindfulnessRunning ? "Breathe..." : "Ready"}
                    </p>
                  </div>
                </div>
                {mindfulnessRunning && (
                  <p className="text-xs text-healthos-600 mb-3 animate-pulse">
                    Inhale slowly... hold... exhale...
                  </p>
                )}
                <div className="w-full bg-gray-200 rounded-full h-1.5 mb-4">
                  <div
                    className="bg-healthos-500 h-1.5 rounded-full transition-all"
                    style={{ width: `${(mindfulnessTimer / 300) * 100}%` }}
                  />
                </div>
              </div>
              <button
                onClick={toggleMindfulness}
                className={`w-full rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  mindfulnessRunning
                    ? "bg-red-600 text-white hover:bg-red-700"
                    : "bg-healthos-600 text-white hover:bg-healthos-700"
                }`}
              >
                {mindfulnessRunning ? "Stop Session" : "Start Session"}
              </button>
            </div>
          </div>

          {/* Patient Progress Timeline */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Patient Engagement Timeline</h3>
            <div className="card p-0 overflow-hidden">
              <div className="divide-y divide-gray-100">
                {[
                  { time: "9:15 AM", patient: "Emily Davis", type: "CBT", activity: "Completed Thought Record", status: "completed" },
                  { time: "10:00 AM", patient: "Anna Rodriguez", type: "Mood", activity: "Mood check-in: Low (2/5)", status: "completed" },
                  { time: "10:30 AM", patient: "Anna Rodriguez", type: "Mindfulness", activity: "4-7-8 Breathing — In Progress", status: "in_progress" },
                  { time: "11:00 AM", patient: "Michael Brown", type: "CBT", activity: "Behavioral Activation scheduled", status: "pending" },
                  { time: "2:00 PM", patient: "Emily Davis", type: "Mindfulness", activity: "Body Scan scheduled", status: "pending" },
                ].map((e, i) => (
                  <div key={i} className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50/50 transition-colors">
                    <span className="text-xs text-gray-500 dark:text-gray-400 w-16 shrink-0">{e.time}</span>
                    <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                      e.status === "completed" ? "bg-green-400" : e.status === "in_progress" ? "bg-yellow-400 animate-pulse" : "bg-gray-300"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{e.patient}</span>
                      <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">{e.activity}</span>
                    </div>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                      e.type === "CBT" ? "bg-purple-50 text-purple-700"
                        : e.type === "Mood" ? "bg-blue-50 text-blue-700"
                        : "bg-green-50 text-green-700"
                    }`}>
                      {e.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
         TAB 4: PATIENT PROGRESS
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "progress" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Search */}
          <div className="card">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Search Patient</label>
                <input
                  value={progressSearch}
                  onChange={(e) => setProgressSearch(e.target.value)}
                  placeholder="Type patient name..."
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
            </div>
            {filteredProgress.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {filteredProgress.map((p) => (
                  <button
                    key={p.patient}
                    onClick={() => setSelectedPatientProgress(p.patient)}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                      selectedPatientProgress === p.patient
                        ? "bg-healthos-600 text-white"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200"
                    }`}
                  >
                    {p.patient}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Longitudinal View */}
          {currentProgress && (
            <div className="space-y-4">
              {/* Score Trends */}
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                  Screening Score Trends &mdash; {currentProgress.patient}
                </h3>
                <div className="space-y-3">
                  {currentProgress.screenings.map((s, i) => {
                    const max = s.tool === "PHQ-9" ? 27 : s.tool === "GAD-7" ? 21 : 12;
                    return (
                      <div key={i} className="flex items-center gap-3">
                        <span className="w-10 text-xs font-medium text-gray-500 dark:text-gray-400">{s.date}</span>
                        <span className="w-14 text-xs text-gray-500 dark:text-gray-400">{s.tool}</span>
                        <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${barColor(s.score, max)} flex items-center justify-end pr-2 transition-all`}
                            style={{ width: barWidth(s.score, max) }}
                          >
                            <span className="text-[11px] font-bold text-white">{s.score}</span>
                          </div>
                        </div>
                        <span className={`w-20 text-right rounded-full px-2 py-0.5 text-[11px] font-medium ${severityFromScore(s.tool, s.score).color}`}>
                          {severityFromScore(s.tool, s.score).label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Engagement Metrics */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {[
                  { label: "Daily Check-ins", value: currentProgress.engagement.checkins },
                  { label: "Exercise Completion", value: currentProgress.engagement.exercises },
                  { label: "Session Attendance", value: currentProgress.engagement.attendance },
                ].map((metric) => (
                  <div key={metric.label} className="card card-hover text-center">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{metric.label}</p>
                    <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{metric.value}%</p>
                    <div className="mt-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2">
                      <div
                        className={`h-full rounded-full ${metric.value >= 80 ? "bg-green-500" : metric.value >= 60 ? "bg-yellow-500" : "bg-red-500"}`}
                        style={{ width: `${metric.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Treatment Plan Adherence */}
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Treatment Plan Adherence</h3>
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${
                    currentProgress.adherence >= 80 ? "bg-green-100 text-green-700"
                      : currentProgress.adherence >= 60 ? "bg-yellow-100 text-yellow-700"
                      : "bg-red-100 text-red-700"
                  }`}>
                    {currentProgress.adherence}%
                  </span>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-4 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      currentProgress.adherence >= 80 ? "bg-green-500"
                        : currentProgress.adherence >= 60 ? "bg-yellow-500"
                        : "bg-red-500"
                    }`}
                    style={{ width: `${currentProgress.adherence}%` }}
                  />
                </div>
              </div>

              {/* Therapist Notes */}
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Therapist Notes</h3>
                <div className="space-y-3 mb-4">
                  {currentProgress.notes.map((note, i) => (
                    <div key={i} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{note.author}</span>
                        <span className="text-[11px] text-gray-500 dark:text-gray-400">{note.date}</span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{note.text}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add a note..."
                    className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                  <button
                    onClick={() => setNewNote("")}
                    disabled={!newNote}
                    className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                  >
                    Add Note
                  </button>
                </div>
              </div>
            </div>
          )}

          {!selectedPatientProgress && (
            <div className="card text-center py-6 sm:py-12">
              <p className="text-gray-500 dark:text-gray-400 text-sm">Select a patient above to view their longitudinal progress</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
