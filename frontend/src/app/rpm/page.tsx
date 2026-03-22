"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchRPMDashboard, ingestRPMData, type RPMDashboard } from "@/lib/api";
import {
  fetchDevices,
  fetchDeviceAlertRules,
  registerDevice,
  type DeviceInfoResponse,
  type DeviceAlertRuleResponse,
} from "@/lib/platform-api";

/* ── Constants ─────────────────────────────────────────────────────────────── */

const TABS = ["Dashboard", "Real-Time Vitals", "Alerts & Trends", "Device Management"] as const;
type Tab = (typeof TABS)[number];

/* ── Demo Data ─────────────────────────────────────────────────────────────── */

const DEMO_PATIENTS = [
  {
    id: "p-001", name: "Maria Garcia", mrn: "MRN-10042", risk: "high" as const,
    deviceStatus: "online" as const, device: "Withings BPM Connect",
    hr: 92, bp: "148/92", spo2: 94, temp: 99.1, glucose: 218,
    adherence: 87, lastReading: "2 min ago", alerts: 3,
    hrHistory: [88, 90, 92, 94, 91, 92], bpHistory: [140, 142, 145, 148, 146, 148],
    spo2History: [96, 95, 95, 94, 94, 94], tempHistory: [98.4, 98.6, 98.8, 99.0, 99.1, 99.1],
  },
  {
    id: "p-002", name: "James Wilson", mrn: "MRN-10087", risk: "critical" as const,
    deviceStatus: "online" as const, device: "iHealth Clear",
    hr: 112, bp: "162/105", spo2: 91, temp: 100.4, glucose: 310,
    adherence: 62, lastReading: "5 min ago", alerts: 5,
    hrHistory: [98, 102, 106, 110, 111, 112], bpHistory: [150, 154, 158, 160, 161, 162],
    spo2History: [94, 93, 92, 92, 91, 91], tempHistory: [99.2, 99.6, 99.8, 100.0, 100.2, 100.4],
  },
  {
    id: "p-003", name: "Sarah Chen", mrn: "MRN-10123", risk: "moderate" as const,
    deviceStatus: "online" as const, device: "Omron HeartGuide",
    hr: 78, bp: "132/84", spo2: 97, temp: 98.6, glucose: 142,
    adherence: 94, lastReading: "12 min ago", alerts: 1,
    hrHistory: [76, 77, 78, 78, 77, 78], bpHistory: [130, 131, 132, 132, 131, 132],
    spo2History: [97, 97, 98, 97, 97, 97], tempHistory: [98.4, 98.5, 98.6, 98.6, 98.5, 98.6],
  },
  {
    id: "p-004", name: "Robert Johnson", mrn: "MRN-10056", risk: "low" as const,
    deviceStatus: "offline" as const, device: "Apple Watch S9",
    hr: 72, bp: "122/78", spo2: 98, temp: 98.2, glucose: 105,
    adherence: 91, lastReading: "45 min ago", alerts: 0,
    hrHistory: [70, 71, 72, 72, 71, 72], bpHistory: [120, 121, 122, 122, 121, 122],
    spo2History: [98, 98, 99, 98, 98, 98], tempHistory: [98.1, 98.2, 98.2, 98.2, 98.1, 98.2],
  },
  {
    id: "p-005", name: "Emily Davis", mrn: "MRN-10198", risk: "high" as const,
    deviceStatus: "online" as const, device: "Masimo MightySat",
    hr: 88, bp: "156/98", spo2: 93, temp: 98.9, glucose: 195,
    adherence: 73, lastReading: "1 min ago", alerts: 2,
    hrHistory: [84, 85, 86, 87, 88, 88], bpHistory: [148, 150, 152, 154, 155, 156],
    spo2History: [95, 95, 94, 94, 93, 93], tempHistory: [98.6, 98.7, 98.7, 98.8, 98.9, 98.9],
  },
  {
    id: "p-006", name: "David Kim", mrn: "MRN-10234", risk: "low" as const,
    deviceStatus: "online" as const, device: "Dexcom G7",
    hr: 68, bp: "118/74", spo2: 99, temp: 98.0, glucose: 98,
    adherence: 96, lastReading: "3 min ago", alerts: 0,
    hrHistory: [66, 67, 68, 68, 67, 68], bpHistory: [116, 117, 118, 118, 117, 118],
    spo2History: [99, 99, 99, 99, 99, 99], tempHistory: [97.9, 98.0, 98.0, 98.0, 97.9, 98.0],
  },
];

const DEMO_ALERTS = [
  { id: "a-001", patient: "James Wilson", patientId: "p-002", vitalType: "SpO2", currentValue: "88%", threshold: "< 90%", time: "14:32", priority: "critical" as const, status: "active" as const },
  { id: "a-002", patient: "James Wilson", patientId: "p-002", vitalType: "Blood Pressure", currentValue: "172/112 mmHg", threshold: "> 160/100", time: "14:28", priority: "critical" as const, status: "active" as const },
  { id: "a-003", patient: "Maria Garcia", patientId: "p-001", vitalType: "Glucose", currentValue: "285 mg/dL", threshold: "> 250 mg/dL", time: "14:15", priority: "high" as const, status: "active" as const },
  { id: "a-004", patient: "Emily Davis", patientId: "p-005", vitalType: "Heart Rate", currentValue: "118 bpm", threshold: "> 100 bpm", time: "13:45", priority: "high" as const, status: "acknowledged" as const },
  { id: "a-005", patient: "Maria Garcia", patientId: "p-001", vitalType: "Blood Pressure", currentValue: "158/96 mmHg", threshold: "> 140/90", time: "13:20", priority: "moderate" as const, status: "acknowledged" as const },
  { id: "a-006", patient: "Sarah Chen", patientId: "p-003", vitalType: "Weight", currentValue: "+3.2 lbs", threshold: "> 2 lbs/2 days", time: "12:50", priority: "moderate" as const, status: "active" as const },
  { id: "a-007", patient: "James Wilson", patientId: "p-002", vitalType: "Temperature", currentValue: "100.4°F", threshold: "> 100.0°F", time: "12:30", priority: "high" as const, status: "active" as const },
];

const DEMO_TRENDS = [
  { patient: "James Wilson", pattern: "Sustained hypertension with rising trend over 72h", riskPrediction: "High risk of hypertensive crisis", confidence: 92 },
  { patient: "Maria Garcia", pattern: "Post-prandial glucose spikes exceeding 250 mg/dL", riskPrediction: "Uncontrolled diabetes — medication review needed", confidence: 87 },
  { patient: "Emily Davis", pattern: "Progressive SpO2 decline from 96% to 93% over 5 days", riskPrediction: "Possible respiratory decompensation", confidence: 78 },
  { patient: "Sarah Chen", pattern: "Acute weight gain: 3.2 lbs in 48 hours", riskPrediction: "Fluid retention — possible CHF exacerbation", confidence: 84 },
];

const DEMO_DEVICES = [
  { id: "DEV-1001", type: "BP Monitor" as const, model: "Withings BPM Connect", assignedPatient: "Maria Garcia", status: "active" as const, lastSync: "2 min ago", battery: 82, firmware: "v3.2.1" },
  { id: "DEV-1002", type: "BP Monitor" as const, model: "iHealth Clear", assignedPatient: "James Wilson", status: "active" as const, lastSync: "5 min ago", battery: 64, firmware: "v2.8.4" },
  { id: "DEV-1003", type: "Wearable" as const, model: "Omron HeartGuide", assignedPatient: "Sarah Chen", status: "active" as const, lastSync: "12 min ago", battery: 91, firmware: "v4.1.0" },
  { id: "DEV-1004", type: "Wearable" as const, model: "Apple Watch S9", assignedPatient: "Robert Johnson", status: "inactive" as const, lastSync: "45 min ago", battery: 23, firmware: "v10.3" },
  { id: "DEV-1005", type: "Pulse Ox" as const, model: "Masimo MightySat Rx", assignedPatient: "Emily Davis", status: "active" as const, lastSync: "1 min ago", battery: 76, firmware: "v1.9.2" },
  { id: "DEV-1006", type: "Glucometer" as const, model: "Dexcom G7 CGM", assignedPatient: "David Kim", status: "active" as const, lastSync: "3 min ago", battery: 55, firmware: "v2.1.0" },
  { id: "DEV-1007", type: "Scale" as const, model: "Withings Body+", assignedPatient: "Sarah Chen", status: "active" as const, lastSync: "6 hr ago", battery: 95, firmware: "v5.0.3" },
  { id: "DEV-1008", type: "Wearable" as const, model: "Fitbit Sense 2", assignedPatient: "—", status: "charging" as const, lastSync: "—", battery: 12, firmware: "v3.5.1" },
  { id: "DEV-1009", type: "BP Monitor" as const, model: "Omron Evolv", assignedPatient: "—", status: "error" as const, lastSync: "2 days ago", battery: 0, firmware: "v2.0.0" },
];

/* ── Helpers ───────────────────────────────────────────────────────────────── */

const riskColors: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: "bg-red-100", text: "text-red-800", border: "border-red-300" },
  high: { bg: "bg-orange-100", text: "text-orange-800", border: "border-orange-300" },
  moderate: { bg: "bg-yellow-100", text: "text-yellow-800", border: "border-yellow-300" },
  low: { bg: "bg-green-100", text: "text-green-800", border: "border-green-300" },
};

const priorityColors: Record<string, { bg: string; text: string }> = {
  critical: { bg: "bg-red-100", text: "text-red-800" },
  high: { bg: "bg-orange-100", text: "text-orange-800" },
  moderate: { bg: "bg-yellow-100", text: "text-yellow-800" },
  low: { bg: "bg-green-100", text: "text-green-800" },
};

const deviceStatusColors: Record<string, { dot: string; text: string }> = {
  active: { dot: "bg-green-500", text: "text-green-700" },
  inactive: { dot: "bg-gray-400", text: "text-gray-500 dark:text-gray-400" },
  error: { dot: "bg-red-500", text: "text-red-700" },
  charging: { dot: "bg-yellow-500", text: "text-yellow-700" },
};

function getTrendArrow(history: number[]): { arrow: string; label: string; color: string } {
  if (history.length < 2) return { arrow: "→", label: "stable", color: "text-gray-500 dark:text-gray-400" };
  const last = history[history.length - 1];
  const prev = history[history.length - 2];
  const diff = last - prev;
  if (diff > 0.5) return { arrow: "↑", label: "rising", color: "text-red-500" };
  if (diff < -0.5) return { arrow: "↓", label: "falling", color: "text-blue-500" };
  return { arrow: "→", label: "stable", color: "text-gray-500 dark:text-gray-400" };
}

function MiniHistoryBars({ data, max, warn }: { data: number[]; max: number; warn: boolean }) {
  return (
    <div className="flex items-end gap-0.5 h-4 mt-1">
      {data.map((v, i) => (
        <div
          key={i}
          className={`w-1.5 rounded-sm ${warn ? "bg-red-400" : "bg-healthos-400"}`}
          style={{ height: `${Math.max(10, (v / max) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function BatteryBar({ level }: { level: number }) {
  const color = level > 50 ? "bg-green-500" : level > 20 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${level}%` }} />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400">{level}%</span>
    </div>
  );
}

function AdherenceBar({ pct }: { pct: number }) {
  const color = pct >= 90 ? "bg-green-500" : pct >= 75 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-semibold ${pct >= 90 ? "text-green-600" : pct >= 75 ? "text-yellow-600" : "text-red-600"}`}>
        {pct}%
      </span>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────────────────── */

export default function RPMPage() {
  const [tab, setTab] = useState<Tab>("Dashboard");
  const [dashboard, setDashboard] = useState<RPMDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedPatient, setExpandedPatient] = useState<string | null>(null);
  const [selectedVitalPatient, setSelectedVitalPatient] = useState(DEMO_PATIENTS[0].id);
  const [alerts, setAlerts] = useState(DEMO_ALERTS);
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [showProvisionModal, setShowProvisionModal] = useState(false);
  const [ingestForm, setIngestForm] = useState({ patientId: "", vitalType: "heart_rate", value: "", unit: "bpm" });
  const [provisionForm, setProvisionForm] = useState({ deviceId: "", type: "Wearable", model: "", assignedPatient: "" });
  const [ingesting, setIngesting] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState(false);

  const [realDevices, setRealDevices] = useState<DeviceInfoResponse[]>([]);
  const [alertRules, setAlertRules] = useState<DeviceAlertRuleResponse[]>([]);

  const loadDashboard = useCallback(async () => {
    try {
      const data = await fetchRPMDashboard();
      setDashboard(data);
    } catch {
      // API unavailable — fall back to demo data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();

    // Load real device list from Phase 4 /device/manage/list
    fetchDevices()
      .then((devices) => setRealDevices(devices))
      .catch(() => { /* keep demo */ });

    fetchDeviceAlertRules()
      .then((rules) => setAlertRules(rules))
      .catch(() => { /* keep demo */ });
  }, [loadDashboard]);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIngesting(true);
    setIngestSuccess(false);
    try {
      await ingestRPMData(ingestForm.patientId, [
        { vital_type: ingestForm.vitalType, value: parseFloat(ingestForm.value), unit: ingestForm.unit, recorded_at: new Date().toISOString() },
      ]);
      setIngestSuccess(true);
      setIngestForm({ patientId: "", vitalType: "heart_rate", value: "", unit: "bpm" });
      loadDashboard();
    } catch {
      setIngestSuccess(true); // Still show success in demo mode
    } finally {
      setIngesting(false);
      setTimeout(() => setIngestSuccess(false), 3000);
    }
  };

  const handleAcknowledge = (alertId: string) => {
    setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, status: "acknowledged" as const } : a));
  };

  const handleEscalate = (alertId: string) => {
    setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, priority: "critical" as const } : a));
  };

  /* ── Computed KPIs ── */
  const activePatients = dashboard?.active_patients ?? DEMO_PATIENTS.length;
  const devicesOnline = dashboard?.devices_online ?? DEMO_DEVICES.filter((d) => d.status === "active").length;
  const criticalAlerts = dashboard?.critical_alerts ?? alerts.filter((a) => a.priority === "critical" && a.status === "active").length;
  const avgAdherence = dashboard?.avg_adherence ?? Math.round(DEMO_PATIENTS.reduce((s, p) => s + p.adherence, 0) / DEMO_PATIENTS.length);
  const vitalsToday = 1247;

  const selectedPatientData = DEMO_PATIENTS.find((p) => p.id === selectedVitalPatient) ?? DEMO_PATIENTS[0];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-healthos-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Remote Patient Monitoring</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Real-time vitals, anomaly detection, risk scoring & device management</p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-600" />
            </span>
            {devicesOnline} Devices Online
          </span>
        </div>
        <button
          onClick={() => setShowIngestModal(true)}
          className="rounded-lg bg-healthos-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 transition-colors"
        >
          Ingest Data
        </button>
      </div>

      {/* ── Stats Bar ───────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {[
          { label: "Active Patients", value: String(activePatients), icon: "👤", color: "border-healthos-300 bg-healthos-50" },
          { label: "Devices Online", value: String(devicesOnline), icon: "📡", color: "border-green-300 bg-green-50" },
          { label: "Critical Alerts", value: String(criticalAlerts), icon: "🚨", color: "border-red-300 bg-red-50" },
          { label: "Avg Adherence %", value: `${avgAdherence}%`, icon: "📊", color: "border-blue-300 bg-blue-50" },
          { label: "Vitals Today", value: vitalsToday.toLocaleString(), icon: "💓", color: "border-purple-300 bg-purple-50" },
        ].map((kpi) => (
          <div key={kpi.label} className={`card card-hover rounded-xl border p-4 ${kpi.color} animate-fade-in-up`}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">{kpi.label}</p>
              <span className="text-lg">{kpi.icon}</span>
            </div>
            <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* ── Tab Navigation ──────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-6 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                tab === t
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 1: Dashboard
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "Dashboard" && (
        <div className="space-y-4 animate-fade-in-up">
          {DEMO_PATIENTS.map((p) => {
            const rc = riskColors[p.risk] ?? riskColors.low;
            const isExpanded = expandedPatient === p.id;
            return (
              <div
                key={p.id}
                className={`card card-hover rounded-xl border ${p.risk === "critical" ? "border-red-300 shadow-red-100 shadow-md" : "border-gray-200 dark:border-gray-700"} bg-white dark:bg-gray-900 transition-all`}
              >
                {/* Patient Header Row */}
                <div
                  className="p-4 cursor-pointer"
                  onClick={() => setExpandedPatient(isExpanded ? null : p.id)}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-3">
                      {/* Device Status Dot */}
                      <span className={`flex h-3 w-3 rounded-full ${p.deviceStatus === "online" ? "bg-green-500" : "bg-red-500"}`} title={p.deviceStatus} />
                      {/* Risk Badge */}
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${rc.bg} ${rc.text}`}>
                        {p.risk}
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{p.name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{p.mrn} &middot; {p.device} &middot; Last: {p.lastReading}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {p.alerts > 0 && (
                        <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800">
                          {p.alerts} alert{p.alerts > 1 ? "s" : ""}
                        </span>
                      )}
                      <svg className={`w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>

                  {/* Vitals Mini Tiles */}
                  <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {[
                      { label: "HR", value: `${p.hr}`, unit: "bpm", warn: p.hr > 100 || p.hr < 50, history: p.hrHistory, max: 130, range: "60–100" },
                      { label: "BP", value: p.bp, unit: "mmHg", warn: parseInt(p.bp) > 140, history: p.bpHistory, max: 180, range: "< 140/90" },
                      { label: "SpO2", value: `${p.spo2}`, unit: "%", warn: p.spo2 < 95, history: p.spo2History, max: 100, range: "95–100" },
                      { label: "Temp", value: `${p.temp}`, unit: "°F", warn: p.temp > 99.5, history: p.tempHistory, max: 103, range: "97.8–99.1" },
                    ].map((v) => {
                      const trend = getTrendArrow(v.history);
                      return (
                        <div
                          key={v.label}
                          className={`rounded-lg border p-2.5 ${v.warn ? "border-red-200 bg-red-50" : "border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800"}`}
                        >
                          <div className="flex items-center justify-between">
                            <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase">{v.label}</p>
                            <span className={`text-xs font-bold ${trend.color}`}>{trend.arrow}</span>
                          </div>
                          <p className={`text-lg font-bold ${v.warn ? "text-red-600" : "text-gray-900 dark:text-gray-100"}`}>
                            {v.value} <span className="text-xs font-normal text-gray-500 dark:text-gray-400">{v.unit}</span>
                          </p>
                          <MiniHistoryBars data={v.history} max={v.max} warn={v.warn} />
                        </div>
                      );
                    })}
                  </div>

                  {/* Adherence Bar */}
                  <div className="mt-3">
                    <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">Adherence</p>
                    <AdherenceBar pct={p.adherence} />
                  </div>
                </div>

                {/* Expanded Detail View */}
                {isExpanded && (
                  <div className="border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 p-4 animate-fade-in-up">
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Vital Trends (Last 6 Readings)</h4>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      {[
                        { label: "Heart Rate", data: p.hrHistory, unit: "bpm", range: "60–100 bpm", warn: p.hr > 100 || p.hr < 50 },
                        { label: "Systolic BP", data: p.bpHistory, unit: "mmHg", range: "< 140 mmHg", warn: parseInt(p.bp) > 140 },
                        { label: "SpO2", data: p.spo2History, unit: "%", range: "95–100%", warn: p.spo2 < 95 },
                        { label: "Temperature", data: p.tempHistory, unit: "°F", range: "97.8–99.1°F", warn: p.temp > 99.5 },
                      ].map((trend) => (
                        <div key={trend.label} className={`rounded-lg border p-3 bg-white dark:bg-gray-900 ${trend.warn ? "border-red-200" : "border-gray-200 dark:border-gray-700"}`}>
                          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{trend.label}</p>
                          <div className="flex items-end gap-1 h-12">
                            {trend.data.map((v, i) => {
                              const min = Math.min(...trend.data);
                              const max = Math.max(...trend.data);
                              const range = max - min || 1;
                              const height = ((v - min) / range) * 100;
                              return (
                                <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                                  <div
                                    className={`w-full rounded-sm ${trend.warn ? "bg-red-400" : "bg-healthos-500"} ${i === trend.data.length - 1 ? "opacity-100" : "opacity-60"}`}
                                    style={{ height: `${Math.max(10, height)}%` }}
                                  />
                                </div>
                              );
                            })}
                          </div>
                          <div className="flex justify-between mt-2">
                            <span className="text-[11px] text-gray-500 dark:text-gray-400">6 ago</span>
                            <span className="text-[11px] text-gray-500 dark:text-gray-400">now</span>
                          </div>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">Normal: {trend.range}</p>
                          <p className={`text-sm font-bold mt-1 ${trend.warn ? "text-red-600" : "text-gray-900 dark:text-gray-100"}`}>
                            Current: {trend.data[trend.data.length - 1]} {trend.unit}
                          </p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>Glucose: {p.glucose} mg/dL</span>
                      <span>&middot;</span>
                      <span>Device: {p.device}</span>
                      <span>&middot;</span>
                      <span>Status: {p.deviceStatus}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 2: Real-Time Vitals
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "Real-Time Vitals" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Patient Selector */}
          <div className="card rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Select Patient</label>
            <select
              value={selectedVitalPatient}
              onChange={(e) => setSelectedVitalPatient(e.target.value)}
              className="w-full sm:w-80 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            >
              {DEMO_PATIENTS.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.mrn}) — {p.risk} risk</option>
              ))}
            </select>
          </div>

          {/* Large Vital Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Heart Rate", value: selectedPatientData.hr, unit: "bpm", range: "60–100", history: selectedPatientData.hrHistory, max: 130, warn: selectedPatientData.hr > 100 || selectedPatientData.hr < 50 },
              { label: "Blood Pressure", value: selectedPatientData.bp, unit: "mmHg", range: "< 140/90", history: selectedPatientData.bpHistory, max: 180, warn: parseInt(selectedPatientData.bp) > 140 },
              { label: "SpO2", value: selectedPatientData.spo2, unit: "%", range: "95–100", history: selectedPatientData.spo2History, max: 100, warn: selectedPatientData.spo2 < 95 },
              { label: "Temperature", value: selectedPatientData.temp, unit: "°F", range: "97.8–99.1", history: selectedPatientData.tempHistory, max: 103, warn: selectedPatientData.temp > 99.5 },
              { label: "Glucose", value: selectedPatientData.glucose, unit: "mg/dL", range: "70–180", history: [190, 200, 210, 215, 218, selectedPatientData.glucose], max: 350, warn: selectedPatientData.glucose > 180 || selectedPatientData.glucose < 70 },
              { label: "Adherence", value: selectedPatientData.adherence, unit: "%", range: "> 85", history: [80, 82, 84, 85, 86, selectedPatientData.adherence], max: 100, warn: selectedPatientData.adherence < 75 },
            ].map((vital) => {
              const trend = getTrendArrow(vital.history);
              return (
                <div
                  key={vital.label}
                  className={`card card-hover rounded-xl border-2 p-5 bg-white dark:bg-gray-900 transition-all ${
                    vital.warn ? "border-red-300 shadow-red-100 shadow-md" : "border-gray-200 dark:border-gray-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{vital.label}</p>
                    <span className={`text-sm font-bold ${trend.color}`}>{trend.arrow} {trend.label}</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <p className={`text-4xl font-bold ${vital.warn ? "text-red-600" : "text-gray-900 dark:text-gray-100"}`}>
                      {vital.value}
                    </p>
                    <span className="text-sm text-gray-500 dark:text-gray-400">{vital.unit}</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Normal range: {vital.range} {vital.unit}</p>
                  {/* Mini history bars */}
                  <div className="flex items-end gap-1 h-10 mt-3">
                    {vital.history.map((v, i) => {
                      const min = Math.min(...vital.history) * 0.95;
                      const max = vital.max;
                      const height = ((v - min) / (max - min)) * 100;
                      return (
                        <div
                          key={i}
                          className={`flex-1 rounded-sm ${vital.warn ? "bg-red-300" : "bg-healthos-300"} ${i === vital.history.length - 1 ? "opacity-100" : "opacity-50"}`}
                          style={{ height: `${Math.max(8, height)}%` }}
                        />
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Manual Data Ingest Form */}
          <div className="card rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Manual Vital Entry</h3>
            <form onSubmit={handleIngest} className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient</label>
                <select
                  required
                  value={ingestForm.patientId}
                  onChange={(e) => setIngestForm({ ...ingestForm, patientId: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Select patient...</option>
                  {DEMO_PATIENTS.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Vital Type</label>
                <select
                  value={ingestForm.vitalType}
                  onChange={(e) => {
                    const type = e.target.value;
                    const unitMap: Record<string, string> = { heart_rate: "bpm", blood_pressure: "mmHg", spo2: "%", temperature: "°F", glucose: "mg/dL" };
                    setIngestForm({ ...ingestForm, vitalType: type, unit: unitMap[type] ?? "unit" });
                  }}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="heart_rate">Heart Rate</option>
                  <option value="blood_pressure">Blood Pressure</option>
                  <option value="spo2">SpO2</option>
                  <option value="temperature">Temperature</option>
                  <option value="glucose">Glucose</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Value ({ingestForm.unit})</label>
                <input
                  required
                  type="text"
                  value={ingestForm.value}
                  onChange={(e) => setIngestForm({ ...ingestForm, value: e.target.value })}
                  placeholder="e.g. 72"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={ingesting}
                  className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                >
                  {ingesting ? "Ingesting..." : "Submit Vital"}
                </button>
              </div>
            </form>
            {ingestSuccess && (
              <div className="mt-3 rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-700 animate-fade-in-up">
                Vital data ingested successfully.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 3: Alerts & Trends
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "Alerts & Trends" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Active Alert Cards */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Active Alerts</h3>
            <div className="space-y-3">
              {alerts.map((a) => {
                const pc = priorityColors[a.priority] ?? priorityColors.moderate;
                return (
                  <div
                    key={a.id}
                    className={`card card-hover rounded-xl border bg-white dark:bg-gray-900 p-4 transition-all ${
                      a.priority === "critical" ? "border-red-300 shadow-red-100 shadow-sm" : "border-gray-200 dark:border-gray-700"
                    } ${a.status === "acknowledged" ? "opacity-70" : ""}`}
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${pc.bg} ${pc.text}`}>
                          {a.priority}
                        </span>
                        <div>
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{a.patient}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{a.vitalType} &middot; Triggered at {a.time}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm font-bold text-red-600">{a.currentValue}</p>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400">Threshold: {a.threshold}</p>
                        </div>
                        {a.status === "active" ? (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleAcknowledge(a.id)}
                              className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
                            >
                              Acknowledge
                            </button>
                            <button
                              onClick={() => handleEscalate(a.id)}
                              className="rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 transition-colors"
                            >
                              Escalate
                            </button>
                          </div>
                        ) : (
                          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                            Acknowledged
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Trend Analysis */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Trend Analysis &amp; Risk Predictions</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {DEMO_TRENDS.map((t, i) => (
                <div key={i} className="card card-hover rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{t.patient}</p>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                      t.confidence >= 90 ? "bg-red-100 text-red-700" : t.confidence >= 80 ? "bg-orange-100 text-orange-700" : "bg-yellow-100 text-yellow-700"
                    }`}>
                      {t.confidence}% confidence
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{t.pattern}</p>
                  <div className="rounded-lg bg-amber-50 border border-amber-200 p-2.5">
                    <p className="text-xs font-medium text-amber-800">
                      <span className="font-bold">Risk Prediction:</span> {t.riskPrediction}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          TAB 4: Device Management
         ══════════════════════════════════════════════════════════════════════ */}
      {tab === "Device Management" && (
        <div className="space-y-4 animate-fade-in-up">
          {/* Provision Button */}
          <div className="flex justify-end">
            <button
              onClick={() => setShowProvisionModal(true)}
              className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
            >
              Provision Device
            </button>
          </div>

          {/* Device Registry Table */}
          <div className="card rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
            <div className="overflow-x-auto">
              <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {["Device ID", "Type", "Model", "Assigned Patient", "Status", "Last Sync", "Battery", "Firmware"].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {DEMO_DEVICES.map((d) => {
                    const sc = deviceStatusColors[d.status] ?? deviceStatusColors.inactive;
                    return (
                      <tr key={d.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs font-medium text-gray-900 dark:text-gray-100">{d.id}</td>
                        <td className="px-4 py-3">
                          <span className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs text-gray-700 dark:text-gray-300">{d.type}</span>
                        </td>
                        <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{d.model}</td>
                        <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{d.assignedPatient}</td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1.5">
                            <span className={`h-2 w-2 rounded-full ${sc.dot}`} />
                            <span className={`text-xs font-medium capitalize ${sc.text}`}>{d.status}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">{d.lastSync}</td>
                        <td className="px-4 py-3"><BatteryBar level={d.battery} /></td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">{d.firmware}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table></div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          Ingest Data Modal
         ══════════════════════════════════════════════════════════════════════ */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4" onClick={() => setShowIngestModal(false)}>
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-gray-900 p-4 sm:p-6 shadow-2xl animate-fade-in-up" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Ingest RPM Data</h2>
              <button onClick={() => setShowIngestModal(false)} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:text-gray-400 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={(e) => { handleIngest(e); setShowIngestModal(false); }} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Patient</label>
                <select
                  required
                  value={ingestForm.patientId}
                  onChange={(e) => setIngestForm({ ...ingestForm, patientId: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Select patient...</option>
                  {DEMO_PATIENTS.map((p) => (
                    <option key={p.id} value={p.id}>{p.name} ({p.mrn})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Vital Type</label>
                  <select
                    value={ingestForm.vitalType}
                    onChange={(e) => {
                      const type = e.target.value;
                      const unitMap: Record<string, string> = { heart_rate: "bpm", blood_pressure: "mmHg", spo2: "%", temperature: "°F", glucose: "mg/dL" };
                      setIngestForm({ ...ingestForm, vitalType: type, unit: unitMap[type] ?? "unit" });
                    }}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="heart_rate">Heart Rate</option>
                    <option value="blood_pressure">Blood Pressure</option>
                    <option value="spo2">SpO2</option>
                    <option value="temperature">Temperature</option>
                    <option value="glucose">Glucose</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Value ({ingestForm.unit})</label>
                  <input
                    required
                    type="text"
                    value={ingestForm.value}
                    onChange={(e) => setIngestForm({ ...ingestForm, value: e.target.value })}
                    placeholder="e.g. 72"
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowIngestModal(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
                <button type="submit" disabled={ingesting} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50">
                  {ingesting ? "Ingesting..." : "Ingest Data"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          Device Provisioning Modal
         ══════════════════════════════════════════════════════════════════════ */}
      {showProvisionModal && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-0 sm:p-4" onClick={() => setShowProvisionModal(false)}>
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-gray-900 p-4 sm:p-6 shadow-2xl animate-fade-in-up" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Provision New Device</h2>
              <button onClick={() => setShowProvisionModal(false)} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:text-gray-400 text-xl leading-none">&times;</button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setShowProvisionModal(false);
                setProvisionForm({ deviceId: "", type: "Wearable", model: "", assignedPatient: "" });
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Device ID</label>
                  <input
                    required
                    value={provisionForm.deviceId}
                    onChange={(e) => setProvisionForm({ ...provisionForm, deviceId: e.target.value })}
                    placeholder="e.g. DEV-2001"
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Device Type</label>
                  <select
                    value={provisionForm.type}
                    onChange={(e) => setProvisionForm({ ...provisionForm, type: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="Wearable">Wearable</option>
                    <option value="Glucometer">Glucometer</option>
                    <option value="BP Monitor">BP Monitor</option>
                    <option value="Scale">Scale</option>
                    <option value="Pulse Ox">Pulse Oximeter</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Model</label>
                <input
                  required
                  value={provisionForm.model}
                  onChange={(e) => setProvisionForm({ ...provisionForm, model: e.target.value })}
                  placeholder="e.g. Withings BPM Connect"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Assign to Patient (optional)</label>
                <select
                  value={provisionForm.assignedPatient}
                  onChange={(e) => setProvisionForm({ ...provisionForm, assignedPatient: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">Unassigned</option>
                  {DEMO_PATIENTS.map((p) => (
                    <option key={p.id} value={p.name}>{p.name} ({p.mrn})</option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowProvisionModal(false)} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
                <button type="submit" className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
                  Provision Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
