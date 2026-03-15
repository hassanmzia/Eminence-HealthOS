"use client";

import { useState } from "react";
import { TaskQueue } from "@/components/operations/TaskQueue";
import { PriorAuthPanel } from "@/components/operations/PriorAuthPanel";
import { ReferralTracker } from "@/components/operations/ReferralTracker";
import { SLAComplianceWidget } from "@/components/operations/SLAComplianceWidget";
import { BillingDashboard } from "@/components/operations/BillingDashboard";
import { WorkflowProgress } from "@/components/operations/WorkflowProgress";

export default function OperationsPage() {
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [showNewWorkflow, setShowNewWorkflow] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: "", assignee: "", priority: "medium", dueDate: "" });
  const [workflowForm, setWorkflowForm] = useState({ name: "", type: "prior_auth" });

  const handleCreateTask = (e: React.FormEvent) => {
    e.preventDefault();
    // Task creation would go to backend; for now close modal
    setShowCreateTask(false);
    setTaskForm({ title: "", assignee: "", priority: "medium", dueDate: "" });
  };

  const handleNewWorkflow = (e: React.FormEvent) => {
    e.preventDefault();
    setShowNewWorkflow(false);
    setWorkflowForm({ name: "", type: "prior_auth" });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Operations</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowNewWorkflow(true)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            New Workflow
          </button>
          <button onClick={() => setShowCreateTask(true)} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
            Create Task
          </button>
        </div>
      </div>

      {/* Create Task Modal */}
      {showCreateTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowCreateTask(false)}>
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">Create Task</h2>
              <button onClick={() => setShowCreateTask(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Task Title *</label>
                <input required value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Review prior auth for Patient X" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Assignee</label>
                  <input value={taskForm.assignee} onChange={(e) => setTaskForm({ ...taskForm, assignee: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Dr. Smith" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select value={taskForm.priority} onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                <input type="date" value={taskForm.dueDate} onChange={(e) => setTaskForm({ ...taskForm, dueDate: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowCreateTask(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                <button type="submit" className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">Create Task</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Workflow Modal */}
      {showNewWorkflow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowNewWorkflow(false)}>
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">New Workflow</h2>
              <button onClick={() => setShowNewWorkflow(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleNewWorkflow} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Workflow Name *</label>
                <input required value={workflowForm.name} onChange={(e) => setWorkflowForm({ ...workflowForm, name: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Insurance Verification" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Workflow Type *</label>
                <select required value={workflowForm.type} onChange={(e) => setWorkflowForm({ ...workflowForm, type: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                  <option value="prior_auth">Prior Authorization</option>
                  <option value="referral">Referral Management</option>
                  <option value="billing">Billing & Claims</option>
                  <option value="scheduling">Scheduling</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowNewWorkflow(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                <button type="submit" className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">Create Workflow</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Top row: Task queue + SLA */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TaskQueue />
        </div>
        <div>
          <SLAComplianceWidget />
        </div>
      </div>

      {/* Workflow progress */}
      <WorkflowProgress />

      {/* Billing & Claims */}
      <BillingDashboard />

      {/* Prior authorizations */}
      <PriorAuthPanel />

      {/* Referral tracker */}
      <ReferralTracker />
    </div>
  );
}
