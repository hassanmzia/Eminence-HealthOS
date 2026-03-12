"use client";

const ACHIEVEMENTS = [
  "30-day readmission rate decreased to 8.2% (target: <10%)",
  "SLA compliance at 91.7%, up 3.4% from prior period",
  "PMPM cost down to $262, first time below $270 target",
  "RPM program delivering 128.9% ROI",
];

const CONCERNS = [
  "Prior auth approval rate at 82.8% — below 90% target",
  "Referral completion rate at 78.6% — specialist response delays",
  "6 overdue SLA tasks in billing review queue",
];

const RECOMMENDATIONS = [
  "Expand RPM enrollment to capture additional 200 high-risk patients",
  "Implement dedicated prior auth specialist for top 3 payers",
  "Launch pharmacy optimization program for $95K potential savings",
];

const HEADLINE_KPIS = [
  { label: "Patients", value: "2,847" },
  { label: "PMPM Cost", value: "$262" },
  { label: "Quality", value: "0.82" },
  { label: "Net Margin", value: "27.8%" },
  { label: "RPM ROI", value: "128.9%" },
];

export function ExecutiveSummary() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-gray-900">Executive Summary</h2>
      <p className="mt-1 text-sm text-healthos-600 font-medium">
        Platform performance improving across key metrics with 8.1% cost reduction
      </p>

      {/* KPI strip */}
      <div className="my-4 grid grid-cols-5 gap-3">
        {HEADLINE_KPIS.map((kpi) => (
          <div key={kpi.label} className="rounded-lg bg-gray-50 p-3 text-center">
            <p className="text-xs text-gray-500">{kpi.label}</p>
            <p className="mt-0.5 text-xl font-bold text-gray-900">{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-green-700">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            Key Achievements
          </h3>
          <ul className="space-y-1.5">
            {ACHIEVEMENTS.map((a, i) => (
              <li key={i} className="text-xs text-gray-700 leading-relaxed">{a}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-red-700">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            Areas of Concern
          </h3>
          <ul className="space-y-1.5">
            {CONCERNS.map((c, i) => (
              <li key={i} className="text-xs text-gray-700 leading-relaxed">{c}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-blue-700">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            Recommendations
          </h3>
          <ul className="space-y-1.5">
            {RECOMMENDATIONS.map((r, i) => (
              <li key={i} className="text-xs text-gray-700 leading-relaxed">{r}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
