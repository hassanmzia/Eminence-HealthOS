"use client";

import { useState } from "react";

const TABS = ["Results", "Orders", "Trends", "Critical Alerts"] as const;

const LAB_RESULTS = [
  { test: "Glucose", value: 118, unit: "mg/dL", range: "70-100", flag: "High", date: "2026-03-12" },
  { test: "BUN", value: 22, unit: "mg/dL", range: "7-20", flag: "High", date: "2026-03-12" },
  { test: "Creatinine", value: 1.4, unit: "mg/dL", range: "0.6-1.2", flag: "High", date: "2026-03-12" },
  { test: "Sodium", value: 141, unit: "mEq/L", range: "136-145", flag: "Normal", date: "2026-03-12" },
  { test: "Potassium", value: 5.2, unit: "mEq/L", range: "3.5-5.0", flag: "High", date: "2026-03-12" },
  { test: "HbA1c", value: 7.3, unit: "%", range: "4.0-5.6", flag: "High", date: "2026-03-12" },
  { test: "eGFR", value: 52, unit: "mL/min/1.73m2", range: ">60", flag: "Low", date: "2026-03-12" },
  { test: "Hemoglobin", value: 13.5, unit: "g/dL", range: "12.0-17.5", flag: "Normal", date: "2026-03-12" },
];

const LAB_ORDERS = [
  { id: "LO-2026-0089", patient: "Maria Garcia", panels: "BMP, HbA1c, Lipid", priority: "Routine", status: "Results Available", ordered: "2026-03-10", provider: "Dr. Patel" },
  { id: "LO-2026-0090", patient: "James Wilson", panels: "CBC, CMP", priority: "Routine", status: "Processing", ordered: "2026-03-11", provider: "Dr. Kim" },
  { id: "LO-2026-0091", patient: "Robert Johnson", panels: "PT/INR", priority: "Urgent", status: "Specimen Collected", ordered: "2026-03-12", provider: "Dr. Patel" },
  { id: "LO-2026-0092", patient: "Emily Davis", panels: "TSH, Renal Panel", priority: "Routine", status: "Ordered", ordered: "2026-03-12", provider: "Dr. Williams" },
];

const TREND_DATA = [
  { test: "HbA1c", values: [6.8, 7.0, 7.1, 7.3], dates: ["Jun 25", "Sep 25", "Dec 25", "Mar 26"], direction: "Increasing", concern: true, note: "Worsening glycemic control" },
  { test: "eGFR", values: [68, 62, 56, 52], dates: ["Jun 25", "Sep 25", "Dec 25", "Mar 26"], direction: "Decreasing", concern: true, note: "Progressive CKD Stage 3b" },
  { test: "Potassium", values: [4.2, 4.5, 4.8, 5.2], dates: ["Jun 25", "Sep 25", "Dec 25", "Mar 26"], direction: "Increasing", concern: true, note: "Approaching upper limit" },
  { test: "LDL", values: [105, 98, 95, 95], dates: ["Jun 25", "Sep 25", "Dec 25", "Mar 26"], direction: "Stable", concern: false, note: "At target on statin therapy" },
];

const CRITICAL_ALERTS = [
  { date: "2026-03-12 14:30", test: "Potassium", value: 6.8, unit: "mEq/L", urgency: "Immediate", response_min: 12, acknowledged_by: "Dr. Williams", status: "Acknowledged" },
  { date: "2026-03-10 08:15", test: "Glucose", value: 42, unit: "mg/dL", urgency: "Immediate", response_min: 8, acknowledged_by: "Dr. Patel", status: "Acknowledged" },
  { date: "2026-03-05 22:00", test: "Troponin", value: 0.12, unit: "ng/mL", urgency: "Stat", response_min: 4, acknowledged_by: "Dr. Kim", status: "Acknowledged" },
];

function flagColor(flag: string) {
  const map: Record<string, string> = {
    High: "bg-red-100 text-red-800",
    Low: "bg-yellow-100 text-yellow-800",
    Normal: "bg-green-100 text-green-800",
    Critical: "bg-red-200 text-red-900",
  };
  return map[flag] ?? "bg-gray-100 text-gray-800";
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    "Results Available": "bg-green-100 text-green-800",
    Processing: "bg-blue-100 text-blue-800",
    "Specimen Collected": "bg-yellow-100 text-yellow-800",
    Ordered: "bg-gray-100 text-gray-800",
    Acknowledged: "bg-green-100 text-green-800",
    Pending: "bg-red-100 text-red-800",
  };
  return map[status] ?? "bg-gray-100 text-gray-800";
}

function urgencyColor(u: string) {
  const map: Record<string, string> = { Stat: "bg-red-200 text-red-900", Immediate: "bg-red-100 text-red-800", Urgent: "bg-yellow-100 text-yellow-800" };
  return map[u] ?? "bg-gray-100 text-gray-800";
}

export default function LabsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Labs</h1>
        <p className="text-sm text-gray-500">Lab orders, results, trend analysis, and CLIA-compliant critical value alerting</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Pending Orders", value: "12", sub: "3 urgent" },
          { label: "Results Today", value: "47", sub: "8 abnormal" },
          { label: "Critical Alerts", value: "3", sub: "All acknowledged" },
          { label: "Avg Response Time", value: "8 min", sub: "Target: 30 min" },
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
        <nav className="-mb-px flex gap-4">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                tab === t ? "border-healthos-600 text-healthos-600" : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {tab === "Results" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Test", "Value", "Unit", "Reference Range", "Flag", "Date"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {LAB_RESULTS.map((r) => (
                <tr key={r.test} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.test}</td>
                  <td className="px-4 py-3 font-mono font-semibold">{r.value}</td>
                  <td className="px-4 py-3 text-gray-500">{r.unit}</td>
                  <td className="px-4 py-3 text-gray-500">{r.range}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${flagColor(r.flag)}`}>{r.flag}</span></td>
                  <td className="px-4 py-3 text-gray-500">{r.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Orders" && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Order ID", "Patient", "Panels", "Priority", "Provider", "Ordered", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {LAB_ORDERS.map((o) => (
                <tr key={o.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{o.id}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{o.patient}</td>
                  <td className="px-4 py-3">{o.panels}</td>
                  <td className="px-4 py-3">{o.priority}</td>
                  <td className="px-4 py-3">{o.provider}</td>
                  <td className="px-4 py-3 text-gray-500">{o.ordered}</td>
                  <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(o.status)}`}>{o.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Trends" && (
        <div className="space-y-4">
          {TREND_DATA.map((t) => (
            <div key={t.test} className={`rounded-lg border p-4 ${t.concern ? "border-red-200 bg-red-50" : "border-gray-200 bg-white"}`}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{t.test}</h3>
                  <p className="text-sm text-gray-500">{t.note}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  t.direction === "Increasing" ? "bg-red-100 text-red-800" :
                  t.direction === "Decreasing" ? "bg-yellow-100 text-yellow-800" :
                  "bg-green-100 text-green-800"
                }`}>{t.direction}</span>
              </div>
              <div className="mt-3 flex gap-6 text-sm">
                {t.values.map((v, i) => (
                  <div key={i} className="text-center">
                    <p className="font-mono font-semibold text-gray-900">{v}</p>
                    <p className="text-xs text-gray-400">{t.dates[i]}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "Critical Alerts" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900">CLIA Critical Value Log</h3>
            <p className="text-xs text-gray-500">Average response time: 8 min | All within 30-min target</p>
          </div>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Date/Time", "Test", "Value", "Urgency", "Response (min)", "Acknowledged By", "Status"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {CRITICAL_ALERTS.map((a, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{a.date}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{a.test}</td>
                    <td className="px-4 py-3 font-mono font-semibold">{a.value} {a.unit}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${urgencyColor(a.urgency)}`}>{a.urgency}</span></td>
                    <td className="px-4 py-3 font-mono">{a.response_min}</td>
                    <td className="px-4 py-3">{a.acknowledged_by}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(a.status)}`}>{a.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
