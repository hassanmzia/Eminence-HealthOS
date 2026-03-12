"use client";

import { useState } from "react";

const KPI_DATA = [
  { label: "Total Billed (MTD)", value: "$485,000", change: "+8.2%" },
  { label: "Total Collected", value: "$428,000", change: "+5.7%" },
  { label: "Collection Rate", value: "96.2%", change: "+1.1%" },
  { label: "Clean Claim Rate", value: "94.8%", change: "+2.3%" },
  { label: "Denial Rate", value: "5.2%", change: "-1.8%" },
  { label: "Days in AR", value: "42.5", change: "-3.2" },
];

const CLAIMS_PIPELINE = [
  { id: "CLM-8921", patient: "Sarah Johnson", payer: "Blue Cross", amount: 425.00, status: "submitted", codes: "99214, 80048", submitted: "2026-03-12" },
  { id: "CLM-8920", patient: "Michael Chen", payer: "Aetna", amount: 285.50, status: "paid", codes: "99213, 85025", submitted: "2026-03-10" },
  { id: "CLM-8919", patient: "Emma Davis", payer: "UnitedHealth", amount: 1250.00, status: "denied", codes: "99215, 93000, 80053", submitted: "2026-03-08" },
  { id: "CLM-8918", patient: "Robert Wilson", payer: "Medicare", amount: 198.75, status: "paid", codes: "99213", submitted: "2026-03-07" },
  { id: "CLM-8917", patient: "Lisa Thompson", payer: "Cigna", amount: 680.00, status: "pending", codes: "99214, 80069", submitted: "2026-03-06" },
  { id: "CLM-8916", patient: "James Brown", payer: "Medicare", amount: 156.00, status: "paid", codes: "99212", submitted: "2026-03-05" },
];

const DENIAL_SUMMARY = [
  { reason: "Prior authorization missing", code: "CO-197", count: 28, amount: 18500, appealable: true },
  { reason: "Coding error / mismatch", code: "CO-4", count: 22, amount: 12300, appealable: true },
  { reason: "Eligibility issue", code: "CO-22", count: 19, amount: 9800, appealable: true },
  { reason: "Timely filing exceeded", code: "CO-29", count: 10, amount: 6200, appealable: true },
  { reason: "Duplicate claim", code: "CO-18", count: 8, amount: 3450, appealable: false },
];

const AR_BUCKETS = [
  { bucket: "0-30 days", claims: 245, amount: 187500, pct: 49.3 },
  { bucket: "31-60 days", claims: 128, amount: 96400, pct: 25.3 },
  { bucket: "61-90 days", claims: 67, amount: 52300, pct: 13.7 },
  { bucket: "91-120 days", claims: 34, amount: 28100, pct: 7.4 },
  { bucket: "120+ days", claims: 19, amount: 15800, pct: 4.2 },
];

const LEAKAGE_ITEMS = [
  { category: "Missed HCC codes", amount: 45200, encounters: 89 },
  { category: "Under-coded E&M levels", amount: 28350, encounters: 234 },
  { category: "Unbilled procedures", amount: 18900, encounters: 56 },
  { category: "Unbilled care coordination", amount: 12400, encounters: 148 },
  { category: "Missed modifier charges", amount: 8650, encounters: 42 },
];

const statusBadge = (s: string) => {
  const map: Record<string, string> = {
    submitted: "bg-blue-100 text-blue-700",
    paid: "bg-green-100 text-green-700",
    denied: "bg-red-100 text-red-700",
    pending: "bg-yellow-100 text-yellow-700",
    appealed: "bg-purple-100 text-purple-700",
  };
  return map[s] || "bg-gray-100 text-gray-600";
};

export default function RCMPage() {
  const [tab, setTab] = useState<"pipeline" | "denials" | "ar" | "leakage">("pipeline");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Revenue Cycle Management</h1>
          <p className="text-sm text-gray-500">End-to-end billing automation, claims optimization, and revenue integrity</p>
        </div>
        <div className="flex gap-2">
          <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Export Report</button>
          <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">New Claim</button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {KPI_DATA.map((k) => (
          <div key={k.label} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className="mt-1 text-xl font-bold text-gray-900">{k.value}</p>
            <p className={`text-xs mt-0.5 ${k.change.startsWith("+") || k.change.startsWith("-1") || k.change.startsWith("-2") || k.change.startsWith("-3") ? "text-green-600" : "text-red-600"}`}>{k.change} vs last month</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {(["pipeline", "denials", "ar", "leakage"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`border-b-2 pb-3 text-sm font-medium capitalize ${tab === t ? "border-healthos-600 text-healthos-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {t === "pipeline" ? "Claims Pipeline" : t === "denials" ? "Denial Management" : t === "ar" ? "AR Aging" : "Revenue Leakage"}
            </button>
          ))}
        </nav>
      </div>

      {/* Claims Pipeline */}
      {tab === "pipeline" && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["Claim ID", "Patient", "Payer", "Codes", "Amount", "Submitted", "Status", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {CLAIMS_PIPELINE.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-healthos-600">{c.id}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{c.patient}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.payer}</td>
                  <td className="px-4 py-3 text-xs font-mono text-gray-600">{c.codes}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">${c.amount.toFixed(2)}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.submitted}</td>
                  <td className="px-4 py-3"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge(c.status)}`}>{c.status}</span></td>
                  <td className="px-4 py-3">
                    {c.status === "denied" && (
                      <button className="rounded bg-orange-600 px-3 py-1 text-xs font-medium text-white hover:bg-orange-700">Appeal</button>
                    )}
                    {c.status === "submitted" && (
                      <button className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50">Track</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Denial Management */}
      {tab === "denials" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm font-medium text-red-800">87 claims denied this month — $50,250 at risk</p>
            <p className="text-xs text-red-600 mt-1">72 claims are appealable with estimated 70% recovery rate</p>
          </div>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Denial Reason", "CARC Code", "Count", "Amount", "Appealable", "Action"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {DENIAL_SUMMARY.map((d) => (
                  <tr key={d.code} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">{d.reason}</td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-600">{d.code}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{d.count}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">${d.amount.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${d.appealable ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                        {d.appealable ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {d.appealable && (
                        <button className="rounded bg-healthos-600 px-3 py-1 text-xs font-medium text-white hover:bg-healthos-700">Batch Appeal</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AR Aging */}
      {tab === "ar" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500">Total AR</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">$380,100</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500">Avg Days in AR</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">42.5</p>
              <p className="text-xs text-gray-400">Target: 35</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500">Over 90 Days</p>
              <p className="mt-1 text-2xl font-bold text-red-600">11.6%</p>
              <p className="text-xs text-gray-400">Target: &lt; 10%</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500">Total Claims</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">493</p>
            </div>
          </div>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Aging Bucket", "Claims", "Amount", "% of Total", "Bar"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {AR_BUCKETS.map((b) => (
                  <tr key={b.bucket} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{b.bucket}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{b.claims}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">${b.amount.toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{b.pct}%</td>
                    <td className="px-4 py-3 w-48">
                      <div className="h-3 w-full rounded-full bg-gray-100">
                        <div className={`h-3 rounded-full ${b.bucket.includes("120") || b.bucket.includes("91") ? "bg-red-400" : b.bucket.includes("61") ? "bg-yellow-400" : "bg-healthos-400"}`} style={{ width: `${b.pct}%` }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Revenue Leakage */}
      {tab === "leakage" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
            <p className="text-sm font-medium text-orange-800">$113,500 in identified revenue leakage this quarter</p>
            <p className="text-xs text-orange-600 mt-1">All identified leakage is recoverable with corrective action</p>
          </div>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Category", "Amount", "Encounters Affected", "% of Total", "Action"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {LEAKAGE_ITEMS.map((l) => (
                  <tr key={l.category} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{l.category}</td>
                    <td className="px-4 py-3 text-sm font-bold text-orange-600">${l.amount.toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{l.encounters}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{(l.amount / 1135).toFixed(1)}%</td>
                    <td className="px-4 py-3">
                      <button className="rounded border border-orange-300 px-3 py-1 text-xs font-medium text-orange-700 hover:bg-orange-50">Recover</button>
                    </td>
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
