import { ExecutiveSummary } from "@/components/analytics/ExecutiveSummary";
import { KPIScorecard } from "@/components/analytics/KPIScorecard";
import { TrendDigest } from "@/components/analytics/TrendDigest";
import Link from "next/link";

export default function ExecutiveDashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Executive Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Strategic insights, KPI scorecards, and trend analysis</p>
        </div>
        <Link
          href="/analytics"
          className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          Back to Analytics
        </Link>
      </div>

      <ExecutiveSummary />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <KPIScorecard />
        <TrendDigest />
      </div>
    </div>
  );
}
