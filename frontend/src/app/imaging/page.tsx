"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchImagingStudies, fetchImagingWorklist, analyzeImage, evaluateCriticalFinding } from "@/lib/api";

const TABS = ["Studies", "AI Analysis", "Worklist", "Critical Findings"] as const;

const STUDIES = [
  { id: "STD-001", patient: "Maria Garcia", modality: "CR", body_part: "Chest", description: "PA and Lateral Chest X-ray", status: "Read", date: "2026-03-12", radiologist: "Dr. Rodriguez" },
  { id: "STD-002", patient: "James Wilson", modality: "CT", body_part: "Head", description: "CT Head w/o Contrast", status: "Read", date: "2026-03-10", radiologist: "Dr. Chen" },
  { id: "STD-003", patient: "Robert Johnson", modality: "MR", body_part: "Spine", description: "MRI Lumbar Spine", status: "Pending Read", date: "2026-03-08", radiologist: "—" },
  { id: "STD-004", patient: "Emily Davis", modality: "US", body_part: "Abdomen", description: "Abdominal Ultrasound", status: "Read", date: "2026-03-05", radiologist: "Dr. Rodriguez" },
  { id: "STD-005", patient: "Sarah Chen", modality: "MG", body_part: "Breast", description: "Bilateral Screening Mammography", status: "Read", date: "2026-03-03", radiologist: "Dr. Kim" },
];

const AI_FINDINGS = [
  { study: "STD-001", type: "Chest X-ray", model: "CheXNet-v2", finding: "Mild cardiomegaly", confidence: 0.87, severity: "Moderate", action: "Clinical correlation" },
  { study: "STD-002", type: "CT Head", model: "DeepBleed-v1", finding: "No acute hemorrhage", confidence: 0.97, severity: "Low", action: "None required" },
  { study: "STD-005", type: "Mammography", model: "BreastScreen-v1", finding: "BI-RADS 2 — Benign", confidence: 0.91, severity: "Low", action: "Routine follow-up" },
];

const WORKLIST = {
  STAT: { pending: 1, in_progress: 0, completed: 3 },
  URGENT: { pending: 4, in_progress: 2, completed: 8 },
  ROUTINE: { pending: 18, in_progress: 3, completed: 42 },
  SCREENING: { pending: 12, in_progress: 0, completed: 15 },
};

const CRITICAL_FINDINGS = [
  { date: "2026-03-12 09:15", finding: "Pneumothorax", modality: "CR", patient: "John Doe", urgency: "Stat", response_min: 8, acknowledged_by: "Dr. Rodriguez", status: "Acknowledged" },
  { date: "2026-03-10 14:22", finding: "Intracranial Hemorrhage", modality: "CT", patient: "Jane Smith", urgency: "Stat", response_min: 6, acknowledged_by: "Dr. Chen", status: "Acknowledged" },
  { date: "2026-03-07 03:45", finding: "Pulmonary Embolism", modality: "CT", patient: "Bob Wilson", urgency: "Stat", response_min: 11, acknowledged_by: "Dr. Kim", status: "Acknowledged" },
];

function statusColor(s: string) {
  const map: Record<string, string> = {
    Read: "bg-green-100 text-green-800",
    "Pending Read": "bg-yellow-100 text-yellow-800",
    Acknowledged: "bg-green-100 text-green-800",
    Stat: "bg-red-200 text-red-900",
  };
  return map[s] ?? "bg-gray-100 text-gray-800";
}

function severityColor(s: string) {
  const map: Record<string, string> = { Critical: "bg-red-200 text-red-900", High: "bg-red-100 text-red-800", Moderate: "bg-yellow-100 text-yellow-800", Low: "bg-green-100 text-green-800" };
  return map[s] ?? "bg-gray-100 text-gray-800";
}

export default function ImagingPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const [apiStudies, setApiStudies] = useState<typeof STUDIES | null>(null);
  const [apiWorklist, setApiWorklist] = useState<typeof WORKLIST | null>(null);

  useEffect(() => {
    fetchImagingWorklist()
      .then((data) => setApiWorklist(data as typeof WORKLIST))
      .catch(() => {/* use demo data */});
  }, []);

  const studies = apiStudies ?? STUDIES;
  const worklist = apiWorklist ?? WORKLIST;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Imaging & Radiology</h1>
        <p className="text-sm text-gray-500">DICOM ingestion, AI image analysis, radiology reports, and critical finding alerts</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Studies Today", value: "68", sub: "12 pending read" },
          { label: "AI Analyses", value: "54", sub: "3 critical findings" },
          { label: "Avg Read Time", value: "14 min", sub: "SLA: 96.5%" },
          { label: "Critical Findings", value: "3", sub: "All acknowledged" },
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

      {tab === "Studies" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>{["Study ID", "Patient", "Modality", "Body Part", "Description", "Radiologist", "Status", "Date"].map((h) => <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {STUDIES.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{s.id}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{s.patient}</td>
                  <td className="px-4 py-3">{s.modality}</td>
                  <td className="px-4 py-3">{s.body_part}</td>
                  <td className="px-4 py-3 text-gray-500">{s.description}</td>
                  <td className="px-4 py-3">{s.radiologist}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(s.status)}`}>{s.status}</span></td>
                  <td className="px-4 py-3 text-gray-500">{s.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "AI Analysis" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900">AI Model Performance</h3>
            <div className="mt-3 grid grid-cols-1 gap-4 text-sm sm:grid-cols-3">
              {[
                { model: "CheXNet-v2", modality: "Chest X-ray", auc: "0.94" },
                { model: "DeepBleed-v1", modality: "CT Head", auc: "0.96" },
                { model: "BreastScreen-v1", modality: "Mammography", auc: "0.93" },
              ].map((m) => (
                <div key={m.model} className="rounded border border-gray-100 p-3 text-center">
                  <p className="font-semibold text-gray-900">{m.model}</p>
                  <p className="text-xs text-gray-500">{m.modality}</p>
                  <p className="mt-1 text-lg font-bold text-healthos-600">AUC {m.auc}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>{["Study", "Type", "Model", "Finding", "Confidence", "Severity", "Action"].map((h) => <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {AI_FINDINGS.map((f, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{f.study}</td>
                    <td className="px-4 py-3">{f.type}</td>
                    <td className="px-4 py-3 text-gray-500">{f.model}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{f.finding}</td>
                    <td className="px-4 py-3 font-mono">{(f.confidence * 100).toFixed(0)}%</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${severityColor(f.severity)}`}>{f.severity}</span></td>
                    <td className="px-4 py-3 text-gray-500">{f.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "Worklist" && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Object.entries(WORKLIST).map(([name, data]) => (
            <div key={name} className={`rounded-lg border p-4 ${name === "STAT" ? "border-red-200 bg-red-50" : "border-gray-200 bg-white"}`}>
              <h3 className="text-sm font-semibold text-gray-900">{name}</h3>
              <div className="mt-2 space-y-1 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Pending</span><span className="font-mono font-semibold">{data.pending}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">In Progress</span><span className="font-mono font-semibold">{data.in_progress}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Completed</span><span className="font-mono font-semibold">{data.completed}</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "Critical Findings" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>{["Date/Time", "Finding", "Modality", "Patient", "Urgency", "Response (min)", "Acknowledged By", "Status"].map((h) => <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {CRITICAL_FINDINGS.map((c, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{c.date}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{c.finding}</td>
                  <td className="px-4 py-3">{c.modality}</td>
                  <td className="px-4 py-3">{c.patient}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(c.urgency)}`}>{c.urgency}</span></td>
                  <td className="px-4 py-3 font-mono">{c.response_min}</td>
                  <td className="px-4 py-3">{c.acknowledged_by}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(c.status)}`}>{c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
