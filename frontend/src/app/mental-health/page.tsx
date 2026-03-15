"use client";

import { useState, useCallback } from "react";
import { submitPHQ9Screening, submitGAD7Screening, detectCrisis, createSafetyPlan, submitTherapeuticEngagement } from "@/lib/api";

const SCREENING_QUEUE = [
  { id: "MH-001", patient: "Emily Davis", age: 34, type: "PHQ-9 + GAD-7", due: "Today", lastScreen: "2026-02-10", priority: "high" },
  { id: "MH-002", patient: "Michael Brown", age: 52, type: "PHQ-9", due: "Today", lastScreen: "2026-01-28", priority: "medium" },
  { id: "MH-003", patient: "Lisa Park", age: 28, type: "Comprehensive", due: "Tomorrow", lastScreen: "2026-02-20", priority: "high" },
  { id: "MH-004", patient: "David Wilson", age: 45, type: "AUDIT-C", due: "Mar 14", lastScreen: "2025-12-15", priority: "low" },
  { id: "MH-005", patient: "Anna Rodriguez", age: 19, type: "PHQ-9 + GAD-7", due: "Today", lastScreen: "2026-03-01", priority: "high" },
];

const ACTIVE_CASES = [
  {
    id: "BH-101",
    patient: "Emily Davis",
    diagnosis: "Major Depressive Disorder",
    phq9: 16,
    gad7: 12,
    provider: "Dr. Sarah Kim, PsyD",
    modality: "CBT — Telehealth",
    sessions: 8,
    nextSession: "2026-03-14",
    trend: "improving",
    riskLevel: "moderate",
  },
  {
    id: "BH-102",
    patient: "Anna Rodriguez",
    diagnosis: "Generalized Anxiety Disorder",
    phq9: 9,
    gad7: 18,
    provider: "Dr. James Lee, MD",
    modality: "CBT + Medication",
    sessions: 4,
    nextSession: "2026-03-13",
    trend: "stable",
    riskLevel: "moderate",
  },
  {
    id: "BH-103",
    patient: "Michael Brown",
    diagnosis: "PTSD",
    phq9: 14,
    gad7: 15,
    provider: "Dr. Maria Gonzalez, LCSW",
    modality: "EMDR — In Person",
    sessions: 12,
    nextSession: "2026-03-15",
    trend: "improving",
    riskLevel: "low",
  },
];

const ENGAGEMENT_STATS = [
  { label: "Daily Check-ins (7d)", value: "82%", trend: "+5%" },
  { label: "CBT Exercise Completion", value: "68%", trend: "+3%" },
  { label: "Session Attendance", value: "94%", trend: "+1%" },
  { label: "Crisis Alerts (30d)", value: "2", trend: "-3" },
];

const phq9Severity = (score: number) =>
  score >= 20 ? { label: "Severe", color: "bg-red-100 text-red-700" } :
  score >= 15 ? { label: "Mod. Severe", color: "bg-orange-100 text-orange-700" } :
  score >= 10 ? { label: "Moderate", color: "bg-yellow-100 text-yellow-700" } :
  score >= 5 ? { label: "Mild", color: "bg-green-100 text-green-700" } :
  { label: "Minimal", color: "bg-gray-100 text-gray-600" };

const gad7Severity = (score: number) =>
  score >= 15 ? { label: "Severe", color: "bg-red-100 text-red-700" } :
  score >= 10 ? { label: "Moderate", color: "bg-yellow-100 text-yellow-700" } :
  score >= 5 ? { label: "Mild", color: "bg-green-100 text-green-700" } :
  { label: "Minimal", color: "bg-gray-100 text-gray-600" };

const riskColor = (r: string) =>
  r === "high" || r === "imminent" ? "bg-red-100 text-red-700" :
  r === "moderate" ? "bg-yellow-100 text-yellow-700" :
  "bg-green-100 text-green-700";

const priorityColor = (p: string) =>
  p === "high" ? "bg-red-50 text-red-700" : p === "medium" ? "bg-yellow-50 text-yellow-700" : "bg-gray-100 text-gray-600";

export default function MentalHealthPage() {
  const [tab, setTab] = useState<"screening" | "cases" | "engagement">("screening");
  const [showNewScreen, setShowNewScreen] = useState(false);
  const [screenForm, setScreenForm] = useState({ patient: "", type: "PHQ-9 + GAD-7" });
  const [submittingScreen, setSubmittingScreen] = useState(false);
  const [showCrisisProtocol, setShowCrisisProtocol] = useState(false);

  const handleNewScreen = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingScreen(true);
    try {
      if (screenForm.type.includes("PHQ-9")) await submitPHQ9Screening({ patient_name: screenForm.patient });
      if (screenForm.type.includes("GAD-7")) await submitGAD7Screening({ patient_name: screenForm.patient });
      setShowNewScreen(false);
      setScreenForm({ patient: "", type: "PHQ-9 + GAD-7" });
    } catch { /* silently handle */ }
    finally { setSubmittingScreen(false); }
  };

  const handleCrisisDetect = useCallback(async (patientId: string) => {
    try { await detectCrisis({ patient_id: patientId, action: "assess" }); } catch { /* demo mode */ }
  }, []);

  const handleStartScreen = useCallback(async (patientId: string, type: string) => {
    try {
      if (type.includes("PHQ-9")) await submitPHQ9Screening({ patient_id: patientId });
      if (type.includes("GAD-7")) await submitGAD7Screening({ patient_id: patientId });
    } catch {
      // API unavailable — demo mode
    }
  }, []);

  const handleSafetyPlan = useCallback(async (patientId: string) => {
    try {
      await createSafetyPlan({ patient_id: patientId });
    } catch {
      // API unavailable — demo mode
    }
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mental Health</h1>
          <p className="text-sm text-gray-500">Screening, behavioral health workflows, crisis detection, and therapeutic engagement</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowCrisisProtocol(!showCrisisProtocol)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            Crisis Protocol
          </button>
          <button onClick={() => setShowNewScreen(true)} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
            New Screening
          </button>
        </div>
      </div>

      {/* Crisis Protocol Panel */}
      {showCrisisProtocol && (
        <div className="rounded-lg border-2 border-red-300 bg-red-50 p-6 animate-fade-in">
          <h3 className="text-sm font-bold text-red-900 mb-3">Crisis Intervention Protocol</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {ACTIVE_CASES.map((c) => (
              <div key={c.id} className="rounded-lg bg-white p-3 border border-red-200">
                <p className="text-sm font-semibold text-gray-900">{c.patient}</p>
                <p className="text-xs text-gray-500">{c.diagnosis}</p>
                <button onClick={() => handleCrisisDetect(c.id)} className="mt-2 w-full rounded bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700">Assess Crisis Risk</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New Screening Modal */}
      {showNewScreen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowNewScreen(false)}>
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">New Screening</h2>
              <button onClick={() => setShowNewScreen(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleNewScreen} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Patient Name *</label>
                <input required value={screenForm.patient} onChange={(e) => setScreenForm({ ...screenForm, patient: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Emily Davis" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Screening Type *</label>
                <select required value={screenForm.type} onChange={(e) => setScreenForm({ ...screenForm, type: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                  <option value="PHQ-9 + GAD-7">PHQ-9 + GAD-7 (Comprehensive)</option>
                  <option value="PHQ-9">PHQ-9 (Depression)</option>
                  <option value="GAD-7">GAD-7 (Anxiety)</option>
                  <option value="AUDIT-C">AUDIT-C (Alcohol Use)</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowNewScreen(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={submittingScreen} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50">{submittingScreen ? "Starting..." : "Start Screening"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {ENGAGEMENT_STATS.map((s) => (
          <div key={s.label} className="card text-center">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{s.value}</p>
            <p className={`mt-1 text-xs font-medium ${s.trend.startsWith("+") || s.trend.startsWith("-3") ? "text-green-600" : "text-gray-500"}`}>
              {s.trend} vs last period
            </p>
          </div>
        ))}
      </div>

      {/* Crisis Banner */}
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-red-100 text-red-600">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-800">Crisis Resources Always Available</p>
            <p className="text-xs text-red-600">988 Suicide & Crisis Lifeline | Crisis Text Line: Text HOME to 741741 | Emergency: 911</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5 w-fit">
        {(["screening", "cases", "engagement"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize ${
              tab === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
            }`}
          >
            {t === "cases" ? "Active Cases" : t === "engagement" ? "Therapeutic Engagement" : "Screening Queue"}
          </button>
        ))}
      </div>

      {tab === "screening" && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-700">Pending Screenings</h3>
          {SCREENING_QUEUE.map((s) => (
            <div key={s.id} className="card flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${priorityColor(s.priority)}`}>
                  {s.priority}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">{s.patient}</span>
                    <span className="text-xs text-gray-400">Age {s.age}</span>
                  </div>
                  <div className="mt-0.5 flex gap-3 text-xs text-gray-500">
                    <span>Type: {s.type}</span>
                    <span>Due: {s.due}</span>
                    <span>Last: {s.lastScreen}</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => handleStartScreen(s.id, s.type)} className="rounded bg-healthos-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-healthos-700">
                  Start Screen
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "cases" && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-700">Active Behavioral Health Cases</h3>
          {ACTIVE_CASES.map((c) => (
            <div key={c.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">{c.patient}</span>
                    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${riskColor(c.riskLevel)}`}>
                      {c.riskLevel} risk
                    </span>
                    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                      c.trend === "improving" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-600"
                    }`}>{c.trend}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-600">{c.diagnosis} — {c.modality}</p>
                  <p className="mt-0.5 text-xs text-gray-400">Provider: {c.provider} | Sessions: {c.sessions} | Next: {c.nextSession}</p>

                  <div className="mt-3 flex gap-4">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">PHQ-9:</span>
                      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${phq9Severity(c.phq9).color}`}>
                        {c.phq9} — {phq9Severity(c.phq9).label}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">GAD-7:</span>
                      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${gad7Severity(c.gad7).color}`}>
                        {c.gad7} — {gad7Severity(c.gad7).label}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <button className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">Treatment Plan</button>
                  <button onClick={() => handleSafetyPlan(c.id)} className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">Safety Plan</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "engagement" && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Today's Exercises */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Today&apos;s Therapeutic Exercises</h3>
            <div className="space-y-3">
              {[
                { type: "CBT", name: "Thought Record", patient: "Emily Davis", status: "completed", time: "9:15 AM" },
                { type: "Mindfulness", name: "4-7-8 Breathing", patient: "Anna Rodriguez", status: "in_progress", time: "10:30 AM" },
                { type: "CBT", name: "Behavioral Activation", patient: "Michael Brown", status: "pending", time: "2:00 PM" },
                { type: "Mindfulness", name: "Body Scan", patient: "Emily Davis", status: "pending", time: "4:00 PM" },
              ].map((e, i) => (
                <div key={i} className="card flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`h-2 w-2 rounded-full ${
                      e.status === "completed" ? "bg-green-400" : e.status === "in_progress" ? "bg-yellow-400" : "bg-gray-300"
                    }`} />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">{e.name}</span>
                        <span className="rounded bg-healthos-50 px-1.5 py-0.5 text-[10px] text-healthos-700">{e.type}</span>
                      </div>
                      <p className="text-xs text-gray-500">{e.patient} — {e.time}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-medium ${
                    e.status === "completed" ? "text-green-600" : e.status === "in_progress" ? "text-yellow-600" : "text-gray-400"
                  }`}>{e.status.replace("_", " ")}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Mood Check-ins */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Recent Mood Check-ins</h3>
            <div className="space-y-3">
              {[
                { patient: "Emily Davis", mood: 6, sleep: 7, energy: 5, anxiety: 4, time: "8:30 AM" },
                { patient: "Anna Rodriguez", mood: 4, sleep: 4, energy: 3, anxiety: 8, time: "7:45 AM" },
                { patient: "Michael Brown", mood: 5, sleep: 6, energy: 5, anxiety: 6, time: "9:00 AM" },
              ].map((m, i) => (
                <div key={i} className="card">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{m.patient}</span>
                    <span className="text-xs text-gray-400">{m.time}</span>
                  </div>
                  <div className="mt-2 grid grid-cols-4 gap-2">
                    {[
                      { label: "Mood", value: m.mood },
                      { label: "Sleep", value: m.sleep },
                      { label: "Energy", value: m.energy },
                      { label: "Anxiety", value: m.anxiety },
                    ].map((metric) => (
                      <div key={metric.label} className="text-center">
                        <div className={`text-lg font-bold ${
                          metric.label === "Anxiety"
                            ? (metric.value <= 3 ? "text-green-600" : metric.value <= 6 ? "text-yellow-600" : "text-red-600")
                            : (metric.value >= 7 ? "text-green-600" : metric.value >= 4 ? "text-yellow-600" : "text-red-600")
                        }`}>{metric.value}</div>
                        <div className="text-[10px] text-gray-500">{metric.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
