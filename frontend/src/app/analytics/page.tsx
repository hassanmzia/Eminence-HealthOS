import { KPIStrip } from "@/components/analytics/KPIStrip";
import { CostDriverChart } from "@/components/analytics/CostDriverChart";
import { OpportunityList } from "@/components/analytics/OpportunityList";
import Link from "next/link";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500">Cost intelligence, KPI tracking, and executive insights</p>
        </div>
        <Link
          href="/analytics/executive"
          className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
        >
          Executive Dashboard
        </Link>
      </div>

      <KPIStrip />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CostDriverChart />
        <OpportunityList />
      </div>
    </div>
  );
}
