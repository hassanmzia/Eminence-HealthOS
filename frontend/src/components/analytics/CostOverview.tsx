"use client";

const COST_DATA = {
  rpm_roi: {
    annual_cost: 180000,
    annual_savings: 412000,
    net_benefit: 232000,
    roi_percent: 128.9,
    payback_months: 5.2,
  },
  cost_by_risk: [
    { level: "Low", monthly: 50, patients: 1427, color: "bg-green-500" },
    { level: "Moderate", monthly: 150, patients: 896, color: "bg-yellow-500" },
    { level: "High", monthly: 400, patients: 382, color: "bg-orange-500" },
    { level: "Critical", monthly: 1200, patients: 142, color: "bg-red-500" },
  ],
  forecast: [
    { year: 1, savings: 412000 },
    { year: 2, savings: 453200 },
    { year: 3, savings: 498520 },
  ],
};

export function CostOverview() {
  const totalMonthly = COST_DATA.cost_by_risk.reduce((s, d) => s + d.monthly * d.patients, 0);

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Cost Analysis</h2>
        <span className="rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-600">
          {COST_DATA.rpm_roi.roi_percent}% RPM ROI
        </span>
      </div>

      {/* RPM ROI summary */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <p className="text-xs text-gray-500">Annual RPM Cost</p>
          <p className="mt-1 text-sm font-bold text-gray-900">${(COST_DATA.rpm_roi.annual_cost / 1000).toFixed(0)}K</p>
        </div>
        <div className="rounded-lg bg-green-50 p-3 text-center">
          <p className="text-xs text-gray-500">Annual Savings</p>
          <p className="mt-1 text-sm font-bold text-green-700">${(COST_DATA.rpm_roi.annual_savings / 1000).toFixed(0)}K</p>
        </div>
        <div className="rounded-lg bg-healthos-50 p-3 text-center">
          <p className="text-xs text-gray-500">Net Benefit</p>
          <p className="mt-1 text-sm font-bold text-healthos-700">${(COST_DATA.rpm_roi.net_benefit / 1000).toFixed(0)}K</p>
        </div>
      </div>

      {/* Cost by risk level */}
      <h3 className="mb-2 text-sm font-medium text-gray-700">Monthly Cost by Risk Level</h3>
      <div className="space-y-2">
        {COST_DATA.cost_by_risk.map((d) => {
          const total = d.monthly * d.patients;
          const pct = (total / totalMonthly) * 100;
          return (
            <div key={d.level} className="flex items-center gap-3 text-sm">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${d.color}`} />
              <span className="w-20 font-medium text-gray-900">{d.level}</span>
              <div className="flex-1">
                <div className="h-2 rounded-full bg-gray-100">
                  <div className={`h-2 rounded-full ${d.color}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
              <span className="w-16 text-right text-xs text-gray-500">
                ${(total / 1000).toFixed(0)}K
              </span>
            </div>
          );
        })}
      </div>

      {/* Savings forecast */}
      <div className="mt-4 rounded-lg border border-gray-200 p-3">
        <h3 className="mb-2 text-sm font-medium text-gray-700">3-Year Savings Forecast</h3>
        <div className="flex gap-4">
          {COST_DATA.forecast.map((f) => (
            <div key={f.year} className="flex-1 text-center">
              <p className="text-xs text-gray-500">Year {f.year}</p>
              <p className="text-sm font-bold text-green-600">${(f.savings / 1000).toFixed(0)}K</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
