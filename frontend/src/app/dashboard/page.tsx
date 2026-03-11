import { PatientRiskHeatmap } from "@/components/dashboard/PatientRiskHeatmap";
import { CriticalAlertsBanner } from "@/components/dashboard/CriticalAlertsBanner";
import { AgentActivityFeed } from "@/components/dashboard/AgentActivityFeed";
import { SystemHealthWidget } from "@/components/dashboard/SystemHealthWidget";
import { VitalsSummaryCards } from "@/components/dashboard/VitalsSummaryCards";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <span className="text-sm text-gray-500">Real-time overview</span>
      </div>

      {/* Critical alerts banner */}
      <CriticalAlertsBanner />

      {/* Summary cards */}
      <VitalsSummaryCards />

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <PatientRiskHeatmap />
        </div>
        <div className="space-y-6">
          <SystemHealthWidget />
          <AgentActivityFeed />
        </div>
      </div>
    </div>
  );
}
