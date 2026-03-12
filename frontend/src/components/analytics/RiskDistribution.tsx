"use client";

import { useState } from "react";

const RISK_DATA = [
  { level: "Critical", count: 142, pct: 5.0, color: "bg-red-500", bar: "bg-red-200" },
  { level: "High", count: 382, pct: 13.4, color: "bg-orange-500", bar: "bg-orange-200" },
  { level: "Moderate", count: 896, pct: 31.5, color: "bg-yellow-500", bar: "bg-yellow-200" },
  { level: "Low", count: 1427, pct: 50.1, color: "bg-green-500", bar: "bg-green-200" },
];

const RECOMMENDATIONS = [
  { tier: "Critical", action: "Daily monitoring, weekly provider review", patients: 142 },
  { tier: "High", action: "Twice-weekly monitoring, bi-weekly review", patients: 382 },
  { tier: "Moderate", action: "Weekly monitoring, monthly review", patients: 896 },
  { tier: "Low", action: "Monthly check-in, quarterly review", patients: 1427 },
];

export function RiskDistribution() {
  const [view, setView] = useState<"chart" | "recommendations">("chart");
  const total = RISK_DATA.reduce((s, d) => s + d.count, 0);

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Risk Stratification</h2>
        <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
          <button
            onClick={() => setView("chart")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${view === "chart" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
          >
            Distribution
          </button>
          <button
            onClick={() => setView("recommendations")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${view === "recommendations" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
          >
            Actions
          </button>
        </div>
      </div>

      {view === "chart" ? (
        <div className="space-y-3">
          {RISK_DATA.map((d) => (
            <div key={d.level}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${d.color}`} />
                  <span className="font-medium text-gray-900">{d.level}</span>
                </div>
                <span className="text-gray-500">
                  {d.count.toLocaleString()} ({d.pct}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-gray-100">
                <div
                  className={`h-2 rounded-full ${d.color}`}
                  style={{ width: `${(d.count / total) * 100}%` }}
                />
              </div>
            </div>
          ))}
          <p className="mt-2 text-xs text-gray-500">
            Total: {total.toLocaleString()} patients evaluated
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {RECOMMENDATIONS.map((r) => (
            <div key={r.tier} className="flex items-start gap-3 rounded-lg border border-gray-200 p-3">
              <span className={`mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full ${
                r.tier === "Critical" ? "bg-red-500" :
                r.tier === "High" ? "bg-orange-500" :
                r.tier === "Moderate" ? "bg-yellow-500" : "bg-green-500"
              }`} />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{r.tier}</span>
                  <span className="text-xs text-gray-500">{r.patients} patients</span>
                </div>
                <p className="mt-0.5 text-xs text-gray-600">{r.action}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
