import { RiskDistribution } from "@/components/analytics/RiskDistribution";
import { QualityMetrics } from "@/components/analytics/QualityMetrics";
import { ReadmissionRisk } from "@/components/analytics/ReadmissionRisk";
import { CostOverview } from "@/components/analytics/CostOverview";
import { CohortSummary } from "@/components/analytics/CohortSummary";
import Link from "next/link";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Population Health Analytics</h1>
          <p className="text-sm text-gray-500">Risk stratification, outcomes, costs, and cohort insights</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/analytics/executive"
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
          >
            Executive Dashboard
          </Link>
          <Link
            href="/analytics/cohorts"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cohort Builder
          </Link>
        </div>
      </div>

      {/* Top KPI row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Total Patients", value: "2,847", change: "+12%", up: true },
          { label: "High/Critical Risk", value: "18.4%", change: "-2.1%", up: false },
          { label: "30-Day Readmission", value: "8.2%", change: "-1.3%", up: false },
          { label: "Quality Score", value: "0.82", change: "+0.04", up: true },
        ].map((kpi) => (
          <div key={kpi.label} className="card">
            <p className="text-xs font-medium text-gray-500">{kpi.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{kpi.value}</p>
            <p className={`mt-1 text-xs font-medium ${kpi.up ? "text-green-600" : "text-red-600"}`}>
              {kpi.change} vs last period
            </p>
          </div>
        ))}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <RiskDistribution />
        <QualityMetrics />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <ReadmissionRisk />
        <CostOverview />
      </div>

      <CohortSummary />
    </div>
  );
}
