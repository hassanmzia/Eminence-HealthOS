import { WorkflowConfig } from "@/components/operations/WorkflowConfig";
import Link from "next/link";

export default function OperationsAdminPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Operations Admin</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Workflow templates, SLA rules, and payer configuration</p>
        </div>
        <Link
          href="/operations"
          className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          Back to Operations
        </Link>
      </div>

      {/* Workflow configuration */}
      <WorkflowConfig />

      {/* Payer connections */}
      <div className="card">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">Payer Connections</h2>
        <div className="space-y-2">
          {[
            { name: "Aetna", status: "connected", realTime: true },
            { name: "UnitedHealthcare", status: "connected", realTime: true },
            { name: "Cigna", status: "connected", realTime: true },
            { name: "Anthem BCBS", status: "connected", realTime: true },
            { name: "Humana", status: "connected", realTime: false },
            { name: "CMS Medicare", status: "connected", realTime: false },
            { name: "State Medicaid", status: "connected", realTime: false },
          ].map((payer) => (
            <div key={payer.name} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 p-3">
              <div className="flex items-center gap-3">
                <span className={`h-2 w-2 rounded-full ${payer.status === "connected" ? "bg-green-500" : "bg-gray-300"}`} />
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{payer.name}</span>
                {payer.realTime && (
                  <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">Real-time</span>
                )}
              </div>
              <button className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300">Configure</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
