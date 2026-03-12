"use client";

const COST_DRIVERS = [
  { driver: "Inpatient Admissions", pct: 30, color: "bg-red-500" },
  { driver: "ED Visits", pct: 18, color: "bg-orange-500" },
  { driver: "Pharmacy", pct: 15, color: "bg-blue-500" },
  { driver: "Specialist Visits", pct: 12, color: "bg-purple-500" },
  { driver: "Readmissions", pct: 10, color: "bg-pink-500" },
  { driver: "Imaging", pct: 8, color: "bg-teal-500" },
  { driver: "Lab Tests", pct: 5, color: "bg-green-500" },
  { driver: "Post-Acute Care", pct: 2, color: "bg-gray-400" },
];

export function CostDriverChart() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-gray-900">Cost Drivers</h2>
      <p className="mb-4 text-xs text-gray-500">Breakdown by category</p>

      {/* Stacked bar */}
      <div className="mb-4 flex h-6 overflow-hidden rounded-full">
        {COST_DRIVERS.map((d) => (
          <div
            key={d.driver}
            className={d.color}
            style={{ width: `${d.pct}%` }}
            title={`${d.driver}: ${d.pct}%`}
          />
        ))}
      </div>

      <div className="space-y-2">
        {COST_DRIVERS.map((d) => (
          <div key={d.driver} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${d.color}`} />
              <span className="text-gray-900">{d.driver}</span>
            </div>
            <span className="font-medium text-gray-700">{d.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
