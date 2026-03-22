"use client";

import { useState, useEffect } from "react";

interface WorkflowStep {
  step_id: string;
  name: string;
  agent: string;
  status: string;
  depends_on: string[];
}

interface Workflow {
  workflow_id: string;
  name: string;
  workflow_type: string;
  status: string;
  priority: string;
  patient_name: string;
  progress: number;
  total_steps: number;
  steps: WorkflowStep[];
  created_at: string;
}

const STEP_STATUS_ICON: Record<string, { icon: string; color: string }> = {
  completed: { icon: "\u2713", color: "bg-green-500 text-white" },
  in_progress: { icon: "\u25B6", color: "bg-blue-500 text-white" },
  ready: { icon: "\u25CB", color: "bg-yellow-100 text-yellow-800 border border-yellow-300" },
  pending: { icon: "\u25CB", color: "bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-300 dark:border-gray-600" },
  failed: { icon: "\u2717", color: "bg-red-500 text-white" },
  blocked: { icon: "!", color: "bg-orange-500 text-white" },
};

const WORKFLOW_STATUS_COLORS: Record<string, string> = {
  active: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  paused: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
};

const DEMO_WORKFLOWS: Workflow[] = [
  {
    workflow_id: "WF-001",
    name: "Specialist Referral Workflow",
    workflow_type: "specialist_referral",
    status: "active",
    priority: "normal",
    patient_name: "J. Smith",
    progress: 0.40,
    total_steps: 5,
    steps: [
      { step_id: "S1", name: "Verify Specialist Coverage", agent: "insurance_verification", status: "completed", depends_on: [] },
      { step_id: "S2", name: "Create Referral", agent: "referral_coordination", status: "completed", depends_on: ["S1"] },
      { step_id: "S3", name: "Match Specialist", agent: "referral_coordination", status: "in_progress", depends_on: ["S2"] },
      { step_id: "S4", name: "Schedule Visit", agent: "task_orchestration", status: "pending", depends_on: ["S3"] },
      { step_id: "S5", name: "Send Clinical Summary", agent: "task_orchestration", status: "pending", depends_on: ["S2"] },
    ],
    created_at: "2026-03-11T10:00:00Z",
  },
  {
    workflow_id: "WF-002",
    name: "Claim Submission Workflow",
    workflow_type: "claim_submission",
    status: "active",
    priority: "urgent",
    patient_name: "M. Johnson",
    progress: 0.60,
    total_steps: 5,
    steps: [
      { step_id: "S1", name: "Validate Encounter", agent: "billing_readiness", status: "completed", depends_on: [] },
      { step_id: "S2", name: "Check Coding", agent: "billing_readiness", status: "completed", depends_on: ["S1"] },
      { step_id: "S3", name: "Verify Insurance", agent: "insurance_verification", status: "completed", depends_on: [] },
      { step_id: "S4", name: "Check Prior Auth", agent: "prior_authorization", status: "in_progress", depends_on: ["S3"] },
      { step_id: "S5", name: "Prepare Claim", agent: "billing_readiness", status: "pending", depends_on: ["S1", "S2", "S3"] },
    ],
    created_at: "2026-03-10T14:00:00Z",
  },
  {
    workflow_id: "WF-003",
    name: "Discharge Follow-Up Workflow",
    workflow_type: "discharge_follow_up",
    status: "completed",
    priority: "normal",
    patient_name: "K. Wilson",
    progress: 1.0,
    total_steps: 5,
    steps: [
      { step_id: "S1", name: "Prepare Summary", agent: "task_orchestration", status: "completed", depends_on: [] },
      { step_id: "S2", name: "Review Billing", agent: "billing_readiness", status: "completed", depends_on: [] },
      { step_id: "S3", name: "Schedule Follow-Up", agent: "task_orchestration", status: "completed", depends_on: ["S1"] },
      { step_id: "S4", name: "Notify PCP", agent: "task_orchestration", status: "completed", depends_on: ["S1"] },
      { step_id: "S5", name: "Patient Education", agent: "task_orchestration", status: "completed", depends_on: ["S1"] },
    ],
    created_at: "2026-03-09T08:00:00Z",
  },
];

export function WorkflowProgress() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    setWorkflows(DEMO_WORKFLOWS);
  }, []);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Active Workflows</h2>
        <button className="rounded bg-healthos-600 px-3 py-1 text-xs font-medium text-white hover:bg-healthos-700">
          New Workflow
        </button>
      </div>

      <div className="space-y-3">
        {workflows.map((wf) => (
          <div key={wf.workflow_id} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
            {/* Workflow header */}
            <div
              className="cursor-pointer p-3"
              onClick={() => setExpandedId(expandedId === wf.workflow_id ? null : wf.workflow_id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{wf.name}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${WORKFLOW_STATUS_COLORS[wf.status] || "bg-gray-100 dark:bg-gray-800"}`}>
                    {wf.status}
                  </span>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400">{wf.workflow_id}</span>
              </div>
              <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                <span>{wf.patient_name}</span>
                <span>&middot;</span>
                <span>{wf.workflow_type.replace(/_/g, " ")}</span>
                <span>&middot;</span>
                <span>{Math.round(wf.progress * 100)}% complete</span>
              </div>
              {/* Progress bar */}
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-200">
                <div
                  className={`h-full rounded-full transition-all ${wf.status === "completed" ? "bg-green-500" : "bg-healthos-600"}`}
                  style={{ width: `${wf.progress * 100}%` }}
                />
              </div>
            </div>

            {/* Expanded step detail */}
            {expandedId === wf.workflow_id && (
              <div className="border-t border-gray-200 dark:border-gray-700 p-3">
                <div className="space-y-2">
                  {wf.steps.map((step, i) => {
                    const statusInfo = STEP_STATUS_ICON[step.status] || STEP_STATUS_ICON.pending;
                    return (
                      <div key={step.step_id} className="flex items-center gap-3">
                        {/* Status icon */}
                        <div className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${statusInfo.color}`}>
                          {statusInfo.icon}
                        </div>
                        {/* Connector line */}
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className={`text-sm ${step.status === "completed" ? "text-gray-500 dark:text-gray-400 line-through" : "text-gray-900 dark:text-gray-100"}`}>
                              {step.name}
                            </span>
                            <span className="text-xs text-gray-500 dark:text-gray-400">{step.agent}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
