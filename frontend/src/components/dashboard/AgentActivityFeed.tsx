"use client";

import { useState, useEffect } from "react";

interface AgentEvent {
  id: string;
  agent: string;
  action: string;
  patient: string;
  time: string;
  confidence: number;
}

const TIER_COLORS: Record<string, string> = {
  sensing: "bg-blue-100 text-blue-700",
  interpretation: "bg-purple-100 text-purple-700",
  decisioning: "bg-orange-100 text-orange-700",
  action: "bg-green-100 text-green-700",
  measurement: "bg-gray-100 text-gray-700",
};

const DEMO_EVENTS: AgentEvent[] = [
  { id: "1", agent: "anomaly_detection", action: "Detected HR anomaly", patient: "J. Smith", time: "2s ago", confidence: 0.92 },
  { id: "2", agent: "risk_scoring", action: "Risk score updated", patient: "K. Wilson", time: "5s ago", confidence: 0.87 },
  { id: "3", agent: "policy_rules", action: "Policy check passed", patient: "M. Johnson", time: "8s ago", confidence: 0.95 },
  { id: "4", agent: "context_assembly", action: "Context assembled", patient: "R. Williams", time: "12s ago", confidence: 0.90 },
  { id: "5", agent: "vitals_normalization", action: "Vitals normalized", patient: "S. Brown", time: "15s ago", confidence: 0.98 },
];

export function AgentActivityFeed() {
  const [events, setEvents] = useState<AgentEvent[]>([]);

  useEffect(() => {
    // TODO: Replace with WebSocket real-time feed
    setEvents(DEMO_EVENTS);
  }, []);

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Agent Activity</h2>
        <span className="flex items-center gap-1 text-xs text-green-600">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
          Live
        </span>
      </div>
      <div className="space-y-3">
        {events.map((event) => (
          <div key={event.id} className="flex items-start gap-2">
            <div className="mt-0.5 h-2 w-2 rounded-full bg-healthos-400" />
            <div className="flex-1 text-xs">
              <p className="text-gray-700">
                <span className="font-medium">{event.agent}</span>{" "}
                {event.action} for{" "}
                <span className="font-medium">{event.patient}</span>
              </p>
              <p className="text-gray-400">
                {event.time} &middot; {Math.round(event.confidence * 100)}% confidence
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
