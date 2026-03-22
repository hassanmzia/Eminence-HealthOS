"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchAgents,
  fetchAgentActivity,
  AgentExecutionEntry,
  PipelineRunEntry,
  AgentActivityResponse,
} from "@/lib/api";

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
  measurement: "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200",
};

const TIER_ORDER = ["sensing", "interpretation", "decisioning", "action", "measurement"];

const STATUS_COLORS: Record<string, { dot: string; badge: string }> = {
  idle: { dot: "bg-gray-400", badge: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300" },
  running: { dot: "bg-blue-500 animate-pulse", badge: "bg-blue-100 text-blue-800" },
  completed: { dot: "bg-green-500", badge: "bg-green-100 text-green-800" },
  failed: { dot: "bg-red-500", badge: "bg-red-100 text-red-800" },
  waiting_hitl: { dot: "bg-yellow-500 animate-pulse", badge: "bg-yellow-100 text-yellow-800" },
};

function StatusDot({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.idle;
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${colors.dot}`} />;
}

function StatusBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.idle;
  const label = status === "waiting_hitl" ? "HITL" : status;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors.badge}`}>
      {label}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-500 dark:text-gray-400">--</span>;
  }
  const pct = Math.round(value * 100);
  const barColor =
    pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 rounded-full bg-gray-200">
        <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400">{pct}%</span>
    </div>
  );
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "--";
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "--";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function AgentMonitor() {
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [activity, setActivity] = useState<AgentActivityResponse | null>(null);
  const [activityLoading, setActivityLoading] = useState(true);

  useEffect(() => {
    fetchAgents()
      .then((data) => {
        const list = (data.agents || data) as AgentRow[];
        setAgents(list);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const loadActivity = useCallback(() => {
    fetchAgentActivity(10)
      .then((data) => setActivity(data))
      .catch(() => {})
      .finally(() => setActivityLoading(false));
  }, []);

  useEffect(() => {
    loadActivity();
    // Poll every 15 seconds for near-live updates
    const interval = setInterval(loadActivity, 15_000);
    return () => clearInterval(interval);
  }, [loadActivity]);

  const agentStatuses = activity?.agent_statuses ?? {};

  const groupedByTier = TIER_ORDER.map((tier) => ({
    tier,
    agents: agents.filter((a) => a.tier === tier),
  })).filter((g) => g.agents.length > 0);

  // Summary counts
  const statusCounts = Object.values(agentStatuses).reduce(
    (acc, s) => {
      acc[s] = (acc[s] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-5">
        <div className="card">
          <p className="text-sm text-gray-500 dark:text-gray-400">Registered Agents</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{agents.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 dark:text-gray-400">Tiers Active</p>
          <p className="text-2xl font-bold text-healthos-600">{groupedByTier.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 dark:text-gray-400">HITL Required</p>
          <p className="text-2xl font-bold text-orange-600">
            {agents.filter((a) => a.requires_hitl).length}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 dark:text-gray-400">Running</p>
          <p className="text-2xl font-bold text-blue-600">{statusCounts.running || 0}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 dark:text-gray-400">Failed</p>
          <p className="text-2xl font-bold text-red-600">{statusCounts.failed || 0}</p>
        </div>
      </div>

      {loading ? (
        <div className="card py-8 text-center text-sm text-gray-500 dark:text-gray-400">Loading agents...</div>
      ) : agents.length === 0 ? (
        <div className="card py-8 text-center text-sm text-gray-500 dark:text-gray-400">No agents registered</div>
      ) : (
        /* Agents by tier - now with status column */
        groupedByTier.map((group) => (
          <div key={group.tier}>
            <div className="mb-2 flex items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TIER_COLORS[group.tier]}`}>
                {group.tier}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">Layer {TIER_ORDER.indexOf(group.tier) + 1}</span>
            </div>

            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Agent</th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Version</th>
                    <th className="px-4 py-2 text-center text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
                    <th className="px-4 py-2 text-center text-xs font-medium uppercase text-gray-500 dark:text-gray-400">HITL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {group.agents.map((agent) => {
                    const status = agentStatuses[agent.name] || "idle";
                    return (
                      <tr key={agent.name} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{agent.name}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{agent.description}</p>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{agent.version}</td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            <StatusDot status={status} />
                            <span className="text-xs text-gray-600 dark:text-gray-400">{status}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {agent.requires_hitl ? (
                            <span className="text-xs text-orange-600">Required</span>
                          ) : (
                            <span className="text-xs text-gray-500 dark:text-gray-400">Auto</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table></div>
            </div>
          </div>
        ))
      )}

      {/* ── Recent Activity ─────────────────────────────────────────────── */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Recent Activity</h2>
          <button
            onClick={loadActivity}
            className="rounded-md bg-gray-100 dark:bg-gray-800 px-3 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-200"
          >
            Refresh
          </button>
        </div>

        {activityLoading ? (
          <div className="card py-8 text-center text-sm text-gray-500 dark:text-gray-400">Loading activity...</div>
        ) : !activity || activity.executions.length === 0 ? (
          <div className="card py-8 text-center text-sm text-gray-500 dark:text-gray-400">No recent agent executions</div>
        ) : (
          <div className="card overflow-hidden p-0">
            <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Time</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Agent</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Action</th>
                  <th className="px-4 py-2 text-center text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Duration</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {activity.executions.map((ex) => (
                  <tr key={ex.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="whitespace-nowrap px-4 py-2.5 text-xs text-gray-500 dark:text-gray-400">
                      {formatTimestamp(ex.created_at)}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{ex.agent_name}</span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500 dark:text-gray-400">{ex.action}</td>
                    <td className="px-4 py-2.5 text-center">
                      <StatusBadge status={ex.status} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-right text-xs text-gray-600 dark:text-gray-400">
                      {formatDuration(ex.duration_ms)}
                    </td>
                    <td className="px-4 py-2.5">
                      <ConfidenceBar value={ex.confidence_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        )}
      </div>

      {/* ── Pipeline Activity Feed ──────────────────────────────────────── */}
      {activity && activity.pipeline_runs.length > 0 && (
        <div>
          <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">Pipeline Activity</h2>
          <div className="space-y-3">
            {activity.pipeline_runs.map((run) => (
              <div key={run.trace_id} className="card">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                        {run.trace_id.slice(0, 8)}...
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">{run.trigger_event}</span>
                    </div>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {run.agents_executed.map((name) => (
                        <span
                          key={name}
                          className="inline-flex items-center rounded bg-healthos-50 px-1.5 py-0.5 text-xs font-medium text-healthos-700"
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {formatDuration(run.total_duration_ms)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {run.started_at ? formatTimestamp(run.started_at) : "--"}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
