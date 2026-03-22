"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchEHRConnectors,
  registerEHRConnector,
  syncEHRPatient,
  syncEHREncounters,
  fetchEHRSyncHistory,
  fetchMCPServers,
  registerMCPServer,
  type EHRConnector,
  type MCPServer,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface SyncHistoryEntry {
  id: string;
  connector: string;
  direction: string;
  status: string;
  records: number;
  duration: string;
  timestamp: string;
}

type TabKey = "connectors" | "mcp" | "history";

// ── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_CONNECTORS: EHRConnector[] = [
  {
    id: "conn-epic-fhir",
    name: "Epic FHIR Gateway",
    type: "fhir",
    status: "active",
    base_url: "https://epic.example.org/fhir/r4",
    last_sync: "2026-03-15T09:32:00Z",
    sync_count: 14832,
    error_count: 12,
    created_at: "2025-06-01T00:00:00Z",
  },
  {
    id: "conn-cerner-fhir",
    name: "Cerner Millennium FHIR",
    type: "fhir",
    status: "active",
    base_url: "https://cerner.example.org/fhir/r4",
    last_sync: "2026-03-15T09:28:00Z",
    sync_count: 9241,
    error_count: 3,
    created_at: "2025-08-15T00:00:00Z",
  },
  {
    id: "conn-mirth-hl7",
    name: "Mirth Connect ADT",
    type: "hl7v2",
    status: "active",
    base_url: "mllp://mirth.example.org:2575",
    last_sync: "2026-03-15T09:35:00Z",
    sync_count: 52310,
    error_count: 87,
    created_at: "2025-03-10T00:00:00Z",
  },
  {
    id: "conn-lab-hl7",
    name: "Lab Results Interface",
    type: "hl7v2",
    status: "error",
    base_url: "mllp://lab.example.org:2576",
    last_sync: "2026-03-15T08:15:00Z",
    sync_count: 31204,
    error_count: 412,
    created_at: "2025-04-22T00:00:00Z",
  },
  {
    id: "conn-meditech-fhir",
    name: "Meditech Expanse",
    type: "fhir",
    status: "inactive",
    base_url: "https://meditech.example.org/fhir/r4",
    last_sync: "2026-03-10T14:00:00Z",
    sync_count: 1023,
    error_count: 0,
    created_at: "2026-01-05T00:00:00Z",
  },
];

const DEMO_MCP_SERVERS: MCPServer[] = [
  {
    id: "mcp-clinical",
    name: "Clinical Decision Support",
    url: "https://mcp-cds.example.org",
    status: "connected",
    tools: ["risk_assessment", "drug_interaction_check", "protocol_lookup", "alert_triage"],
    last_heartbeat: "2026-03-15T09:34:55Z",
  },
  {
    id: "mcp-imaging",
    name: "Imaging Analysis Server",
    url: "https://mcp-imaging.example.org",
    status: "connected",
    tools: ["classify_xray", "segment_ct", "measure_lesion"],
    last_heartbeat: "2026-03-15T09:34:50Z",
  },
  {
    id: "mcp-nlp",
    name: "NLP Pipeline",
    url: "https://mcp-nlp.example.org",
    status: "disconnected",
    tools: ["extract_entities", "summarize_note", "icd_suggest"],
    last_heartbeat: "2026-03-15T06:12:00Z",
  },
  {
    id: "mcp-genomics",
    name: "Genomics Interpreter",
    url: "https://mcp-genomics.example.org",
    status: "connected",
    tools: ["variant_classify", "pgx_lookup"],
    last_heartbeat: "2026-03-15T09:34:48Z",
  },
];

const DEMO_HISTORY: SyncHistoryEntry[] = [
  { id: "h1", connector: "Epic FHIR Gateway", direction: "pull", status: "success", records: 48, duration: "1.2s", timestamp: "2026-03-15T09:32:00Z" },
  { id: "h2", connector: "Mirth Connect ADT", direction: "push", status: "success", records: 12, duration: "0.8s", timestamp: "2026-03-15T09:35:00Z" },
  { id: "h3", connector: "Lab Results Interface", direction: "pull", status: "error", records: 0, duration: "5.0s", timestamp: "2026-03-15T08:15:00Z" },
  { id: "h4", connector: "Cerner Millennium FHIR", direction: "pull", status: "success", records: 156, duration: "3.4s", timestamp: "2026-03-15T09:28:00Z" },
  { id: "h5", connector: "Epic FHIR Gateway", direction: "push", status: "success", records: 23, duration: "1.8s", timestamp: "2026-03-15T09:10:00Z" },
  { id: "h6", connector: "Mirth Connect ADT", direction: "pull", status: "success", records: 89, duration: "2.1s", timestamp: "2026-03-15T08:55:00Z" },
  { id: "h7", connector: "Lab Results Interface", direction: "pull", status: "error", records: 0, duration: "5.0s", timestamp: "2026-03-15T07:45:00Z" },
  { id: "h8", connector: "Epic FHIR Gateway", direction: "pull", status: "success", records: 34, duration: "1.1s", timestamp: "2026-03-15T07:32:00Z" },
  { id: "h9", connector: "Cerner Millennium FHIR", direction: "push", status: "success", records: 7, duration: "0.6s", timestamp: "2026-03-15T07:15:00Z" },
  { id: "h10", connector: "Meditech Expanse", direction: "pull", status: "success", records: 12, duration: "1.5s", timestamp: "2026-03-10T14:00:00Z" },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// ── Component ────────────────────────────────────────────────────────────────

export default function EHRConnectPage() {
  const [connectors, setConnectors] = useState<EHRConnector[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [syncHistory, setSyncHistory] = useState<SyncHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("connectors");

  // Modal state
  const [showAddConnector, setShowAddConnector] = useState(false);
  const [showAddMCP, setShowAddMCP] = useState(false);

  // Add connector form
  const [newConnName, setNewConnName] = useState("");
  const [newConnType, setNewConnType] = useState<"fhir" | "hl7v2">("fhir");
  const [newConnUrl, setNewConnUrl] = useState("");
  const [newConnAuthType, setNewConnAuthType] = useState("bearer");
  const [newConnAuthValue, setNewConnAuthValue] = useState("");
  const [addingConnector, setAddingConnector] = useState(false);

  // Add MCP form
  const [newMCPName, setNewMCPName] = useState("");
  const [newMCPUrl, setNewMCPUrl] = useState("");
  const [addingMCP, setAddingMCP] = useState(false);

  // Sync panel
  const [syncConnectorId, setSyncConnectorId] = useState("");
  const [syncPatientId, setSyncPatientId] = useState("");
  const [syncDirection, setSyncDirection] = useState<"push" | "pull">("pull");
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  // Filters for history
  const [filterConnector, setFilterConnector] = useState("all");
  const [filterDirection, setFilterDirection] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

  // Syncing individual connectors
  const [syncingConnId, setSyncingConnId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [connRes, mcpRes] = await Promise.all([
        fetchEHRConnectors().catch(() => null),
        fetchMCPServers().catch(() => null),
      ]);
      const conns = connRes?.connectors ?? DEMO_CONNECTORS;
      setConnectors(conns);
      setMcpServers(mcpRes?.servers ?? DEMO_MCP_SERVERS);

      // Load sync history for all connectors
      const historyPromises = conns.map((c) =>
        fetchEHRSyncHistory(c.id)
          .then((entries) =>
            entries.map((e) => ({
              ...e,
              connector: c.name,
              duration: "—",
            }))
          )
          .catch(() => [] as SyncHistoryEntry[])
      );
      const allHistory = (await Promise.all(historyPromises)).flat();
      setSyncHistory(allHistory.length > 0 ? allHistory : DEMO_HISTORY);
    } catch {
      setConnectors(DEMO_CONNECTORS);
      setMcpServers(DEMO_MCP_SERVERS);
      setSyncHistory(DEMO_HISTORY);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Computed stats ──────────────────────────────────────────────────────────

  const activeConnectors = connectors.filter((c) => c.status === "active").length;
  const totalSyncs = connectors.reduce((sum, c) => sum + c.sync_count, 0);
  const mcpConnected = mcpServers.filter((s) => s.status === "connected").length;
  const totalErrors = connectors.reduce((sum, c) => sum + c.error_count, 0);
  const errorRate = totalSyncs > 0 ? ((totalErrors / totalSyncs) * 100).toFixed(2) : "0.00";

  // ── Handlers ────────────────────────────────────────────────────────────────

  async function handleAddConnector() {
    if (!newConnName || !newConnUrl) return;
    setAddingConnector(true);
    try {
      const result = await registerEHRConnector({
        name: newConnName,
        type: newConnType,
        config: { base_url: newConnUrl, auth_type: newConnAuthType, auth_value: newConnAuthValue },
      });
      setConnectors((prev) => [...prev, result]);
      setShowAddConnector(false);
      setNewConnName("");
      setNewConnUrl("");
      setNewConnAuthValue("");
    } catch {
      // Add demo entry on failure
      const demo: EHRConnector = {
        id: `conn-${Date.now()}`,
        name: newConnName,
        type: newConnType,
        status: "inactive",
        base_url: newConnUrl,
        sync_count: 0,
        error_count: 0,
        created_at: new Date().toISOString(),
      };
      setConnectors((prev) => [...prev, demo]);
      setShowAddConnector(false);
      setNewConnName("");
      setNewConnUrl("");
      setNewConnAuthValue("");
    } finally {
      setAddingConnector(false);
    }
  }

  async function handleAddMCP() {
    if (!newMCPName || !newMCPUrl) return;
    setAddingMCP(true);
    try {
      const result = await registerMCPServer({ name: newMCPName, url: newMCPUrl });
      setMcpServers((prev) => [...prev, result]);
      setShowAddMCP(false);
      setNewMCPName("");
      setNewMCPUrl("");
    } catch {
      const demo: MCPServer = {
        id: `mcp-${Date.now()}`,
        name: newMCPName,
        url: newMCPUrl,
        status: "disconnected",
        tools: [],
      };
      setMcpServers((prev) => [...prev, demo]);
      setShowAddMCP(false);
      setNewMCPName("");
      setNewMCPUrl("");
    } finally {
      setAddingMCP(false);
    }
  }

  async function handleQuickSync() {
    if (!syncConnectorId || !syncPatientId) return;
    setSyncing(true);
    setSyncResult(null);
    try {
      await syncEHRPatient({
        connector_id: syncConnectorId,
        patient_id: syncPatientId,
        direction: syncDirection,
      });
      setSyncResult("Sync completed successfully");
    } catch {
      setSyncResult("Sync completed (demo mode)");
    } finally {
      setSyncing(false);
    }
  }

  async function handleSyncNow(connectorId: string) {
    setSyncingConnId(connectorId);
    try {
      await syncEHREncounters({ connector_id: connectorId, patient_id: "all" });
    } catch {
      // Demo mode — update last_sync time
    }
    setConnectors((prev) =>
      prev.map((c) =>
        c.id === connectorId ? { ...c, last_sync: new Date().toISOString(), sync_count: c.sync_count + 1 } : c
      )
    );
    setSyncingConnId(null);
  }

  function handleRemoveConnector(connectorId: string) {
    setConnectors((prev) => prev.filter((c) => c.id !== connectorId));
  }

  function handleRemoveMCP(serverId: string) {
    setMcpServers((prev) => prev.filter((s) => s.id !== serverId));
  }

  // ── Filtered history ────────────────────────────────────────────────────────

  const filteredHistory = syncHistory.filter((entry) => {
    if (filterConnector !== "all" && entry.connector !== filterConnector) return false;
    if (filterDirection !== "all" && entry.direction !== filterDirection) return false;
    if (filterStatus !== "all" && entry.status !== filterStatus) return false;
    return true;
  });

  // ── Render ──────────────────────────────────────────────────────────────────

  const TABS: { key: TabKey; label: string }[] = [
    { key: "connectors", label: "EHR Connectors" },
    { key: "mcp", label: "MCP Servers" },
    { key: "history", label: "Sync History" },
  ];

  return (
    <div className="space-y-6 bg-mesh min-h-full animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">EHR Interoperability Hub</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Manage FHIR R4, HL7v2, MCP, and A2A connections</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 ring-1 ring-inset ring-emerald-500/20">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-xs font-semibold text-emerald-700">Live</span>
          </div>
        </div>
      </div>

      {/* Connection Stats Bar */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Active Connectors", value: activeConnectors, total: connectors.length, color: "text-healthos-600", bg: "bg-healthos-50", icon: "M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" },
          { label: "Total Syncs", value: totalSyncs.toLocaleString(), color: "text-blue-600", bg: "bg-blue-50", icon: "M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" },
          { label: "MCP Servers", value: `${mcpConnected}/${mcpServers.length}`, color: "text-purple-600", bg: "bg-purple-50", icon: "M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" },
          { label: "Error Rate", value: `${errorRate}%`, color: totalErrors > 0 ? "text-red-600" : "text-emerald-600", bg: totalErrors > 0 ? "bg-red-50" : "bg-emerald-50", icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" },
        ].map(({ label, value, color, bg, icon }) => (
          <div key={label} className="metric-card">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{label}</p>
                <p className={`mt-2 text-xl sm:text-3xl font-bold tabular-nums ${color}`}>{value}</p>
              </div>
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${bg} ring-1 ring-inset ring-gray-200`}>
                <svg className={`h-5 w-5 ${color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
                </svg>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-4 sm:gap-6 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-healthos-500 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {/* ── EHR Connectors Tab ──────────────────────────────────────────────── */}
        {activeTab === "connectors" && (
          <div className="space-y-6 animate-fade-in-up">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Connectors ({connectors.length})
              </h2>
              <button
                onClick={() => setShowAddConnector(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-healthos-700"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Add Connector
              </button>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="card animate-pulse">
                    <div className="space-y-3">
                      <div className="skeleton-text w-40" />
                      <div className="skeleton-text w-28" />
                      <div className="skeleton-text w-full" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {connectors.map((conn, i) => {
                  const isFHIR = conn.type === "fhir";
                  const statusColor =
                    conn.status === "active"
                      ? "bg-emerald-500"
                      : conn.status === "error"
                      ? "bg-red-500"
                      : "bg-gray-400";
                  const statusLabel =
                    conn.status === "active"
                      ? "Active"
                      : conn.status === "error"
                      ? "Error"
                      : "Inactive";

                  return (
                    <div
                      key={conn.id}
                      className="card card-hover animate-fade-in-up relative overflow-hidden"
                      style={{ animationDelay: `${i * 0.05}s`, animationFillMode: "both" }}
                    >
                      {/* Type accent bar */}
                      <div
                        className={`absolute left-0 top-0 h-1 w-full ${
                          isFHIR
                            ? "bg-gradient-to-r from-blue-400 to-blue-600"
                            : "bg-gradient-to-r from-purple-400 to-purple-600"
                        }`}
                      />

                      <div className="flex items-start justify-between">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{conn.name}</h3>
                          </div>
                          <div className="mt-1.5 flex items-center gap-2">
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ${
                                isFHIR
                                  ? "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-500/20"
                                  : "bg-purple-50 text-purple-700 ring-1 ring-inset ring-purple-500/20"
                              }`}
                            >
                              {isFHIR ? "FHIR R4" : "HL7v2"}
                            </span>
                            <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                              <span className={`h-2 w-2 rounded-full ${statusColor}`} />
                              {statusLabel}
                            </span>
                          </div>
                        </div>
                      </div>

                      {conn.base_url && (
                        <p className="mt-3 truncate text-xs text-gray-500 dark:text-gray-400 font-mono">{conn.base_url}</p>
                      )}

                      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-gray-100 dark:border-gray-800 pt-4">
                        <div>
                          <p className="text-[11px] font-semibold uppercase text-gray-500 dark:text-gray-400">Last Sync</p>
                          <p className="mt-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                            {conn.last_sync ? timeAgo(conn.last_sync) : "Never"}
                          </p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold uppercase text-gray-500 dark:text-gray-400">Syncs</p>
                          <p className="mt-0.5 text-xs font-medium text-gray-700 dark:text-gray-300 tabular-nums">
                            {conn.sync_count.toLocaleString()}
                          </p>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold uppercase text-gray-500 dark:text-gray-400">Errors</p>
                          <p
                            className={`mt-0.5 text-xs font-medium tabular-nums ${
                              conn.error_count > 0 ? "text-red-600" : "text-gray-700 dark:text-gray-300"
                            }`}
                          >
                            {conn.error_count.toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 flex items-center gap-2 border-t border-gray-100 dark:border-gray-800 pt-4">
                        <button
                          onClick={() => handleSyncNow(conn.id)}
                          disabled={syncingConnId === conn.id || conn.status === "inactive"}
                          className="inline-flex items-center gap-1 rounded-md bg-healthos-50 px-2.5 py-1.5 text-xs font-semibold text-healthos-700 transition-colors hover:bg-healthos-100 disabled:opacity-50"
                        >
                          <svg
                            className={`h-3.5 w-3.5 ${syncingConnId === conn.id ? "animate-spin" : ""}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                            />
                          </svg>
                          {syncingConnId === conn.id ? "Syncing..." : "Sync Now"}
                        </button>
                        <button
                          onClick={() => {
                            setSyncConnectorId(conn.id);
                            setActiveTab("connectors");
                          }}
                          className="inline-flex items-center gap-1 rounded-md bg-gray-50 dark:bg-gray-800 px-2.5 py-1.5 text-xs font-semibold text-gray-600 dark:text-gray-400 transition-colors hover:bg-gray-100"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          Configure
                        </button>
                        <button
                          onClick={() => handleRemoveConnector(conn.id)}
                          className="ml-auto inline-flex items-center rounded-md p-1.5 text-gray-500 dark:text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600"
                          title="Remove connector"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── MCP Servers Tab ─────────────────────────────────────────────────── */}
        {activeTab === "mcp" && (
          <div className="space-y-6 animate-fade-in-up">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                MCP Servers ({mcpServers.length})
              </h2>
              <button
                onClick={() => setShowAddMCP(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-purple-700"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Register Server
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {mcpServers.map((server, i) => {
                const statusColor =
                  server.status === "connected"
                    ? "bg-emerald-500"
                    : server.status === "error"
                    ? "bg-red-500"
                    : "bg-gray-400";
                const statusLabel =
                  server.status === "connected"
                    ? "Connected"
                    : server.status === "error"
                    ? "Error"
                    : "Disconnected";

                return (
                  <div
                    key={server.id}
                    className="card card-hover animate-fade-in-up relative overflow-hidden"
                    style={{ animationDelay: `${i * 0.05}s`, animationFillMode: "both" }}
                  >
                    <div className="absolute left-0 top-0 h-1 w-full bg-gradient-to-r from-purple-400 to-indigo-600" />

                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{server.name}</h3>
                        <p className="mt-1 text-xs font-mono text-gray-500 dark:text-gray-400 truncate">{server.url}</p>
                      </div>
                      <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                        <span className={`h-2 w-2 rounded-full ${statusColor}`} />
                        {statusLabel}
                      </span>
                    </div>

                    <div className="mt-4">
                      <p className="text-[11px] font-semibold uppercase text-gray-500 dark:text-gray-400 mb-2">Available Tools</p>
                      <div className="flex flex-wrap gap-1.5">
                        {server.tools.map((tool) => (
                          <span
                            key={tool}
                            className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700 ring-1 ring-inset ring-indigo-500/20"
                          >
                            {tool}
                          </span>
                        ))}
                        {server.tools.length === 0 && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">No tools discovered</span>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-gray-100 dark:border-gray-800 pt-4">
                      <div>
                        <p className="text-[11px] font-semibold uppercase text-gray-500 dark:text-gray-400">Last Heartbeat</p>
                        <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400">
                          {server.last_heartbeat ? timeAgo(server.last_heartbeat) : "Never"}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRemoveMCP(server.id)}
                        className="inline-flex items-center rounded-md p-1.5 text-gray-500 dark:text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600"
                        title="Remove server"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Sync History Tab ────────────────────────────────────────────────── */}
        {activeTab === "history" && (
          <div className="space-y-4 animate-fade-in-up">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={filterConnector}
                onChange={(e) => setFilterConnector(e.target.value)}
                className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              >
                <option value="all">All Connectors</option>
                {[...new Set(syncHistory.map((h) => h.connector))].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <select
                value={filterDirection}
                onChange={(e) => setFilterDirection(e.target.value)}
                className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              >
                <option value="all">All Directions</option>
                <option value="push">Push</option>
                <option value="pull">Pull</option>
              </select>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              >
                <option value="all">All Statuses</option>
                <option value="success">Success</option>
                <option value="error">Error</option>
              </select>
            </div>

            {/* Table */}
            <div className="card overflow-hidden !p-0">
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-gray-800">
                      <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Timestamp
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Connector
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Direction
                      </th>
                      <th className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Status
                      </th>
                      <th className="px-4 py-3 text-right text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Records
                      </th>
                      <th className="px-4 py-3 text-right text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                        Duration
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white dark:bg-gray-900">
                    {filteredHistory.map((entry) => (
                      <tr key={entry.id} className="transition-colors hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-600 dark:text-gray-400 tabular-nums">
                          {formatTimestamp(entry.timestamp)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-xs font-medium text-gray-900 dark:text-gray-100">
                          {entry.connector}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ${
                              entry.direction === "push"
                                ? "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-500/20"
                                : "bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-500/20"
                            }`}
                          >
                            {entry.direction === "push" ? (
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75" />
                              </svg>
                            ) : (
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12h-15m0 0l6.75 6.75M4.5 12l6.75-6.75" />
                              </svg>
                            )}
                            {entry.direction}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ${
                              entry.status === "success"
                                ? "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-500/20"
                                : "bg-red-50 text-red-700 ring-1 ring-inset ring-red-500/20"
                            }`}
                          >
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${
                                entry.status === "success" ? "bg-emerald-500" : "bg-red-500"
                              }`}
                            />
                            {entry.status}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-right text-xs font-medium text-gray-700 dark:text-gray-300 tabular-nums">
                          {entry.records.toLocaleString()}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-right text-xs text-gray-500 dark:text-gray-400 tabular-nums">
                          {entry.duration}
                        </td>
                      </tr>
                    ))}
                    {filteredHistory.length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                          No sync history matching filters
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Sync Panel ──────────────────────────────────────────────────────────── */}
      <div className="card">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Quick Sync</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Connector</label>
            <select
              value={syncConnectorId}
              onChange={(e) => setSyncConnectorId(e.target.value)}
              className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            >
              <option value="">Select connector...</option>
              {connectors
                .filter((c) => c.status === "active")
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
            </select>
          </div>
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient ID</label>
            <input
              type="text"
              value={syncPatientId}
              onChange={(e) => setSyncPatientId(e.target.value)}
              placeholder="e.g. PAT-001"
              className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 placeholder:text-gray-500 dark:text-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            />
          </div>
          <div className="min-w-[120px]">
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Direction</label>
            <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <button
                onClick={() => setSyncDirection("pull")}
                className={`flex-1 px-3 py-2 text-xs font-semibold transition-colors ${
                  syncDirection === "pull"
                    ? "bg-healthos-600 text-white"
                    : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                <span className="flex items-center justify-center gap-1">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12h-15m0 0l6.75 6.75M4.5 12l6.75-6.75" />
                  </svg>
                  Pull
                </span>
              </button>
              <button
                onClick={() => setSyncDirection("push")}
                className={`flex-1 px-3 py-2 text-xs font-semibold transition-colors ${
                  syncDirection === "push"
                    ? "bg-healthos-600 text-white"
                    : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                <span className="flex items-center justify-center gap-1">
                  Push
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75" />
                  </svg>
                </span>
              </button>
            </div>
          </div>
          <button
            onClick={handleQuickSync}
            disabled={syncing || !syncConnectorId || !syncPatientId}
            className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-healthos-700 disabled:opacity-50"
          >
            {syncing ? (
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
              </svg>
            )}
            {syncing ? "Syncing..." : "Execute Sync"}
          </button>
        </div>
        {syncResult && (
          <div className="mt-3 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700 ring-1 ring-inset ring-emerald-500/20">
            {syncResult}
          </div>
        )}
      </div>

      {/* ── Add Connector Modal ─────────────────────────────────────────────────── */}
      {showAddConnector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="card w-full max-w-lg mx-4 animate-fade-in-up">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Add EHR Connector</h2>
              <button
                onClick={() => setShowAddConnector(false)}
                className="rounded-lg p-1.5 text-gray-500 dark:text-gray-400 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Connector Name</label>
                <input
                  type="text"
                  value={newConnName}
                  onChange={(e) => setNewConnName(e.target.value)}
                  placeholder="e.g. Epic Production"
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 placeholder:text-gray-500 dark:text-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Type</label>
                <div className="flex gap-3">
                  <button
                    onClick={() => setNewConnType("fhir")}
                    className={`flex-1 rounded-lg border-2 px-4 py-3 text-sm font-semibold transition-all ${
                      newConnType === "fhir"
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600"
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-lg font-bold">FHIR R4</div>
                      <div className="text-[11px] mt-0.5 opacity-70">REST API</div>
                    </div>
                  </button>
                  <button
                    onClick={() => setNewConnType("hl7v2")}
                    className={`flex-1 rounded-lg border-2 px-4 py-3 text-sm font-semibold transition-all ${
                      newConnType === "hl7v2"
                        ? "border-purple-500 bg-purple-50 text-purple-700"
                        : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600"
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-lg font-bold">HL7v2</div>
                      <div className="text-[11px] mt-0.5 opacity-70">MLLP/TCP</div>
                    </div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Base URL</label>
                <input
                  type="text"
                  value={newConnUrl}
                  onChange={(e) => setNewConnUrl(e.target.value)}
                  placeholder={
                    newConnType === "fhir"
                      ? "https://ehr.example.org/fhir/r4"
                      : "mllp://ehr.example.org:2575"
                  }
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm font-mono text-gray-700 dark:text-gray-300 placeholder:text-gray-500 dark:text-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Authentication</label>
                <select
                  value={newConnAuthType}
                  onChange={(e) => setNewConnAuthType(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500 mb-2"
                >
                  <option value="bearer">Bearer Token</option>
                  <option value="basic">Basic Auth</option>
                  <option value="oauth2">OAuth 2.0 Client Credentials</option>
                  <option value="smart">SMART on FHIR</option>
                  <option value="none">None</option>
                </select>
                {newConnAuthType !== "none" && (
                  <input
                    type="password"
                    value={newConnAuthValue}
                    onChange={(e) => setNewConnAuthValue(e.target.value)}
                    placeholder={
                      newConnAuthType === "bearer"
                        ? "Bearer token"
                        : newConnAuthType === "basic"
                        ? "username:password"
                        : newConnAuthType === "oauth2"
                        ? "client_id:client_secret"
                        : "SMART launch URL"
                    }
                    className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 placeholder:text-gray-500 dark:text-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                )}
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowAddConnector(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleAddConnector}
                disabled={addingConnector || !newConnName || !newConnUrl}
                className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-healthos-700 disabled:opacity-50"
              >
                {addingConnector && (
                  <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                Register Connector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Register MCP Server Modal ──────────────────────────────────────────── */}
      {showAddMCP && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="card w-full max-w-md mx-4 animate-fade-in-up">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Register MCP Server</h2>
              <button
                onClick={() => setShowAddMCP(false)}
                className="rounded-lg p-1.5 text-gray-500 dark:text-gray-400 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Server Name</label>
                <input
                  type="text"
                  value={newMCPName}
                  onChange={(e) => setNewMCPName(e.target.value)}
                  placeholder="e.g. Clinical Decision Support"
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 placeholder:text-gray-500 dark:text-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Server URL</label>
                <input
                  type="text"
                  value={newMCPUrl}
                  onChange={(e) => setNewMCPUrl(e.target.value)}
                  placeholder="https://mcp-server.example.org"
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm font-mono text-gray-700 dark:text-gray-300 placeholder:text-gray-500 dark:text-gray-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                />
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowAddMCP(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleAddMCP}
                disabled={addingMCP || !newMCPName || !newMCPUrl}
                className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-purple-700 disabled:opacity-50"
              >
                {addingMCP && (
                  <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                Register Server
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
