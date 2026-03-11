"use client";

import { useState, useEffect } from "react";

interface AgentRow {
  name: string;
  tier: string;
  version: string;
  description: string;
  requires_hitl: boolean;
  status: "active" | "idle" | "error";
  decisions_today: number;
  avg_confidence: number;
  avg_latency_ms: number;
}

const TIER_COLORS: Record<string, string> = {
  sensing: "bg-blue-100 text-blue-800",
  interpretation: "bg-purple-100 text-purple-800",
  decisioning: "bg-orange-100 text-orange-800",
  action: "bg-green-100 text-green-800",
  measurement: "bg-gray-100 text-gray-800",
};

const TIER_ORDER = ["sensing", "interpretation", "decisioning", "action", "measurement"];

const DEMO_AGENTS: AgentRow[] = [
  { name: "device_ingestion", tier: "sensing", version: "1.0.0", description: "Multi-device data collection and validation", requires_hitl: false, status: "active", decisions_today: 2847, avg_confidence: 0.97, avg_latency_ms: 12 },
  { name: "vitals_normalization", tier: "sensing", version: "1.0.0", description: "Schema standardization and unit conversion", requires_hitl: false, status: "active", decisions_today: 2841, avg_confidence: 0.98, avg_latency_ms: 8 },
  { name: "anomaly_detection", tier: "interpretation", version: "1.0.0", description: "Threshold and statistical anomaly detection", requires_hitl: false, status: "active", decisions_today: 2841, avg_confidence: 0.91, avg_latency_ms: 45 },
  { name: "adherence_monitoring", tier: "interpretation", version: "1.0.0", description: "Patient compliance tracking", requires_hitl: false, status: "active", decisions_today: 148, avg_confidence: 0.93, avg_latency_ms: 22 },
  { name: "context_assembly", tier: "decisioning", version: "1.0.0", description: "Comprehensive patient context assembly", requires_hitl: false, status: "active", decisions_today: 312, avg_confidence: 0.90, avg_latency_ms: 35 },
  { name: "risk_scoring", tier: "decisioning", version: "1.0.0", description: "Patient deterioration risk computation", requires_hitl: false, status: "active", decisions_today: 567, avg_confidence: 0.85, avg_latency_ms: 55 },
  { name: "trend_analysis", tier: "decisioning", version: "1.0.0", description: "Multi-day pattern detection", requires_hitl: false, status: "active", decisions_today: 445, avg_confidence: 0.88, avg_latency_ms: 42 },
  { name: "policy_rules", tier: "decisioning", version: "1.0.0", description: "Clinical policy and guardrail enforcement", requires_hitl: false, status: "active", decisions_today: 312, avg_confidence: 0.95, avg_latency_ms: 18 },
];

export function AgentMonitor() {
  const [agents, setAgents] = useState<AgentRow[]>([]);

  useEffect(() => {
    // TODO: Replace with fetchAgents() API call
    setAgents(DEMO_AGENTS);
  }, []);

  const groupedByTier = TIER_ORDER.map((tier) => ({
    tier,
    agents: agents.filter((a) => a.tier === tier),
  })).filter((g) => g.agents.length > 0);

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div className="card">
          <p className="text-sm text-gray-500">Total Agents</p>
          <p className="text-2xl font-bold text-gray-900">{agents.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Decisions Today</p>
          <p className="text-2xl font-bold text-healthos-600">
            {agents.reduce((s, a) => s + a.decisions_today, 0).toLocaleString()}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Avg Confidence</p>
          <p className="text-2xl font-bold text-green-600">
            {(agents.reduce((s, a) => s + a.avg_confidence, 0) / (agents.length || 1) * 100).toFixed(1)}%
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Avg Latency</p>
          <p className="text-2xl font-bold text-purple-600">
            {Math.round(agents.reduce((s, a) => s + a.avg_latency_ms, 0) / (agents.length || 1))}ms
          </p>
        </div>
      </div>

      {/* Agents by tier */}
      {groupedByTier.map((group) => (
        <div key={group.tier}>
          <div className="mb-2 flex items-center gap-2">
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TIER_COLORS[group.tier]}`}>
              {group.tier}
            </span>
            <span className="text-xs text-gray-400">Layer {TIER_ORDER.indexOf(group.tier) + 1}</span>
          </div>

          <div className="card overflow-hidden p-0">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Agent</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">Decisions</th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">Confidence</th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">Latency</th>
                  <th className="px-4 py-2 text-center text-xs font-medium uppercase text-gray-500">HITL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {group.agents.map((agent) => (
                  <tr key={agent.name} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-gray-900">{agent.name}</p>
                      <p className="text-xs text-gray-400">{agent.description}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-xs">
                        <span className={`h-2 w-2 rounded-full ${agent.status === "active" ? "bg-green-500" : agent.status === "error" ? "bg-red-500" : "bg-gray-300"}`} />
                        {agent.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-600">{agent.decisions_today.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-sm text-gray-600">{(agent.avg_confidence * 100).toFixed(1)}%</td>
                    <td className="px-4 py-3 text-right text-sm text-gray-600">{agent.avg_latency_ms}ms</td>
                    <td className="px-4 py-3 text-center">
                      {agent.requires_hitl ? (
                        <span className="text-xs text-orange-600">Required</span>
                      ) : (
                        <span className="text-xs text-gray-400">Auto</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
