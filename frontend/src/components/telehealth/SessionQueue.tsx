"use client";

import { useState, useEffect } from "react";
import { fetchTelehealthSessions, type TelehealthSession } from "@/lib/api";

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

interface Props {
  selectedSessionId?: string;
  onSelectSession?: (session: TelehealthSession) => void;
}

export function SessionQueue({ selectedSessionId, onSelectSession }: Props) {
  const [sessions, setSessions] = useState<TelehealthSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTelehealthSessions()
      .then((data) => setSessions(data.sessions || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Session Queue</h2>
        <span className="text-xs text-gray-500 dark:text-gray-400">{sessions.length} sessions</span>
      </div>

      {loading ? (
        <div className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">Loading sessions...</div>
      ) : sessions.length === 0 ? (
        <div className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">No active sessions</div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              onClick={() => onSelectSession?.(session)}
              className={`cursor-pointer rounded-lg border-l-4 p-3 transition-colors ${
                URGENCY_COLORS[session.urgency] || "border-l-gray-300"
              } ${
                selectedSessionId === session.session_id
                  ? "bg-healthos-50 ring-1 ring-healthos-200"
                  : "bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {session.patient_name || `Patient ${session.patient_id.slice(0, 8)}`}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    STATUS_BADGE[session.status] || "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                  }`}
                >
                  {session.status.replace("_", " ")}
                </span>
              </div>
              {session.chief_complaint && (
                <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{session.chief_complaint}</p>
              )}
              <div className="mt-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <span>{session.visit_type.replace("_", " ")}</span>
                <span>&middot;</span>
                <span>
                  {session.estimated_wait_minutes != null && session.estimated_wait_minutes > 0
                    ? `${session.estimated_wait_minutes}m wait`
                    : "Active"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
