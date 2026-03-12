"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchRPMDashboard, fetchVitals, type RPMDashboard } from "@/lib/api";

const TABS = ["Monitoring", "Devices", "Alerts", "Adherence"] as const;

/* ── Fallback demo data (used when API is unavailable) ─────────────────────── */
const DEMO_PATIENTS = [
  { id: "p-001", name: "Maria Garcia", mrn: "MRN-10042", risk: "high", hr: 92, bp: "148/92", spo2: 94, temp: 99.1, glucose: 218, lastReading: "2 min ago", device: "Withings BPM", alerts: 3 },
  { id: "p-002", name: "James Wilson", mrn: "MRN-10087", risk: "critical", hr: 112, bp: "162/105", spo2: 91, temp: 100.4, glucose: 310, lastReading: "5 min ago", device: "iHealth Clear", alerts: 5 },
  { id: "p-003", name: "Sarah Chen", mrn: "MRN-10123", risk: "moderate", hr: 78, bp: "132/84", spo2: 97, temp: 98.6, glucose: 142, lastReading: "12 min ago", device: "Omron HeartGuide", alerts: 1 },
  { id: "p-004", name: "Robert Johnson", mrn: "MRN-10056", risk: "low", hr: 72, bp: "122/78", spo2: 98, temp: 98.2, glucose: 105, lastReading: "8 min ago", device: "Apple Watch S9", alerts: 0 },
  { id: "p-005", name: "Emily Davis", mrn: "MRN-10198", risk: "high", hr: 88, bp: "156/98", spo2: 93, temp: 98.9, glucose: 195, lastReading: "1 min ago", device: "Masimo MightySat", alerts: 2 },
];

const DEVICES = [
  { type: "Blood Pressure Monitor", model: "Withings BPM Connect", enrolled: 342, active: 318, compliance: "93%", avgReadings: "2.1/day" },
  { type: "Pulse Oximeter", model: "Masimo MightySat Rx", enrolled: 287, active: 264, compliance: "92%", avgReadings: "3.4/day" },
  { type: "Glucose Monitor", model: "Dexcom G7 CGM", enrolled: 198, active: 192, compliance: "97%", avgReadings: "48/day" },
  { type: "Weight Scale", model: "Withings Body+", enrolled: 412, active: 356, compliance: "86%", avgReadings: "1.0/day" },
  { type: "Smartwatch", model: "Apple Watch Series 9", enrolled: 524, active: 498, compliance: "95%", avgReadings: "continuous" },
  { type: "Temperature", model: "TempTraq Patch", enrolled: 89, active: 82, compliance: "92%", avgReadings: "continuous" },
];

const RPM_ALERTS = [
  { time: "14:32", patient: "James Wilson", type: "SpO2 Critical", value: "SpO2: 88%", severity: "critical", status: "Active" },
  { time: "14:28", patient: "James Wilson", type: "Blood Pressure", value: "BP: 172/112 mmHg", severity: "critical", status: "Active" },
  { time: "14:15", patient: "Maria Garcia", type: "Glucose High", value: "Glucose: 285 mg/dL", severity: "high", status: "Active" },
  { time: "13:45", patient: "Emily Davis", type: "Heart Rate", value: "HR: 118 bpm", severity: "high", status: "Acknowledged" },
  { time: "13:20", patient: "Maria Garcia", type: "Blood Pressure", value: "BP: 158/96 mmHg", severity: "moderate", status: "Acknowledged" },
  { time: "12:50", patient: "Sarah Chen", type: "Weight Change", value: "+3.2 lbs in 2 days", severity: "moderate", status: "Acknowledged" },
];

const ADHERENCE = [
  { patient: "Maria Garcia", overall: 87, bp: 92, glucose: 78, weight: 90, streak: "14 days", trend: "Stable" },
  { patient: "James Wilson", overall: 62, bp: 55, glucose: 70, weight: 60, streak: "3 days", trend: "Declining" },
  { patient: "Sarah Chen", overall: 94, bp: 96, glucose: 91, weight: 95, streak: "28 days", trend: "Improving" },
  { patient: "Robert Johnson", overall: 91, bp: 93, glucose: 88, weight: 92, streak: "21 days", trend: "Stable" },
  { patient: "Emily Davis", overall: 73, bp: 80, glucose: 65, weight: 75, streak: "5 days", trend: "Improving" },
];

function riskBadge(risk: string) {
  const map: Record<string, string> = {
    critical: "bg-red-200 text-red-900",
    high: "bg-red-100 text-red-800",
    moderate: "bg-yellow-100 text-yellow-800",
    low: "bg-green-100 text-green-800",
  };
  return map[risk] ?? "bg-gray-100 text-gray-800";
}

function severityBadge(s: string) {
  const map: Record<string, string> = {
    critical: "bg-red-200 text-red-900",
    high: "bg-red-100 text-red-800",
    moderate: "bg-yellow-100 text-yellow-800",
    low: "bg-green-100 text-green-800",
  };
  return map[s] ?? "bg-gray-100 text-gray-800";
}

function statusBadge(s: string) {
  const map: Record<string, string> = {
    Active: "bg-red-100 text-red-800",
    Acknowledged: "bg-blue-100 text-blue-800",
    Resolved: "bg-green-100 text-green-800",
  };
  return map[s] ?? "bg-gray-100 text-gray-800";
}

function adherenceColor(pct: number) {
  return pct >= 90 ? "text-green-600" : pct >= 75 ? "text-yellow-600" : "text-red-600";
}

function trendBadge(t: string) {
  const map: Record<string, string> = { Improving: "bg-green-100 text-green-700", Stable: "bg-blue-100 text-blue-700", Declining: "bg-red-100 text-red-700" };
  return map[t] ?? "bg-gray-100 text-gray-700";
}

export default function RPMPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const [dashboard, setDashboard] = useState<RPMDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    try {
      const data = await fetchRPMDashboard();
      setDashboard(data);
    } catch {
      // API unavailable — use demo data (KPIs shown from constants)
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const activePatients = dashboard?.active_patients ?? DEMO_PATIENTS.length;
  const criticalAlerts = dashboard?.critical_alerts ?? RPM_ALERTS.filter((a) => a.severity === "critical").length;
  const avgAdherence = dashboard?.avg_adherence ?? 81;
  const devicesOnline = dashboard?.devices_online ?? DEVICES.reduce((s, d) => s + d.active, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Remote Patient Monitoring</h1>
          <p className="text-sm text-gray-500">Real-time vitals ingestion, anomaly detection, risk scoring, and device management</p>
        </div>
        <div className="flex gap-2">
          <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Export Report</button>
          <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">Enroll Patient</button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Active Patients", value: String(activePatients), sub: `${criticalAlerts} critical` },
          { label: "Devices Online", value: String(devicesOnline), sub: "98.2% uptime" },
          { label: "Alerts (24h)", value: String(criticalAlerts + RPM_ALERTS.length), sub: `${criticalAlerts} critical` },
          { label: "Avg Adherence", value: `${avgAdherence}%`, sub: "Target: 85%" },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs font-medium text-gray-500">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{kpi.value}</p>
            <p className="text-xs text-gray-400">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                tab === t ? "border-healthos-600 text-healthos-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* Monitoring — Live Patient Vitals */}
      {tab === "Monitoring" && (
        <div className="space-y-3">
          {DEMO_PATIENTS.map((p) => (
            <div key={p.id} className={`rounded-lg border bg-white p-4 ${p.risk === "critical" ? "border-red-300" : "border-gray-200"}`}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskBadge(p.risk)}`}>{p.risk}</span>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{p.name}</p>
                    <p className="text-xs text-gray-400">{p.mrn} · {p.device} · Last: {p.lastReading}</p>
                  </div>
                </div>
                {p.alerts > 0 && (
                  <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">{p.alerts} alert{p.alerts > 1 ? "s" : ""}</span>
                )}
              </div>
              <div className="mt-3 grid grid-cols-3 gap-3 sm:grid-cols-5">
                {[
                  { label: "HR", value: `${p.hr} bpm`, warn: p.hr > 100 || p.hr < 50 },
                  { label: "BP", value: p.bp, warn: parseInt(p.bp) > 140 },
                  { label: "SpO2", value: `${p.spo2}%`, warn: p.spo2 < 95 },
                  { label: "Temp", value: `${p.temp}°F`, warn: p.temp > 99.5 },
                  { label: "Glucose", value: `${p.glucose} mg/dL`, warn: p.glucose > 180 || p.glucose < 70 },
                ].map((v) => (
                  <div key={v.label} className={`rounded-lg border p-2 text-center ${v.warn ? "border-red-200 bg-red-50" : "border-gray-100"}`}>
                    <p className="text-[10px] font-medium text-gray-500">{v.label}</p>
                    <p className={`text-sm font-bold ${v.warn ? "text-red-600" : "text-gray-900"}`}>{v.value}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Devices */}
      {tab === "Devices" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Device Type", "Model", "Enrolled", "Active", "Compliance", "Avg Readings"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {DEVICES.map((d) => (
                <tr key={d.type} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{d.type}</td>
                  <td className="px-4 py-3 text-gray-500">{d.model}</td>
                  <td className="px-4 py-3 font-mono">{d.enrolled}</td>
                  <td className="px-4 py-3 font-mono">{d.active}</td>
                  <td className="px-4 py-3"><span className="font-medium text-green-600">{d.compliance}</span></td>
                  <td className="px-4 py-3 text-gray-500">{d.avgReadings}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Alerts */}
      {tab === "Alerts" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Time", "Patient", "Alert Type", "Value", "Severity", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {RPM_ALERTS.map((a, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{a.time}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{a.patient}</td>
                  <td className="px-4 py-3">{a.type}</td>
                  <td className="px-4 py-3 font-mono text-xs">{a.value}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${severityBadge(a.severity)}`}>{a.severity}</span></td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge(a.status)}`}>{a.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Adherence */}
      {tab === "Adherence" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Patient", "Overall", "BP", "Glucose", "Weight", "Streak", "Trend"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {ADHERENCE.map((a, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.patient}</td>
                  <td className="px-4 py-3"><span className={`font-bold ${adherenceColor(a.overall)}`}>{a.overall}%</span></td>
                  <td className="px-4 py-3"><span className={adherenceColor(a.bp)}>{a.bp}%</span></td>
                  <td className="px-4 py-3"><span className={adherenceColor(a.glucose)}>{a.glucose}%</span></td>
                  <td className="px-4 py-3"><span className={adherenceColor(a.weight)}>{a.weight}%</span></td>
                  <td className="px-4 py-3 text-gray-500">{a.streak}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${trendBadge(a.trend)}`}>{a.trend}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
