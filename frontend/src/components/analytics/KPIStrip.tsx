"use client";

const KPIS = [
  { label: "Total Patients", value: "2,847", change: "+12%", positive: true },
  { label: "PMPM Cost", value: "$262", change: "-8.1%", positive: true },
  { label: "Quality Score", value: "0.82", change: "+0.04", positive: true },
  { label: "Readmission Rate", value: "8.2%", change: "-1.3%", positive: true },
  { label: "RPM ROI", value: "128.9%", change: "+22%", positive: true },
];

export function KPIStrip() {
  return (
    <div className="grid grid-cols-5 gap-4">
      {KPIS.map((kpi) => (
        <div key={kpi.label} className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium text-gray-500">{kpi.label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{kpi.value}</p>
          <p className={`mt-1 text-xs font-medium ${kpi.positive ? "text-green-600" : "text-red-600"}`}>
            {kpi.change} vs prior period
          </p>
        </div>
      ))}
    </div>
  );
}
