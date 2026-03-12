"use client";

import { useState } from "react";

const TABS = ["Triage", "Care Navigation", "SDOH Screening", "Engagement"] as const;

const TRIAGE_QUEUE = [
  { id: "TRG-001", patient: "Maria Garcia", complaint: "Headache", symptoms: "Throbbing, 3 days", level: "Semi-Urgent", color: "yellow", recommendation: "Schedule within 24-48h", date: "2026-03-12" },
  { id: "TRG-002", patient: "James Wilson", complaint: "Chest pain", symptoms: "Radiating to left arm", level: "Emergent", color: "red", recommendation: "Call 911 immediately", date: "2026-03-12" },
  { id: "TRG-003", patient: "Emily Davis", complaint: "Cold symptoms", symptoms: "Runny nose, cough, 2 days", level: "Self-Care", color: "blue", recommendation: "Home management", date: "2026-03-12" },
  { id: "TRG-004", patient: "Robert Johnson", complaint: "Back pain", symptoms: "Lower back, after lifting", level: "Routine", color: "green", recommendation: "Schedule routine appointment", date: "2026-03-11" },
];

const JOURNEYS = [
  { patient: "Maria Garcia", pathway: "Diabetes Management", step: "3/6", current: "Diabetes education class", progress: 50, status: "On Track" },
  { patient: "James Wilson", pathway: "Cardiac Rehab", step: "2/8", current: "Stress test scheduled", progress: 25, status: "On Track" },
  { patient: "Sarah Chen", pathway: "Surgical Preparation", step: "4/6", current: "Pre-op teaching", progress: 67, status: "On Track" },
  { patient: "Robert Johnson", pathway: "Cancer Screening", step: "3/5", current: "Results review", progress: 60, status: "Delayed" },
];

const SDOH_RESULTS = [
  { patient: "Maria Garcia", food: "At Risk", housing: "OK", transport: "At Risk", social: "OK", financial: "High Risk", overall: "High" },
  { patient: "James Wilson", food: "OK", housing: "OK", transport: "OK", social: "At Risk", financial: "OK", overall: "Low" },
  { patient: "Emily Davis", food: "At Risk", housing: "At Risk", transport: "OK", social: "OK", financial: "At Risk", overall: "Moderate" },
  { patient: "Robert Johnson", food: "OK", housing: "OK", transport: "At Risk", social: "OK", financial: "OK", overall: "Low" },
];

const ENGAGEMENT_SCORES = [
  { patient: "Maria Garcia", score: 82, trend: "Improving", badges: 8, streak: "12 days", nudges_responded: "78%" },
  { patient: "James Wilson", score: 65, trend: "Declining", badges: 3, streak: "2 days", nudges_responded: "45%" },
  { patient: "Sarah Chen", score: 91, trend: "Stable", badges: 12, streak: "28 days", nudges_responded: "92%" },
  { patient: "Emily Davis", score: 54, trend: "Declining", badges: 2, streak: "0 days", nudges_responded: "32%" },
  { patient: "Robert Johnson", score: 73, trend: "Improving", badges: 5, streak: "7 days", nudges_responded: "61%" },
];

function triageColor(color: string) {
  const map: Record<string, string> = { red: "bg-red-100 text-red-800", orange: "bg-orange-100 text-orange-800", yellow: "bg-yellow-100 text-yellow-800", green: "bg-green-100 text-green-800", blue: "bg-blue-100 text-blue-800" };
  return map[color] ?? "bg-gray-100 text-gray-800";
}

function riskColor(risk: string) {
  const map: Record<string, string> = { "High Risk": "bg-red-100 text-red-800", "At Risk": "bg-yellow-100 text-yellow-800", High: "bg-red-100 text-red-800", Moderate: "bg-yellow-100 text-yellow-800", Low: "bg-green-100 text-green-800", OK: "bg-green-100 text-green-800" };
  return map[risk] ?? "bg-gray-100 text-gray-800";
}

function statusColor(s: string) {
  const map: Record<string, string> = { "On Track": "bg-green-100 text-green-800", Delayed: "bg-red-100 text-red-800", Improving: "bg-green-100 text-green-800", Declining: "bg-red-100 text-red-800", Stable: "bg-blue-100 text-blue-800" };
  return map[s] ?? "bg-gray-100 text-gray-800";
}

export default function PatientEngagementPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Patient Engagement</h1>
        <p className="text-sm text-gray-500">Symptom triage, care navigation, SDOH screening, and motivational engagement</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Triages Today", value: "24", sub: "2 emergent" },
          { label: "Active Journeys", value: "156", sub: "82% completion rate" },
          { label: "SDOH Screenings", value: "284", sub: "78% screening rate" },
          { label: "Avg Engagement", value: "71/100", sub: "71.5% active" },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs font-medium text-gray-500">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{kpi.value}</p>
            <p className="text-xs text-gray-400">{kpi.sub}</p>
          </div>
        ))}
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${tab === t ? "border-healthos-600 text-healthos-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"}`}>
              {t}
            </button>
          ))}
        </nav>
      </div>

      {tab === "Triage" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>{["ID", "Patient", "Chief Complaint", "Symptoms", "Triage Level", "Recommendation", "Date"].map((h) => <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {TRIAGE_QUEUE.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{t.id}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{t.patient}</td>
                  <td className="px-4 py-3">{t.complaint}</td>
                  <td className="px-4 py-3 text-gray-500">{t.symptoms}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${triageColor(t.color)}`}>{t.level}</span></td>
                  <td className="px-4 py-3 text-gray-500">{t.recommendation}</td>
                  <td className="px-4 py-3 text-gray-500">{t.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Care Navigation" && (
        <div className="space-y-3">
          {JOURNEYS.map((j, i) => (
            <div key={i} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{j.patient}</p>
                  <p className="text-sm text-gray-500">{j.pathway} — Step {j.step}</p>
                  <p className="text-xs text-gray-400">Current: {j.current}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(j.status)}`}>{j.status}</span>
              </div>
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Progress</span>
                  <span>{j.progress}%</span>
                </div>
                <div className="mt-1 h-2 w-full rounded-full bg-gray-100">
                  <div className="h-2 rounded-full bg-healthos-600" style={{ width: `${j.progress}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "SDOH Screening" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>{["Patient", "Food", "Housing", "Transport", "Social", "Financial", "Overall Risk"].map((h) => <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {SDOH_RESULTS.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.patient}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColor(r.food)}`}>{r.food}</span></td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColor(r.housing)}`}>{r.housing}</span></td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColor(r.transport)}`}>{r.transport}</span></td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColor(r.social)}`}>{r.social}</span></td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColor(r.financial)}`}>{r.financial}</span></td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColor(r.overall)}`}>{r.overall}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Engagement" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>{["Patient", "Score", "Trend", "Badges", "Streak", "Nudge Response"].map((h) => <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {ENGAGEMENT_SCORES.map((e, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{e.patient}</td>
                  <td className="px-4 py-3 font-mono font-semibold">{e.score}/100</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(e.trend)}`}>{e.trend}</span></td>
                  <td className="px-4 py-3">{e.badges}</td>
                  <td className="px-4 py-3">{e.streak}</td>
                  <td className="px-4 py-3 font-mono">{e.nudges_responded}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
