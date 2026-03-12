"use client";

const SCORECARD = [
  { kpi: "30-Day Readmission", actual: "8.2%", target: "<10%", status: "on_target" },
  { kpi: "ED Visit Rate", actual: "9.0%", target: "<8%", status: "off_target" },
  { kpi: "SLA Compliance", actual: "91.7%", target: "95%", status: "near_target" },
  { kpi: "Medication Adherence", actual: "83%", target: "85%", status: "near_target" },
  { kpi: "Quality Score", actual: "0.82", target: "0.80", status: "on_target" },
  { kpi: "Patient Satisfaction", actual: "4.2", target: "4.0", status: "on_target" },
  { kpi: "PMPM Cost", actual: "$262", target: "$280", status: "on_target" },
  { kpi: "Denial Rate", actual: "6.2%", target: "<5%", status: "off_target" },
  { kpi: "Automation Rate", actual: "62%", target: "70%", status: "off_target" },
  { kpi: "Care Gap Closure", actual: "74%", target: "80%", status: "off_target" },
];

const STATUS_STYLE = {
  on_target: { dot: "bg-green-500", badge: "bg-green-50 text-green-700", label: "On Target" },
  near_target: { dot: "bg-yellow-500", badge: "bg-yellow-50 text-yellow-700", label: "Near" },
  off_target: { dot: "bg-red-500", badge: "bg-red-50 text-red-700", label: "Off Target" },
} as const;

export function KPIScorecard() {
  const onTarget = SCORECARD.filter((s) => s.status === "on_target").length;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">KPI Scorecard</h2>
        <span className="rounded bg-healthos-50 px-2 py-0.5 text-xs font-medium text-healthos-700">
          {onTarget}/{SCORECARD.length} on target
        </span>
      </div>

      <div className="space-y-2">
        {SCORECARD.map((s) => {
          const style = STATUS_STYLE[s.status];
          return (
            <div key={s.kpi} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2">
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${style.dot}`} />
                <span className="text-sm text-gray-900">{s.kpi}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-900">{s.actual}</span>
                <span className="text-xs text-gray-400">/ {s.target}</span>
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${style.badge}`}>
                  {style.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
