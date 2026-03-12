"use client";

const OPPORTUNITIES = [
  { name: "Chronic Disease Management", savings: "$320K", effort: "high", timeline: "12mo" },
  { name: "Reduce Readmissions", savings: "$270K", effort: "high", timeline: "9mo" },
  { name: "Reduce Avoidable ED", savings: "$180K", effort: "medium", timeline: "6mo" },
  { name: "Pharmacy Optimization", savings: "$95K", effort: "low", timeline: "3mo" },
  { name: "Imaging Appropriateness", savings: "$65K", effort: "low", timeline: "4mo" },
];

const EFFORT_STYLE = {
  low: "bg-green-50 text-green-700",
  medium: "bg-yellow-50 text-yellow-700",
  high: "bg-red-50 text-red-700",
} as const;

export function OpportunityList() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-gray-900">Cost Reduction Opportunities</h2>
      <p className="mb-4 text-xs text-gray-500">$930K total potential annual savings</p>

      <div className="space-y-3">
        {OPPORTUNITIES.map((o) => (
          <div key={o.name} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
            <div>
              <p className="text-sm font-medium text-gray-900">{o.name}</p>
              <div className="mt-1 flex gap-2 text-xs">
                <span className={`rounded px-1.5 py-0.5 ${EFFORT_STYLE[o.effort as keyof typeof EFFORT_STYLE]}`}>
                  {o.effort} effort
                </span>
                <span className="text-gray-500">{o.timeline}</span>
              </div>
            </div>
            <span className="text-sm font-bold text-green-600">{o.savings}/yr</span>
          </div>
        ))}
      </div>
    </div>
  );
}
