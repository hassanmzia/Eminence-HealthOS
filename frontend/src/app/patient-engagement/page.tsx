"use client";

import { useState, useCallback, useEffect } from "react";
import {
  triageSymptoms,
  navigateCare,
  screenSDOH,
  findCommunityResources,
  submitMotivationalEngagement,
} from "@/lib/api";

/* ─── Constants ──────────────────────────────────────────────────────────── */

const TABS = ["Symptom Triage", "Care Navigation", "Community Resources", "Engagement & Nudges"] as const;
type Tab = (typeof TABS)[number];

const SYMPTOM_OPTIONS = [
  "Headache", "Chest Pain", "Shortness of Breath", "Abdominal Pain", "Fever",
  "Cough", "Fatigue", "Dizziness", "Nausea", "Back Pain", "Joint Pain",
  "Sore Throat", "Rash", "Palpitations", "Numbness/Tingling",
];

const ASSOCIATED_FACTORS = [
  "Recent travel", "Known allergies", "Chronic condition", "Medication change",
  "Recent surgery", "Pregnancy", "Immunocompromised", "Smoker",
];

const NEED_OPTIONS = ["housing", "food", "transportation", "financial", "mental health"] as const;

const NUDGE_TYPES = ["appointment reminder", "medication", "wellness tip", "follow-up"] as const;
const NUDGE_CHANNELS = ["SMS", "email", "push"] as const;

/* ─── Demo / Fallback Data ───────────────────────────────────────────────── */

const DEMO_TRIAGE_HISTORY = [
  { id: "TRG-001", patient: "Maria Garcia", symptoms: ["Headache", "Dizziness"], severity: 6, urgency: "semi-urgent" as const, venue: "Urgent Care", date: "2026-03-14", followUp: ["Schedule within 24-48h", "Monitor for vision changes"] },
  { id: "TRG-002", patient: "James Wilson", symptoms: ["Chest Pain", "Shortness of Breath"], severity: 9, urgency: "emergency" as const, venue: "Emergency Room", date: "2026-03-14", followUp: ["Call 911 immediately", "Chew aspirin if available"] },
  { id: "TRG-003", patient: "Emily Davis", symptoms: ["Cough", "Sore Throat", "Fever"], severity: 3, urgency: "non-urgent" as const, venue: "Telehealth Visit", date: "2026-03-13", followUp: ["Rest and fluids", "OTC medications"] },
  { id: "TRG-004", patient: "Robert Johnson", symptoms: ["Back Pain"], severity: 4, urgency: "non-urgent" as const, venue: "Primary Care", date: "2026-03-13", followUp: ["Schedule routine appointment", "Apply ice/heat"] },
  { id: "TRG-005", patient: "Sarah Chen", symptoms: ["Palpitations", "Fatigue"], severity: 7, urgency: "urgent" as const, venue: "Cardiology Clinic", date: "2026-03-12", followUp: ["See cardiologist within 24h", "Avoid caffeine"] },
];

const DEMO_JOURNEYS = [
  { id: "JRN-001", patient: "Maria Garcia", patientId: "P-1001", name: "Diabetes Management", steps: ["Intake", "Lab Work", "Education", "Care Plan", "Follow-up", "Review"], currentStep: 2, navigator: "Dr. Sarah Kim", progress: 50, nextActions: ["Complete diabetes education class", "Schedule A1C recheck"], goals: ["Reduce A1C below 7%", "Daily glucose monitoring"] },
  { id: "JRN-002", patient: "James Wilson", patientId: "P-1002", name: "Cardiac Rehab", steps: ["Assessment", "Stress Test", "Exercise Plan", "Nutrition", "Monitoring", "Graduation", "Maintenance", "Review"], currentStep: 1, navigator: "Nurse Patel", progress: 25, nextActions: ["Complete stress test", "Start phase 1 exercises"], goals: ["Improve cardiac output", "Return to normal activity"] },
  { id: "JRN-003", patient: "Sarah Chen", patientId: "P-1003", name: "Surgical Preparation", steps: ["Consultation", "Pre-op Labs", "Imaging", "Pre-op Teaching", "Surgery", "Recovery"], currentStep: 3, navigator: "Dr. Adams", progress: 67, nextActions: ["Attend pre-op teaching session", "Stop blood thinners"], goals: ["Successful knee replacement", "Minimize complications"] },
  { id: "JRN-004", patient: "Robert Johnson", patientId: "P-1004", name: "Cancer Screening", steps: ["Risk Assessment", "Genetic Counseling", "Screening Tests", "Results Review", "Follow-up Plan"], currentStep: 2, navigator: "Nurse Thompson", progress: 60, nextActions: ["Review colonoscopy results", "Schedule follow-up"], goals: ["Complete age-appropriate screenings", "Early detection"] },
];

const DEMO_RESOURCES = [
  { id: "R-001", name: "Community Food Bank of Metro", type: "food", distance: "1.2 mi", phone: "(555) 234-5678", address: "450 Main St, Suite 100", services: ["Emergency food boxes", "Weekly produce distribution", "SNAP enrollment assistance", "Nutrition education"], hours: "Mon-Fri 9am-5pm" },
  { id: "R-002", name: "Safe Harbor Housing", type: "housing", distance: "2.5 mi", phone: "(555) 345-6789", address: "1200 Oak Avenue", services: ["Emergency shelter", "Transitional housing", "Rental assistance", "Housing counseling"], hours: "24/7 intake" },
  { id: "R-003", name: "MedRide Transportation", type: "transportation", distance: "0.8 mi", phone: "(555) 456-7890", address: "78 Transit Way", services: ["Medical appointment rides", "Wheelchair accessible", "Dialysis transport", "Pharmacy trips"], hours: "Mon-Sat 6am-10pm" },
  { id: "R-004", name: "Financial Wellness Center", type: "financial", distance: "3.1 mi", phone: "(555) 567-8901", address: "890 Commerce Blvd", services: ["Medical bill assistance", "Insurance navigation", "Prescription savings", "Benefits enrollment"], hours: "Mon-Fri 8am-6pm" },
  { id: "R-005", name: "Mindful Health Counseling", type: "mental health", distance: "1.8 mi", phone: "(555) 678-9012", address: "321 Wellness Dr, Suite 200", services: ["Individual therapy", "Group counseling", "Crisis intervention", "Substance abuse support"], hours: "Mon-Sat 8am-8pm" },
];

const DEMO_NUDGE_HISTORY = [
  { id: "N-001", patient: "Maria Garcia", type: "medication", channel: "SMS", message: "Time for your evening insulin — you've kept your streak going 12 days!", status: "delivered" as const, sentAt: "2026-03-15 08:30", openedAt: "2026-03-15 08:32" },
  { id: "N-002", patient: "James Wilson", type: "appointment reminder", channel: "email", message: "Your cardiac rehab session is tomorrow at 10am with Dr. Patel.", status: "delivered" as const, sentAt: "2026-03-15 07:00", openedAt: "2026-03-15 09:15" },
  { id: "N-003", patient: "Sarah Chen", type: "wellness tip", channel: "push", message: "Great job walking 8,000 steps today! Try for 8,500 tomorrow.", status: "delivered" as const, sentAt: "2026-03-14 18:00", openedAt: "2026-03-14 18:05" },
  { id: "N-004", patient: "Emily Davis", type: "follow-up", channel: "SMS", message: "How are you feeling after your visit? Reply 1-5 to rate.", status: "pending" as const, sentAt: "2026-03-14 14:00", openedAt: null },
  { id: "N-005", patient: "Robert Johnson", type: "medication", channel: "email", message: "Your prescription refill is ready for pickup at Walgreens.", status: "failed" as const, sentAt: "2026-03-14 10:00", openedAt: null },
];

const DEMO_ENGAGEMENT_SCORES = [
  { patient: "Maria Garcia", score: 82, trend: "up" as const, weeklyScores: [74, 76, 78, 79, 80, 81, 82] },
  { patient: "James Wilson", score: 65, trend: "down" as const, weeklyScores: [72, 70, 69, 68, 67, 66, 65] },
  { patient: "Sarah Chen", score: 91, trend: "up" as const, weeklyScores: [85, 86, 87, 88, 89, 90, 91] },
  { patient: "Emily Davis", score: 54, trend: "down" as const, weeklyScores: [62, 60, 58, 57, 56, 55, 54] },
  { patient: "Robert Johnson", score: 73, trend: "up" as const, weeklyScores: [66, 68, 69, 70, 71, 72, 73] },
];

/* ─── Helpers ────────────────────────────────────────────────────────────── */

type Urgency = "emergency" | "urgent" | "semi-urgent" | "non-urgent";

function urgencyStyle(u: Urgency) {
  const map: Record<Urgency, string> = {
    emergency: "bg-red-100 text-red-800 border-red-300",
    urgent: "bg-orange-100 text-orange-800 border-orange-300",
    "semi-urgent": "bg-yellow-100 text-yellow-800 border-yellow-300",
    "non-urgent": "bg-green-100 text-green-800 border-green-300",
  };
  return map[u] ?? "bg-gray-100 text-gray-800 border-gray-300";
}

function urgencyDot(u: Urgency) {
  const map: Record<Urgency, string> = {
    emergency: "bg-red-500",
    urgent: "bg-orange-500",
    "semi-urgent": "bg-yellow-500",
    "non-urgent": "bg-green-500",
  };
  return map[u] ?? "bg-gray-500";
}

function needBadgeColor(need: string) {
  const map: Record<string, string> = {
    housing: "bg-purple-100 text-purple-800",
    food: "bg-emerald-100 text-emerald-800",
    transportation: "bg-blue-100 text-blue-800",
    financial: "bg-amber-100 text-amber-800",
    "mental health": "bg-pink-100 text-pink-800",
  };
  return map[need] ?? "bg-gray-100 text-gray-800";
}

function nudgeStatusStyle(s: string) {
  const map: Record<string, string> = {
    delivered: "bg-green-100 text-green-800",
    pending: "bg-yellow-100 text-yellow-800",
    failed: "bg-red-100 text-red-800",
  };
  return map[s] ?? "bg-gray-100 text-gray-800";
}

/* ─── Main Component ─────────────────────────────────────────────────────── */

export default function PatientEngagementPage() {
  const [tab, setTab] = useState<Tab>("Symptom Triage");

  /* -- Triage state -- */
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [severity, setSeverity] = useState(5);
  const [duration, setDuration] = useState("");
  const [associatedFactors, setAssociatedFactors] = useState<string[]>([]);
  const [triageResult, setTriageResult] = useState<{
    urgency: Urgency;
    venue: string;
    followUp: string[];
    selfCare: string[];
  } | null>(null);
  const [triageLoading, setTriageLoading] = useState(false);
  const [triageHistory, setTriageHistory] = useState(DEMO_TRIAGE_HISTORY);

  /* -- Care Navigation state -- */
  const [journeys, setJourneys] = useState(DEMO_JOURNEYS);
  const [showJourneyForm, setShowJourneyForm] = useState(false);
  const [journeyPatientId, setJourneyPatientId] = useState("");
  const [journeyType, setJourneyType] = useState("");
  const [journeyGoals, setJourneyGoals] = useState("");
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [selectedJourney, setSelectedJourney] = useState<string | null>(null);

  /* -- Community Resources state -- */
  const [selectedNeeds, setSelectedNeeds] = useState<string[]>([]);
  const [zipCode, setZipCode] = useState("90210");
  const [radius, setRadius] = useState(5);
  const [resources, setResources] = useState(DEMO_RESOURCES);
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [referralSent, setReferralSent] = useState<string | null>(null);

  /* -- Engagement & Nudges state -- */
  const [nudgePatient, setNudgePatient] = useState("");
  const [nudgeType, setNudgeType] = useState<(typeof NUDGE_TYPES)[number]>("appointment reminder");
  const [nudgeChannel, setNudgeChannel] = useState<(typeof NUDGE_CHANNELS)[number]>("SMS");
  const [nudgeMessage, setNudgeMessage] = useState("");
  const [nudgePersonalize, setNudgePersonalize] = useState(true);
  const [nudgeLoading, setNudgeLoading] = useState(false);
  const [nudgeHistory, setNudgeHistory] = useState(DEMO_NUDGE_HISTORY);
  const [engagementScores] = useState(DEMO_ENGAGEMENT_SCORES);

  /* -- KPI stats -- */
  const avgScore = Math.round(engagementScores.reduce((s, e) => s + e.score, 0) / engagementScores.length);

  /* ─── Triage Handler ───────────────────────────────────────────────────── */

  const handleTriage = useCallback(async () => {
    if (selectedSymptoms.length === 0) return;
    setTriageLoading(true);
    try {
      const res = await triageSymptoms({
        symptoms: selectedSymptoms,
        severity,
        duration,
        associated_factors: associatedFactors,
      });
      const data = res as Record<string, unknown>;
      setTriageResult({
        urgency: (data.urgency as Urgency) ?? "non-urgent",
        venue: (data.recommended_venue as string) ?? "Primary Care",
        followUp: (data.follow_up_actions as string[]) ?? [],
        selfCare: (data.self_care_instructions as string[]) ?? [],
      });
    } catch {
      // Fallback demo result based on severity
      const urgency: Urgency = severity >= 8 ? "emergency" : severity >= 6 ? "urgent" : severity >= 4 ? "semi-urgent" : "non-urgent";
      const venues: Record<Urgency, string> = { emergency: "Emergency Room", urgent: "Urgent Care", "semi-urgent": "Telehealth Visit", "non-urgent": "Primary Care" };
      setTriageResult({
        urgency,
        venue: venues[urgency],
        followUp: severity >= 8
          ? ["Seek immediate emergency care", "Call 911 if symptoms worsen", "Do not drive yourself"]
          : severity >= 6
          ? ["Schedule visit within 24 hours", "Monitor symptoms closely", "Keep a symptom diary"]
          : ["Schedule at your convenience", "Rest and stay hydrated", "Use OTC medications as needed"],
        selfCare: urgency === "non-urgent" || urgency === "semi-urgent"
          ? ["Rest and adequate sleep", "Stay hydrated — 8 glasses of water daily", "Over-the-counter pain relief as directed", "Apply warm/cold compress as appropriate"]
          : [],
      });
    } finally {
      setTriageLoading(false);
    }
  }, [selectedSymptoms, severity, duration, associatedFactors]);

  /* ─── Journey Creation Handler ─────────────────────────────────────────── */

  const handleCreateJourney = useCallback(async () => {
    if (!journeyPatientId || !journeyType) return;
    setJourneyLoading(true);
    try {
      await navigateCare({
        patient_id: journeyPatientId,
        journey_type: journeyType,
        goals: journeyGoals.split(",").map((g) => g.trim()).filter(Boolean),
      });
    } catch {
      // Fallback: add demo journey
    }
    const newJourney = {
      id: `JRN-${String(journeys.length + 1).padStart(3, "0")}`,
      patient: `Patient ${journeyPatientId}`,
      patientId: journeyPatientId,
      name: journeyType,
      steps: ["Intake", "Assessment", "Planning", "Intervention", "Follow-up", "Review"],
      currentStep: 0,
      navigator: "Unassigned",
      progress: 0,
      nextActions: ["Complete intake assessment"],
      goals: journeyGoals.split(",").map((g) => g.trim()).filter(Boolean),
    };
    setJourneys((prev) => [newJourney, ...prev]);
    setShowJourneyForm(false);
    setJourneyPatientId("");
    setJourneyType("");
    setJourneyGoals("");
    setJourneyLoading(false);
  }, [journeyPatientId, journeyType, journeyGoals, journeys.length]);

  /* ─── Resource Search Handler ──────────────────────────────────────────── */

  const handleSearchResources = useCallback(async () => {
    if (selectedNeeds.length === 0) return;
    setResourcesLoading(true);
    try {
      const res = await findCommunityResources({
        needs: selectedNeeds,
        zip_code: zipCode,
        radius_miles: radius,
      });
      const data = res as Record<string, unknown>;
      if (data.resources && Array.isArray(data.resources)) {
        setResources(
          (data.resources as Array<Record<string, unknown>>).map((r, i) => ({
            id: `R-${String(i + 1).padStart(3, "0")}`,
            name: (r.name as string) ?? "Unknown Resource",
            type: (r.type as string) ?? "general",
            distance: (r.distance as string) ?? "N/A",
            phone: (r.phone as string) ?? "N/A",
            address: (r.address as string) ?? "N/A",
            services: (r.services as string[]) ?? [],
            hours: (r.hours as string) ?? "Call for hours",
          }))
        );
      }
    } catch {
      // Filter demo resources by selected needs
      setResources(DEMO_RESOURCES.filter((r) => selectedNeeds.includes(r.type)));
    } finally {
      setResourcesLoading(false);
    }
  }, [selectedNeeds, zipCode, radius]);

  /* ─── Send Nudge Handler ───────────────────────────────────────────────── */

  const handleSendNudge = useCallback(async () => {
    if (!nudgePatient) return;
    setNudgeLoading(true);
    try {
      await submitMotivationalEngagement({
        patient_name: nudgePatient,
        nudge_type: nudgeType,
        channel: nudgeChannel,
        message: nudgeMessage,
        personalize: nudgePersonalize,
      });
    } catch {
      // Fallback
    }
    const newNudge = {
      id: `N-${String(nudgeHistory.length + 1).padStart(3, "0")}`,
      patient: nudgePatient,
      type: nudgeType,
      channel: nudgeChannel,
      message: nudgeMessage || `${nudgeType.charAt(0).toUpperCase() + nudgeType.slice(1)} for ${nudgePatient}`,
      status: "pending" as const,
      sentAt: new Date().toLocaleString(),
      openedAt: null,
    };
    setNudgeHistory((prev) => [newNudge, ...prev]);
    setNudgePatient("");
    setNudgeMessage("");
    setNudgeLoading(false);
  }, [nudgePatient, nudgeType, nudgeChannel, nudgeMessage, nudgePersonalize, nudgeHistory.length]);

  /* ─── Toggle helpers ───────────────────────────────────────────────────── */

  const toggleSymptom = (s: string) =>
    setSelectedSymptoms((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));

  const toggleFactor = (f: string) =>
    setAssociatedFactors((prev) => (prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]));

  const toggleNeed = (n: string) =>
    setSelectedNeeds((prev) => (prev.includes(n) ? prev.filter((x) => x !== n) : [...prev, n]));

  /* ─── Render ───────────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Patient Engagement Hub</h1>
            <p className="text-sm text-gray-500">
              Symptom triage, care navigation, community resources, and motivational engagement
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-healthos-100 px-3 py-1 text-sm font-semibold text-healthos-700">
            <span className="inline-block h-2 w-2 rounded-full bg-healthos-500 animate-pulse" />
            {avgScore}% Engagement
          </span>
        </div>
        <button
          onClick={() => { setShowJourneyForm(true); setTab("Care Navigation"); }}
          className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-healthos-700 focus:outline-none focus:ring-2 focus:ring-healthos-500 focus:ring-offset-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
          New Journey
        </button>
      </div>

      {/* ── Stats Bar ───────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5 animate-fade-in-up">
        {[
          { label: "Active Journeys", value: String(journeys.length), icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2", color: "text-healthos-600 bg-healthos-50" },
          { label: "Triage Assessments Today", value: String(triageHistory.filter((t) => t.date === "2026-03-14" || t.date === "2026-03-15").length), icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z", color: "text-blue-600 bg-blue-50" },
          { label: "Resources Matched", value: String(resources.length), icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z", color: "text-emerald-600 bg-emerald-50" },
          { label: "Engagement Score", value: `${avgScore}%`, icon: "M13 10V3L4 14h7v7l9-11h-7z", color: "text-amber-600 bg-amber-50" },
          { label: "Nudges Sent", value: String(nudgeHistory.length), icon: "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9", color: "text-purple-600 bg-purple-50" },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover p-4 animate-fade-in-up">
            <div className="flex items-center gap-3">
              <div className={`rounded-lg p-2 ${kpi.color}`}>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d={kpi.icon} /></svg>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500">{kpi.label}</p>
                <p className="text-xl font-bold text-gray-900">{kpi.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Tab Bar ─────────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                tab === t
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* ════════════════════════════════════════════════════════════════════════
          TAB 1 — SYMPTOM TRIAGE
      ════════════════════════════════════════════════════════════════════════ */}
      {tab === "Symptom Triage" && (
        <div className="grid gap-6 lg:grid-cols-2 animate-fade-in-up">
          {/* Triage Form */}
          <div className="card p-6 space-y-5">
            <h2 className="text-lg font-semibold text-gray-900">Symptom Assessment</h2>

            {/* Symptom Chips */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Select Symptoms</label>
              <div className="flex flex-wrap gap-2">
                {SYMPTOM_OPTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => toggleSymptom(s)}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all ${
                      selectedSymptoms.includes(s)
                        ? "bg-healthos-600 text-white shadow-sm"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Severity Slider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity Level: <span className={`font-bold ${severity >= 8 ? "text-red-600" : severity >= 5 ? "text-yellow-600" : "text-green-600"}`}>{severity}/10</span>
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={severity}
                onChange={(e) => setSeverity(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-healthos-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Mild</span>
                <span>Moderate</span>
                <span>Severe</span>
              </div>
            </div>

            {/* Duration */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Duration</label>
              <input
                type="text"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="e.g., 3 days, 2 hours, 1 week"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 focus:outline-none"
              />
            </div>

            {/* Associated Factors */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Associated Factors</label>
              <div className="grid grid-cols-2 gap-2">
                {ASSOCIATED_FACTORS.map((f) => (
                  <label key={f} className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={associatedFactors.includes(f)}
                      onChange={() => toggleFactor(f)}
                      className="h-4 w-4 rounded border-gray-300 text-healthos-600 focus:ring-healthos-500"
                    />
                    {f}
                  </label>
                ))}
              </div>
            </div>

            {/* Assess Button */}
            <button
              onClick={handleTriage}
              disabled={selectedSymptoms.length === 0 || triageLoading}
              className="w-full rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-healthos-500 focus:ring-offset-2"
            >
              {triageLoading ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                  Assessing...
                </span>
              ) : "Assess"}
            </button>

            {/* Triage Result */}
            {triageResult && (
              <div className={`rounded-lg border-2 p-4 space-y-3 animate-fade-in-up ${urgencyStyle(triageResult.urgency)}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`inline-block h-3 w-3 rounded-full ${urgencyDot(triageResult.urgency)}`} />
                    <span className="text-lg font-bold capitalize">{triageResult.urgency}</span>
                  </div>
                  <span className="rounded-full bg-white/60 px-3 py-1 text-xs font-medium">{triageResult.venue}</span>
                </div>
                <div>
                  <p className="text-sm font-medium mb-1">Follow-up Actions:</p>
                  <ul className="list-disc list-inside text-sm space-y-0.5">
                    {triageResult.followUp.map((a, i) => <li key={i}>{a}</li>)}
                  </ul>
                </div>
                {triageResult.selfCare.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-1">Self-Care Instructions:</p>
                    <ul className="list-disc list-inside text-sm space-y-0.5">
                      {triageResult.selfCare.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Recent Triage History */}
          <div className="card p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Triage History</h2>
            <div className="space-y-3">
              {triageHistory.map((t) => (
                <div key={t.id} className="card-hover rounded-lg border border-gray-200 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`inline-block h-2.5 w-2.5 rounded-full ${urgencyDot(t.urgency)}`} />
                      <span className="font-medium text-gray-900">{t.patient}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${urgencyStyle(t.urgency)}`}>{t.urgency}</span>
                      <span className="text-xs text-gray-400">{t.date}</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {t.symptoms.map((s) => (
                      <span key={s} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{s}</span>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Severity: {t.severity}/10</span>
                    <span>Venue: {t.venue}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════
          TAB 2 — CARE NAVIGATION
      ════════════════════════════════════════════════════════════════════════ */}
      {tab === "Care Navigation" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Create Journey Form */}
          {showJourneyForm && (
            <div className="card p-6 space-y-4 border-2 border-healthos-200 animate-fade-in-up">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Create Care Journey</h2>
                <button onClick={() => setShowJourneyForm(false)} className="text-gray-400 hover:text-gray-600">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Patient ID</label>
                  <input
                    type="text"
                    value={journeyPatientId}
                    onChange={(e) => setJourneyPatientId(e.target.value)}
                    placeholder="e.g., P-1005"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Journey Type</label>
                  <select
                    value={journeyType}
                    onChange={(e) => setJourneyType(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 focus:outline-none"
                  >
                    <option value="">Select type...</option>
                    <option value="Diabetes Management">Diabetes Management</option>
                    <option value="Cardiac Rehab">Cardiac Rehab</option>
                    <option value="Surgical Preparation">Surgical Preparation</option>
                    <option value="Cancer Screening">Cancer Screening</option>
                    <option value="Chronic Pain Management">Chronic Pain Management</option>
                    <option value="Behavioral Health">Behavioral Health</option>
                    <option value="Maternal Care">Maternal Care</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Goals (comma-separated)</label>
                  <input
                    type="text"
                    value={journeyGoals}
                    onChange={(e) => setJourneyGoals(e.target.value)}
                    placeholder="e.g., Reduce A1C, Daily monitoring"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 focus:outline-none"
                  />
                </div>
              </div>
              <button
                onClick={handleCreateJourney}
                disabled={!journeyPatientId || !journeyType || journeyLoading}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {journeyLoading ? "Creating..." : "Create Journey"}
              </button>
            </div>
          )}

          {!showJourneyForm && (
            <button
              onClick={() => setShowJourneyForm(true)}
              className="inline-flex items-center gap-2 rounded-lg border-2 border-dashed border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-500 transition-colors hover:border-healthos-400 hover:text-healthos-600"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
              Create Journey
            </button>
          )}

          {/* Journey Cards */}
          <div className="space-y-4">
            {journeys.map((j) => (
              <div key={j.id} className="card card-hover p-5 space-y-4 animate-fade-in-up">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{j.name}</h3>
                      <span className="rounded bg-healthos-50 px-2 py-0.5 text-xs font-medium text-healthos-700">{j.id}</span>
                    </div>
                    <p className="text-sm text-gray-500">{j.patient} &middot; Navigator: {j.navigator}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-bold text-healthos-600">{j.progress}%</span>
                    <p className="text-xs text-gray-400">complete</p>
                  </div>
                </div>

                {/* Step Timeline */}
                <div className="flex items-center gap-1">
                  {j.steps.map((step, idx) => (
                    <div key={idx} className="flex-1 flex flex-col items-center">
                      <div className={`h-2.5 w-full rounded-full ${
                        idx < j.currentStep ? "bg-healthos-500" : idx === j.currentStep ? "bg-healthos-400 animate-pulse" : "bg-gray-200"
                      }`} />
                      <span className={`mt-1 text-[10px] leading-tight text-center ${
                        idx === j.currentStep ? "font-semibold text-healthos-700" : "text-gray-400"
                      }`}>
                        {step}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Expand Detail */}
                <button
                  onClick={() => setSelectedJourney(selectedJourney === j.id ? null : j.id)}
                  className="text-xs text-healthos-600 hover:text-healthos-800 font-medium"
                >
                  {selectedJourney === j.id ? "Hide Details" : "View Details"}
                </button>

                {selectedJourney === j.id && (
                  <div className="grid gap-4 sm:grid-cols-2 pt-2 border-t border-gray-100 animate-fade-in-up">
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Next Actions</p>
                      <ul className="space-y-1">
                        {j.nextActions.map((a, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-healthos-500" />
                            {a}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Goals</p>
                      <ul className="space-y-1">
                        {j.goals.map((g, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                            <svg xmlns="http://www.w3.org/2000/svg" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-healthos-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                            {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="sm:col-span-2">
                      <p className="text-xs font-medium text-gray-500 mb-2">Milestone Timeline</p>
                      <div className="flex items-center gap-3 overflow-x-auto pb-2">
                        {j.steps.map((step, idx) => (
                          <div key={idx} className="flex items-center gap-2">
                            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                              idx < j.currentStep
                                ? "bg-healthos-600 text-white"
                                : idx === j.currentStep
                                ? "bg-healthos-100 text-healthos-700 ring-2 ring-healthos-400"
                                : "bg-gray-100 text-gray-400"
                            }`}>
                              {idx < j.currentStep ? (
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                              ) : (
                                idx + 1
                              )}
                            </div>
                            {idx < j.steps.length - 1 && (
                              <div className={`h-0.5 w-8 ${idx < j.currentStep ? "bg-healthos-500" : "bg-gray-200"}`} />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════
          TAB 3 — COMMUNITY RESOURCES
      ════════════════════════════════════════════════════════════════════════ */}
      {tab === "Community Resources" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Search Controls */}
          <div className="card p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Resource Finder</h2>

            {/* Needs Chips */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Select Needs</label>
              <div className="flex flex-wrap gap-2">
                {NEED_OPTIONS.map((n) => (
                  <button
                    key={n}
                    onClick={() => toggleNeed(n)}
                    className={`rounded-full px-4 py-1.5 text-sm font-medium capitalize transition-all ${
                      selectedNeeds.includes(n)
                        ? `${needBadgeColor(n)} ring-2 ring-offset-1 ring-gray-300 shadow-sm`
                        : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">ZIP Code</label>
                <input
                  type="text"
                  value={zipCode}
                  onChange={(e) => setZipCode(e.target.value)}
                  placeholder="Enter ZIP code"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Radius: <span className="font-bold text-healthos-600">{radius} miles</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={25}
                  value={radius}
                  onChange={(e) => setRadius(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-healthos-600 mt-2"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>1 mi</span>
                  <span>25 mi</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleSearchResources}
              disabled={selectedNeeds.length === 0 || resourcesLoading}
              className="rounded-lg bg-healthos-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {resourcesLoading ? "Searching..." : "Search Resources"}
            </button>
          </div>

          {/* Resource Results + Map Placeholder */}
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              {resources.map((r) => (
                <div key={r.id} className="card card-hover p-5 space-y-3 animate-fade-in-up">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900">{r.name}</h3>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${needBadgeColor(r.type)}`}>{r.type}</span>
                      </div>
                      <p className="text-sm text-gray-500 mt-0.5">{r.address}</p>
                    </div>
                    <span className="whitespace-nowrap rounded bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">{r.distance}</span>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span className="flex items-center gap-1">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>
                      {r.phone}
                    </span>
                    <span className="text-xs text-gray-400">{r.hours}</span>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1.5">Services</p>
                    <div className="flex flex-wrap gap-1.5">
                      {r.services.map((s) => (
                        <span key={s} className="rounded bg-gray-50 border border-gray-200 px-2 py-0.5 text-xs text-gray-600">{s}</span>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => { setReferralSent(r.id); setTimeout(() => setReferralSent(null), 3000); }}
                    className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                      referralSent === r.id
                        ? "bg-green-100 text-green-800"
                        : "bg-healthos-50 text-healthos-700 hover:bg-healthos-100"
                    }`}
                  >
                    {referralSent === r.id ? "Referral Sent!" : "Refer Patient"}
                  </button>
                </div>
              ))}
            </div>

            {/* Map Placeholder */}
            <div className="card p-4 space-y-3">
              <h3 className="text-sm font-semibold text-gray-700">Resource Distribution</h3>
              <div className="relative h-80 rounded-lg bg-gradient-to-br from-healthos-50 to-blue-50 border-2 border-dashed border-gray-200 flex flex-col items-center justify-center gap-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" /></svg>
                <p className="text-sm text-gray-400">Map View</p>
                <p className="text-xs text-gray-300">ZIP: {zipCode} | Radius: {radius} mi</p>
                {/* Pin Markers */}
                <div className="absolute inset-4">
                  {resources.slice(0, 5).map((r, i) => {
                    const positions = [
                      { top: "20%", left: "30%" },
                      { top: "45%", left: "60%" },
                      { top: "30%", left: "70%" },
                      { top: "65%", left: "25%" },
                      { top: "55%", left: "45%" },
                    ];
                    return (
                      <div key={r.id} className="absolute group" style={positions[i]}>
                        <div className={`h-4 w-4 rounded-full border-2 border-white shadow-md ${
                          r.type === "food" ? "bg-emerald-500" : r.type === "housing" ? "bg-purple-500" : r.type === "transportation" ? "bg-blue-500" : r.type === "financial" ? "bg-amber-500" : "bg-pink-500"
                        }`} />
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-[10px] text-white">
                          {r.name}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {["food", "housing", "transportation", "financial", "mental health"].map((type) => (
                  <span key={type} className="flex items-center gap-1 text-[10px] text-gray-500">
                    <span className={`inline-block h-2 w-2 rounded-full ${
                      type === "food" ? "bg-emerald-500" : type === "housing" ? "bg-purple-500" : type === "transportation" ? "bg-blue-500" : type === "financial" ? "bg-amber-500" : "bg-pink-500"
                    }`} />
                    {type}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════════════════
          TAB 4 — ENGAGEMENT & NUDGES
      ════════════════════════════════════════════════════════════════════════ */}
      {tab === "Engagement & Nudges" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Engagement Metrics Row */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {/* Score Trends */}
            <div className="card p-5 sm:col-span-2 lg:col-span-2 space-y-3">
              <h2 className="text-lg font-semibold text-gray-900">Engagement Score Trends</h2>
              <div className="space-y-3">
                {engagementScores.map((e) => (
                  <div key={e.patient} className="flex items-center gap-4">
                    <span className="w-32 truncate text-sm font-medium text-gray-700">{e.patient}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        {e.weeklyScores.map((s, i) => (
                          <div key={i} className="flex-1 flex flex-col items-center">
                            <div
                              className={`w-full rounded-sm ${
                                s >= 80 ? "bg-green-400" : s >= 60 ? "bg-yellow-400" : "bg-red-400"
                              }`}
                              style={{ height: `${Math.max(s * 0.4, 4)}px` }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                    <span className="w-12 text-right text-sm font-bold text-gray-900">{e.score}%</span>
                    <span className={`text-xs ${e.trend === "up" ? "text-green-600" : "text-red-600"}`}>
                      {e.trend === "up" ? "+" : "-"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Nudge Effectiveness */}
            <div className="card p-5 space-y-3">
              <h2 className="text-sm font-semibold text-gray-900">Nudge Effectiveness</h2>
              {(() => {
                const total = nudgeHistory.length;
                const delivered = nudgeHistory.filter((n) => n.status === "delivered").length;
                const opened = nudgeHistory.filter((n) => n.openedAt).length;
                const pending = nudgeHistory.filter((n) => n.status === "pending").length;
                const failed = nudgeHistory.filter((n) => n.status === "failed").length;
                return (
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs text-gray-500 mb-1"><span>Delivery Rate</span><span>{total > 0 ? Math.round((delivered / total) * 100) : 0}%</span></div>
                      <div className="h-2 rounded-full bg-gray-100"><div className="h-2 rounded-full bg-green-500" style={{ width: `${total > 0 ? (delivered / total) * 100 : 0}%` }} /></div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs text-gray-500 mb-1"><span>Open Rate</span><span>{delivered > 0 ? Math.round((opened / delivered) * 100) : 0}%</span></div>
                      <div className="h-2 rounded-full bg-gray-100"><div className="h-2 rounded-full bg-blue-500" style={{ width: `${delivered > 0 ? (opened / delivered) * 100 : 0}%` }} /></div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 pt-2">
                      <div className="text-center">
                        <p className="text-lg font-bold text-green-600">{delivered}</p>
                        <p className="text-[10px] text-gray-400">Delivered</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-yellow-600">{pending}</p>
                        <p className="text-[10px] text-gray-400">Pending</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-red-600">{failed}</p>
                        <p className="text-[10px] text-gray-400">Failed</p>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>

          {/* Send Nudge Form + History */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Send Nudge */}
            <div className="card p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Send Nudge</h2>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Patient</label>
                <select
                  value={nudgePatient}
                  onChange={(e) => setNudgePatient(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 focus:outline-none"
                >
                  <option value="">Select patient...</option>
                  {engagementScores.map((e) => (
                    <option key={e.patient} value={e.patient}>{e.patient} ({e.score}% engagement)</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nudge Type</label>
                <div className="flex flex-wrap gap-2">
                  {NUDGE_TYPES.map((t) => (
                    <button
                      key={t}
                      onClick={() => setNudgeType(t)}
                      className={`rounded-full px-3 py-1.5 text-xs font-medium capitalize transition-all ${
                        nudgeType === t
                          ? "bg-healthos-600 text-white"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Channel</label>
                <div className="flex gap-2">
                  {NUDGE_CHANNELS.map((c) => (
                    <button
                      key={c}
                      onClick={() => setNudgeChannel(c)}
                      className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                        nudgeChannel === c
                          ? "bg-healthos-100 text-healthos-700 ring-2 ring-healthos-400"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Message (optional)</label>
                <textarea
                  value={nudgeMessage}
                  onChange={(e) => setNudgeMessage(e.target.value)}
                  rows={3}
                  placeholder="Custom message or leave blank for auto-generated..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 focus:outline-none resize-none"
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={nudgePersonalize}
                  onChange={() => setNudgePersonalize(!nudgePersonalize)}
                  className="h-4 w-4 rounded border-gray-300 text-healthos-600 focus:ring-healthos-500"
                />
                Personalize with patient data (name, streak, goals)
              </label>

              <button
                onClick={handleSendNudge}
                disabled={!nudgePatient || nudgeLoading}
                className="w-full rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {nudgeLoading ? "Sending..." : "Send Nudge"}
              </button>
            </div>

            {/* Nudge History */}
            <div className="card p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Recent Nudge History</h2>
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {nudgeHistory.map((n) => (
                  <div key={n.id} className="rounded-lg border border-gray-200 p-3 space-y-2 card-hover">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-gray-900">{n.patient}</span>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${nudgeStatusStyle(n.status)}`}>{n.status}</span>
                      </div>
                      <span className="text-[10px] text-gray-400">{n.sentAt}</span>
                    </div>
                    <p className="text-sm text-gray-600">{n.message}</p>
                    <div className="flex items-center gap-3 text-[10px] text-gray-400">
                      <span className="capitalize rounded bg-gray-50 px-1.5 py-0.5">{n.type}</span>
                      <span className="rounded bg-gray-50 px-1.5 py-0.5">{n.channel}</span>
                      {n.openedAt && <span className="text-green-600">Opened: {n.openedAt}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Patient Interaction Timeline */}
          <div className="card p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Patient Interaction Timeline</h2>
            <div className="relative border-l-2 border-gray-200 ml-4 space-y-4">
              {[
                { time: "Today 08:32", event: "Maria Garcia opened medication reminder", type: "nudge", color: "bg-green-500" },
                { time: "Today 07:15", event: "James Wilson completed cardiac rehab exercise", type: "journey", color: "bg-blue-500" },
                { time: "Yesterday 18:05", event: "Sarah Chen logged 8,000 steps via wellness tracker", type: "engagement", color: "bg-purple-500" },
                { time: "Yesterday 14:00", event: "Follow-up nudge sent to Emily Davis — awaiting response", type: "nudge", color: "bg-yellow-500" },
                { time: "Yesterday 10:30", event: "Robert Johnson referred to Community Food Bank", type: "resource", color: "bg-emerald-500" },
                { time: "Mar 13 16:45", event: "Maria Garcia completed diabetes education class (Step 3/6)", type: "journey", color: "bg-blue-500" },
                { time: "Mar 13 09:00", event: "Triage assessment completed for Emily Davis — non-urgent", type: "triage", color: "bg-green-500" },
              ].map((item, i) => (
                <div key={i} className="relative pl-6">
                  <div className={`absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full ${item.color}`} />
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm text-gray-700">{item.event}</p>
                      <span className="text-[10px] text-gray-400 capitalize">{item.type}</span>
                    </div>
                    <span className="whitespace-nowrap text-xs text-gray-400">{item.time}</span>
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
