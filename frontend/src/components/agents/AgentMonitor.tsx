"use client";

import { useState, useEffect } from "react";
import { fetchAgents } from "@/lib/api";

interface AgentRow {
  name: string;
  tier: string;
  version: string;
  description: string;
  requires_hitl: boolean;
}

const TIER_COLORS: Record<string, string> = {
  sensing: "bg-blue-100 text-blue-800",
  interpretation: "bg-purple-100 text-purple-800",
  decisioning: "bg-orange-100 text-orange-800",
  action: "bg-green-100 text-green-800",
  measurement: "bg-gray-100 text-gray-800",
};

const TIER_ORDER = ["sensing", "interpretation", "decisioning", "action", "measurement"];

export function AgentMonitor() {
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAgents()
      .then((data) => {
        const list = (data.agents || data) as AgentRow[];
        setAgents(list);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const groupedByTier = TIER_ORDER.map((tier) => ({
    tier,
    agents: agents.filter((a) => a.tier === tier),
  })).filter((g) => g.agents.length > 0);

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="card">
          <p className="text-sm text-gray-500">Registered Agents</p>
          <p className="text-2xl font-bold text-gray-900">{agents.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Tiers Active</p>
          <p className="text-2xl font-bold text-healthos-600">{groupedByTier.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">HITL Required</p>
          <p className="text-2xl font-bold text-orange-600">
            {agents.filter((a) => a.requires_hitl).length}
          </p>
        </div>
      </div>

      {loading ? (
        <div className="card py-8 text-center text-sm text-gray-400">Loading agents...</div>
      ) : agents.length === 0 ? (
        <div className="card py-8 text-center text-sm text-gray-400">No agents registered</div>
      ) : (
        /* Agents by tier */
        groupedByTier.map((group) => (
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
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Version</th>
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
                      <td className="px-4 py-3 text-sm text-gray-600">{agent.version}</td>
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
        ))
      )}
    </div>
  );
}
