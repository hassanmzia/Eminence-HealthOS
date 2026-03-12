"use client";

const TRENDS = [
  { metric: "PMPM Cost", direction: "down", change: "-8.1%", current: "$262", status: "ahead" },
  { metric: "Readmission Rate", direction: "down", change: "-1.3%", current: "8.2%", status: "on_target" },
  { metric: "Quality Score", direction: "up", change: "+0.04", current: "0.82", status: "on_target" },
  { metric: "SLA Compliance", direction: "up", change: "+3.4%", current: "91.7%", status: "improving" },
  { metric: "Automation Rate", direction: "up", change: "+5%", current: "62%", status: "improving" },
  { metric: "Patient Volume", direction: "up", change: "+12%", current: "2,847", status: "on_track" },
];

const STATUS_STYLE = {
  ahead: "bg-green-100 text-green-700",
  on_target: "bg-green-50 text-green-600",
  on_track: "bg-blue-50 text-blue-600",
  improving: "bg-yellow-50 text-yellow-600",
} as const;

export function TrendDigest() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Trend Analysis</h2>
        <span className="text-xs text-gray-500">Last 6 months</span>
      </div>

      <div className="space-y-2">
        {TRENDS.map((t) => (
          <div key={t.metric} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className={t.direction === "up" ? "text-green-500" : "text-green-500"}>
                {t.direction === "up" ? "\u2191" : "\u2193"}
              </span>
              <span className="text-sm text-gray-900">{t.metric}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">{t.current}</span>
              <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_STYLE[t.status as keyof typeof STATUS_STYLE]}`}>
                {t.change}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-lg bg-gray-50 p-3">
        <p className="text-xs leading-relaxed text-gray-700">
          Platform performance continues to improve across all major dimensions. Cost reduction
          is ahead of target with PMPM at $262 (target $280). Clinical quality metrics are on
          or above target. Operational efficiency is the primary area for continued investment.
        </p>
      </div>
    </div>
  );
}
