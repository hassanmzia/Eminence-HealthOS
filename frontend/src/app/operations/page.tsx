import { TaskQueue } from "@/components/operations/TaskQueue";
import { PriorAuthPanel } from "@/components/operations/PriorAuthPanel";
import { ReferralTracker } from "@/components/operations/ReferralTracker";
import { SLAComplianceWidget } from "@/components/operations/SLAComplianceWidget";

export default function OperationsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Operations</h1>
        <div className="flex gap-2">
          <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            New Workflow
          </button>
          <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
            Create Task
          </button>
        </div>
      </div>

      {/* Top row: Task queue + SLA */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TaskQueue />
        </div>
        <div>
          <SLAComplianceWidget />
        </div>
      </div>

      {/* Prior authorizations */}
      <PriorAuthPanel />

      {/* Referral tracker */}
      <ReferralTracker />
    </div>
  );
}
