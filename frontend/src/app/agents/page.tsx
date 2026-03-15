"use client";

import { useState, useEffect } from "react";
import { fetchAgents, fetchRecentAgentActivity, type AgentAuditEntry } from "@/lib/api";

interface RegisteredAgent {
  name: string;
  tier: string;
  version: string;
  description: string;
  requires_hitl: boolean;
}

const TIER_MAP: Record<string, { key: string; label: string; bg: string; text: string; ring: string; gradient: string }> = {
  autonomous: { key: "tier1", label: "Tier 1 — Autonomous", bg: "bg-emerald-50", text: "text-emerald-700", ring: "ring-emerald-500/20", gradient: "bg-gradient-to-r from-emerald-400 to-emerald-600" },
  supervised: { key: "tier2", label: "Tier 2 — Supervised", bg: "bg-amber-50", text: "text-amber-700", ring: "ring-amber-500/20", gradient: "bg-gradient-to-r from-amber-400 to-amber-600" },
  advisory: { key: "tier3", label: "Tier 3 — Advisory", bg: "bg-purple-50", text: "text-purple-700", ring: "ring-purple-500/20", gradient: "bg-gradient-to-r from-purple-400 to-purple-600" },
};

function tierConfig(tier: string) {
  const t = tier.toLowerCase();
  if (t.includes("autonomous") || t === "action" || t === "ingestion" || t === "normalization") return TIER_MAP.autonomous;
  if (t.includes("supervised") || t === "detection" || t === "scoring" || t === "analysis") return TIER_MAP.supervised;
  if (t.includes("advisory") || t === "measurement" || t === "advisory") return TIER_MAP.advisory;
  return TIER_MAP.autonomous;
}

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function ConfidenceRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const circumference = 2 * Math.PI * 18;
  const offset = circumference - (pct / 100) * circumference;
  const color = pct >= 90 ? "text-emerald-500" : pct >= 70 ? "text-amber-500" : "text-red-500";
  return (
    <div className="relative h-12 w-12">
      <svg className="h-12 w-12 -rotate-90" viewBox="0 0 40 40">
        <circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" className="text-gray-100" strokeWidth="3" />
        <circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" className={color} strokeWidth="3" strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-gray-700">{pct}%</span>
    </div>
  );
}

export default function AgentsPage() {
  const [registeredAgents, setRegisteredAgents] = useState<RegisteredAgent[]>([]);
  const [events, setEvents] = useState<AgentAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchAgents()
        .then((data) => {
          // data may be { agents: [...] } or an array directly
          const list = Array.isArray(data) ? data : (data as Record<string, unknown>)?.agents;
          if (Array.isArray(list)) setRegisteredAgents(list as RegisteredAgent[]);
        })
        .catch(() => {}),
      fetchRecentAgentActivity()
        .then(setEvents)
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  // Build activity stats per agent
  const activityMap = new Map<string, { runs: number; avgConf: number; lastAction: string; lastRunAt: string }>();
  for (const event of events) {
    const existing = activityMap.get(event.agent_name);
    if (existing) {
      existing.runs += 1;
      existing.avgConf = (existing.avgConf * (existing.runs - 1) + (event.confidence_score || 0)) / existing.runs;
      if (event.created_at > existing.lastRunAt) {
        existing.lastRunAt = event.created_at;
        existing.lastAction = event.action;
      }
    } else {
      activityMap.set(event.agent_name, {
        runs: 1,
        avgConf: event.confidence_score || 0,
        lastAction: event.action,
        lastRunAt: event.created_at,
      });
    }
  }

  // Merge registered agents with activity data
  const agents = registeredAgents.map((ra) => {
    const activity = activityMap.get(ra.name);
    return {
      ...ra,
      totalRuns: activity?.runs || 0,
      avgConfidence: activity?.avgConf || 0,
      lastAction: activity?.lastAction || "",
      lastRunAt: activity?.lastRunAt || "",
      status: activity ? "active" as const : "idle" as const,
    };
  });

  // Tier counts
  const tierCounts = { tier1: 0, tier2: 0, tier3: 0 };
  for (const a of agents) {
    const tc = tierConfig(a.tier);
    tierCounts[tc.key as keyof typeof tierCounts] += 1;
  }

  const selectedAgentEvents = selectedAgent
    ? events.filter((e) => e.agent_name === selectedAgent)
    : [];

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Agent Monitor</h1>
          <p className="text-sm text-gray-500">Real-time monitoring of autonomous clinical AI agents</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 ring-1 ring-inset ring-emerald-500/20">
            <span className="status-dot-live" />
            <span className="text-xs font-semibold text-emerald-700">Live Monitoring</span>
          </div>
        </div>
      </div>

      {/* Tier overview cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { key: "tier1", label: "Tier 1 — Autonomous", desc: "Fully automated decisions", icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" },
          { key: "tier2", label: "Tier 2 — Supervised", desc: "Requires human approval", icon: "M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" },
          { key: "tier3", label: "Tier 3 — Advisory", desc: "Suggestions only, clinician decides", icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" },
        ].map(({ key, label, desc, icon }) => {
          const cfg = TIER_MAP[key === "tier1" ? "autonomous" : key === "tier2" ? "supervised" : "advisory"];
          return (
            <div key={key} className="metric-card">
              <div className={`absolute left-0 top-0 h-1 w-full rounded-t-xl ${cfg.gradient}`} />
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">{label}</p>
                  <p className="mt-2 text-3xl font-bold tabular-nums text-gray-900">{tierCounts[key as keyof typeof tierCounts]}</p>
                  <p className="mt-1 text-xs text-gray-500">{desc}</p>
                </div>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${cfg.bg} ring-1 ring-inset ${cfg.ring}`}>
                  <svg className={`h-5 w-5 ${cfg.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
                  </svg>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Agent list */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Registered Agents ({agents.length})</h2>
            </div>

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 rounded-xl p-3 animate-pulse">
                    <div className="skeleton-circle h-12 w-12" />
                    <div className="flex-1 space-y-2">
                      <div className="skeleton-text w-40" />
                      <div className="skeleton-text w-28" />
                    </div>
                    <div className="skeleton h-12 w-12 rounded-full" />
                  </div>
                ))}
              </div>
            ) : agents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
                  <svg className="h-7 w-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                  </svg>
                </div>
                <p className="mt-3 text-sm text-gray-500">No agents registered</p>
              </div>
            ) : (
              <div className="space-y-1">
                {agents.map((agent, i) => {
                  const tcfg = tierConfig(agent.tier);
                  const isSelected = selectedAgent === agent.name;
                  const hasActivity = agent.totalRuns > 0;
                  return (
                    <button
                      key={agent.name}
                      onClick={() => setSelectedAgent(isSelected ? null : agent.name)}
                      className={`flex w-full items-center gap-4 rounded-xl p-3 text-left transition-all duration-200 animate-fade-in ${
                        isSelected ? "bg-healthos-50 ring-1 ring-healthos-500/20" : "hover:bg-gray-50"
                      }`}
                      style={{ animationDelay: `${i * 0.05}s`, animationFillMode: "both" }}
                    >
                      {/* Agent icon */}
                      <div className={`flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl ${tcfg.bg} ring-1 ring-inset ${tcfg.ring}`}>
                        <svg className={`h-5 w-5 ${tcfg.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                        </svg>
                      </div>

                      {/* Info */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-gray-900">{agent.name}</p>
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${tcfg.bg} ${tcfg.text} ring-1 ring-inset ${tcfg.ring}`}>
                            {agent.tier}
                          </span>
                          {agent.requires_hitl && (
                            <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700 ring-1 ring-inset ring-amber-500/20">
                              HITL
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs text-gray-500 truncate">{agent.description}</p>
                        <p className="mt-0.5 text-xs text-gray-400">
                          v{agent.version}
                          {hasActivity && <> &middot; {agent.totalRuns} run{agent.totalRuns !== 1 ? "s" : ""} &middot; Last: {timeAgo(agent.lastRunAt)}</>}
                          {!hasActivity && <> &middot; Idle</>}
                        </p>
                      </div>

                      {/* Status / Confidence */}
                      {hasActivity ? (
                        <ConfidenceRing value={agent.avgConfidence} />
                      ) : (
                        <div className="flex h-12 w-12 items-center justify-center">
                          <span className="flex items-center gap-1.5 text-xs text-gray-400">
                            <span className="h-2 w-2 rounded-full bg-gray-300" />
                            Idle
                          </span>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Activity timeline */}
        <div>
          <div className="card sticky top-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
                {selectedAgent ? `${selectedAgent} Activity` : "Recent Activity"}
              </h2>
              {selectedAgent && (
                <button onClick={() => setSelectedAgent(null)} className="text-xs text-healthos-600 hover:text-healthos-700">
                  Show all
                </button>
              )}
            </div>

            <div className="space-y-1">
              {(selectedAgent ? selectedAgentEvents : events).slice(0, 10).map((event, i) => (
                <div
                  key={event.id}
                  className="flex items-start gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-gray-50 animate-fade-in"
                  style={{ animationDelay: `${i * 0.04}s`, animationFillMode: "both" }}
                >
                  <div className="relative mt-1.5 flex-shrink-0">
                    <span className="block h-2 w-2 rounded-full bg-healthos-400" />
                    {i < (selectedAgent ? selectedAgentEvents : events).slice(0, 10).length - 1 && (
                      <span className="absolute left-[3px] top-3 h-6 w-px bg-gray-200" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-700">
                      <span className="font-semibold text-gray-900">{event.agent_name}</span>{" "}
                      <span className="text-gray-500">{event.action}</span>
                    </p>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-400">
                      {event.created_at && <span>{timeAgo(event.created_at)}</span>}
                      {event.confidence_score != null && (
                        <>
                          <span>&middot;</span>
                          <span className="flex items-center gap-1">
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              event.confidence_score >= 0.9 ? "bg-emerald-500" :
                              event.confidence_score >= 0.7 ? "bg-amber-500" : "bg-red-500"
                            }`} />
                            {Math.round(event.confidence_score * 100)}%
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {events.length === 0 && !loading && (
                <div className="flex flex-col items-center py-8">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="mt-2 text-xs text-gray-400">No activity recorded yet</p>
                  <p className="mt-1 text-[10px] text-gray-300">Agent activity will appear here when agents process events</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
