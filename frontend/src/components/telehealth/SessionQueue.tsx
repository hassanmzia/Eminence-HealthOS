"use client";

import { useState, useEffect } from "react";

interface QueueItem {
  id: string;
  patient_name: string;
  visit_type: string;
  urgency: string;
  status: string;
  wait_minutes: number;
  chief_complaint: string;
}

const URGENCY_COLORS: Record<string, string> = {
  emergency: "border-l-red-500",
  urgent: "border-l-orange-400",
  same_day: "border-l-yellow-400",
  routine: "border-l-green-400",
};

const STATUS_BADGE: Record<string, string> = {
  waiting: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
};

const DEMO_QUEUE: QueueItem[] = [
  { id: "1", patient_name: "J. Smith", visit_type: "follow_up", urgency: "urgent", status: "waiting", wait_minutes: 5, chief_complaint: "Elevated heart rate" },
  { id: "2", patient_name: "M. Johnson", visit_type: "new_patient", urgency: "routine", status: "waiting", wait_minutes: 12, chief_complaint: "BP management" },
  { id: "3", patient_name: "K. Wilson", visit_type: "urgent", urgency: "urgent", status: "in_progress", wait_minutes: 0, chief_complaint: "SpO2 drop" },
  { id: "4", patient_name: "S. Brown", visit_type: "follow_up", urgency: "routine", status: "waiting", wait_minutes: 25, chief_complaint: "Glucose review" },
];

export function SessionQueue() {
  const [queue, setQueue] = useState<QueueItem[]>([]);

  useEffect(() => {
    setQueue(DEMO_QUEUE);
  }, []);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Session Queue</h2>
        <span className="text-xs text-gray-400">{queue.length} sessions</span>
      </div>
      <div className="space-y-2">
        {queue.map((item) => (
          <div
            key={item.id}
            className={`cursor-pointer rounded-lg border-l-4 bg-gray-50 p-3 transition-colors hover:bg-gray-100 ${URGENCY_COLORS[item.urgency] || "border-l-gray-300"}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-900">{item.patient_name}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[item.status]}`}>
                {item.status.replace("_", " ")}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-gray-500">{item.chief_complaint}</p>
            <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
              <span>{item.visit_type.replace("_", " ")}</span>
              <span>&middot;</span>
              <span>{item.wait_minutes > 0 ? `${item.wait_minutes}m wait` : "Active"}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
