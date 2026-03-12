"use client";

import { useState, useEffect } from "react";

interface WorkflowTemplate {
  type: string;
  name: string;
  steps: number;
  description: string;
}

interface PriorityConfig {
  task_type: string;
  urgent_sla_hours: number;
  normal_sla_hours: number;
  low_sla_hours: number;
  auto_assignee: string;
}

const DEMO_TEMPLATES: WorkflowTemplate[] = [
  { type: "new_patient_intake", name: "New Patient Intake", steps: 5, description: "Insurance verification, demographics, scheduling, care team assignment" },
  { type: "surgical_prep", name: "Surgical Prep", steps: 6, description: "Coverage verification, prior auth, pre-op, consent, team coordination" },
  { type: "specialist_referral", name: "Specialist Referral", steps: 5, description: "Coverage check, referral creation, specialist matching, scheduling" },
  { type: "discharge_follow_up", name: "Discharge Follow-Up", steps: 5, description: "Discharge summary, billing review, follow-up scheduling, PCP notification" },
  { type: "claim_submission", name: "Claim Submission", steps: 5, description: "Encounter validation, coding check, insurance verification, claim preparation" },
];

const DEMO_PRIORITIES: PriorityConfig[] = [
  { task_type: "prior_auth", urgent_sla_hours: 4, normal_sla_hours: 24, low_sla_hours: 72, auto_assignee: "Auth Specialist" },
  { task_type: "insurance_verification", urgent_sla_hours: 2, normal_sla_hours: 8, low_sla_hours: 24, auto_assignee: "Billing Team" },
  { task_type: "referral", urgent_sla_hours: 4, normal_sla_hours: 24, low_sla_hours: 48, auto_assignee: "Care Coordinator" },
  { task_type: "scheduling", urgent_sla_hours: 1, normal_sla_hours: 8, low_sla_hours: 24, auto_assignee: "Front Desk" },
  { task_type: "billing_review", urgent_sla_hours: 8, normal_sla_hours: 48, low_sla_hours: 120, auto_assignee: "Billing Team" },
  { task_type: "care_coordination", urgent_sla_hours: 2, normal_sla_hours: 12, low_sla_hours: 48, auto_assignee: "Care Coordinator" },
];

export function WorkflowConfig() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [priorities, setPriorities] = useState<PriorityConfig[]>([]);
  const [activeTab, setActiveTab] = useState<"templates" | "sla">("templates");

  useEffect(() => {
    setTemplates(DEMO_TEMPLATES);
    setPriorities(DEMO_PRIORITIES);
  }, []);

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Workflow Configuration</h2>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
        <button
          onClick={() => setActiveTab("templates")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            activeTab === "templates" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600"
          }`}
        >
          Templates
        </button>
        <button
          onClick={() => setActiveTab("sla")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            activeTab === "sla" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600"
          }`}
        >
          SLA & Assignment Rules
        </button>
      </div>

      {activeTab === "templates" ? (
        <div className="space-y-2">
          {templates.map((tpl) => (
            <div key={tpl.type} className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{tpl.name}</span>
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">{tpl.steps} steps</span>
                </div>
                <p className="mt-0.5 text-xs text-gray-500">{tpl.description}</p>
              </div>
              <div className="ml-4 flex gap-2">
                <button className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">
                  Edit
                </button>
                <button className="rounded bg-healthos-600 px-2 py-1 text-xs text-white hover:bg-healthos-700">
                  Launch
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                <th className="pb-2 font-medium">Task Type</th>
                <th className="pb-2 font-medium">Urgent</th>
                <th className="pb-2 font-medium">Normal</th>
                <th className="pb-2 font-medium">Low</th>
                <th className="pb-2 font-medium">Auto-Assign</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {priorities.map((p) => (
                <tr key={p.task_type}>
                  <td className="py-2.5 font-medium capitalize text-gray-900">
                    {p.task_type.replace("_", " ")}
                  </td>
                  <td className="py-2.5 text-red-600">{p.urgent_sla_hours}h</td>
                  <td className="py-2.5 text-blue-600">{p.normal_sla_hours}h</td>
                  <td className="py-2.5 text-gray-500">{p.low_sla_hours}h</td>
                  <td className="py-2.5 text-gray-600">{p.auto_assignee}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
