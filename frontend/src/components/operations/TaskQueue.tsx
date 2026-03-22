"use client";

import { useState, useEffect } from "react";

interface Task {
  task_id: string;
  title: string;
  task_type: string;
  priority: string;
  status: string;
  sla_deadline: string;
  patient_id: string;
  assignee?: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "border-l-red-500",
  normal: "border-l-blue-400",
  low: "border-l-gray-300",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  blocked: "bg-red-100 text-red-800",
};

const TYPE_LABEL: Record<string, string> = {
  prior_auth: "Prior Auth",
  insurance_verification: "Insurance",
  referral: "Referral",
  scheduling: "Scheduling",
  documentation: "Documentation",
  billing_review: "Billing",
  care_coordination: "Care Coord",
};

const DEMO_TASKS: Task[] = [
  { task_id: "TASK-001", title: "Verify insurance — Smith", task_type: "insurance_verification", priority: "urgent", status: "pending", sla_deadline: new Date(Date.now() + 2 * 3600000).toISOString(), patient_id: "PT-001" },
  { task_id: "TASK-002", title: "Prior auth — CT scan", task_type: "prior_auth", priority: "normal", status: "in_progress", sla_deadline: new Date(Date.now() + 18 * 3600000).toISOString(), patient_id: "PT-002", assignee: "Auth Team" },
  { task_id: "TASK-003", title: "Referral — Cardiology", task_type: "referral", priority: "normal", status: "pending", sla_deadline: new Date(Date.now() + 20 * 3600000).toISOString(), patient_id: "PT-003" },
  { task_id: "TASK-004", title: "Schedule follow-up — Johnson", task_type: "scheduling", priority: "low", status: "pending", sla_deadline: new Date(Date.now() + 48 * 3600000).toISOString(), patient_id: "PT-004" },
  { task_id: "TASK-005", title: "Prior auth — MRI (overdue)", task_type: "prior_auth", priority: "urgent", status: "blocked", sla_deadline: new Date(Date.now() - 6 * 3600000).toISOString(), patient_id: "PT-005", assignee: "Auth Team" },
];

function timeRemaining(deadline: string): string {
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff < 0) {
    const hours = Math.abs(Math.floor(diff / 3600000));
    return `${hours}h overdue`;
  }
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return `${Math.floor(diff / 60000)}m left`;
  return `${hours}h left`;
}

function isOverdue(deadline: string): boolean {
  return new Date(deadline).getTime() < Date.now();
}

export function TaskQueue() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    setTasks(DEMO_TASKS);
  }, []);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Task Queue</h2>
        <span className="text-xs text-gray-500 dark:text-gray-400">{tasks.length} tasks</span>
      </div>
      <div className="space-y-2">
        {tasks.map((task) => (
          <div
            key={task.task_id}
            className={`cursor-pointer rounded-lg border-l-4 bg-gray-50 dark:bg-gray-800 p-3 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 ${PRIORITY_COLORS[task.priority] || "border-l-gray-300"}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{task.title}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[task.status] || STATUS_BADGE.pending}`}>
                {task.status.replace("_", " ")}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span className="rounded bg-gray-200 px-1.5 py-0.5 font-medium">{TYPE_LABEL[task.task_type] || task.task_type}</span>
              {task.assignee && <span>&middot; {task.assignee}</span>}
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs">
              <span className={isOverdue(task.sla_deadline) ? "font-semibold text-red-600" : "text-gray-500 dark:text-gray-400"}>
                {timeRemaining(task.sla_deadline)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
