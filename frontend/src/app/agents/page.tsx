"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchAgents,
  fetchAgentActivity,
  fetchPipelineExecutions,
  triggerPipeline,
  fetchHITLQueue,
  resolveHITLItem,
  type AgentActivityResponse,
  type PipelineExecution,
  type HITLReviewItem,
} from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface RegisteredAgent {
  name: string;
  tier: string;
  version: string;
  description: string;
  requires_hitl: boolean;
}

type TabKey = "pipelines" | "registry" | "hitl" | "audit";

// ── Demo / fallback data ─────────────────────────────────────────────────────

const DEMO_AGENTS: RegisteredAgent[] = [
  { name: "VitalIngestion", tier: "sensing", version: "2.1.0", description: "Ingests and normalizes real-time vital streams from IoT devices", requires_hitl: false },
  { name: "AnomalyDetector", tier: "sensing", version: "1.4.2", description: "Detects anomalous vital patterns using statistical models", requires_hitl: false },
  { name: "LabNormalizer", tier: "sensing", version: "1.0.3", description: "Normalizes lab results to standard reference ranges", requires_hitl: false },
  { name: "ClinicalReasoner", tier: "reasoning", version: "3.0.1", description: "Synthesizes patient data into clinical assessments", requires_hitl: false },
  { name: "DiagnosisAssist", tier: "reasoning", version: "2.2.0", description: "Suggests differential diagnoses from symptom clusters", requires_hitl: true },
  { name: "DrugInteractionChecker", tier: "reasoning", version: "1.7.1", description: "Checks multi-drug interaction risks using knowledge graph", requires_hitl: false },
  { name: "RiskScorer", tier: "decision", version: "2.5.0", description: "Calculates patient risk scores for readmission and deterioration", requires_hitl: false },
  { name: "TreatmentRecommender", tier: "decision", version: "1.3.0", description: "Recommends treatment plans based on clinical evidence", requires_hitl: true },
  { name: "AlertPrioritizer", tier: "decision", version: "1.1.2", description: "Prioritizes clinical alerts by severity and clinical context", requires_hitl: false },
  { name: "PipelineOrchestrator", tier: "orchestration", version: "4.0.0", description: "Coordinates multi-agent pipelines and manages execution flow", requires_hitl: false },
  { name: "PolicyGuard", tier: "orchestration", version: "2.0.1", description: "Enforces clinical governance policies across agent decisions", requires_hitl: false },
  { name: "AuditLogger", tier: "orchestration", version: "1.2.0", description: "Records immutable audit trail of all agent actions", requires_hitl: false },
];

const DEMO_PIPELINES: PipelineExecution[] = [
  {
    trace_id: "trc-a1b2c3d4e5f6",
    status: "completed",
    trigger_event: "vital_ingestion",
    patient_id: "PT-00142",
    started_at: new Date(Date.now() - 180000).toISOString(),
    completed_at: new Date(Date.now() - 60000).toISOString(),
    hitl_required: false,
    agents: [
      { name: "VitalIngestion", tier: "sensing", status: "completed", duration_ms: 320, confidence: 0.99, output_summary: "12 vitals ingested" },
      { name: "AnomalyDetector", tier: "sensing", status: "completed", duration_ms: 890, confidence: 0.94, output_summary: "1 anomaly detected" },
      { name: "ClinicalReasoner", tier: "reasoning", status: "completed", duration_ms: 1540, confidence: 0.87, output_summary: "Elevated HR pattern" },
      { name: "RiskScorer", tier: "decision", status: "completed", duration_ms: 450, confidence: 0.91, output_summary: "Risk: moderate" },
      { name: "PolicyGuard", tier: "orchestration", status: "completed", duration_ms: 120, confidence: 0.98, output_summary: "Policy: pass" },
    ],
  },
  {
    trace_id: "trc-f7e8d9c0b1a2",
    status: "running",
    trigger_event: "lab_result_received",
    patient_id: "PT-00287",
    started_at: new Date(Date.now() - 45000).toISOString(),
    hitl_required: false,
    agents: [
      { name: "LabNormalizer", tier: "sensing", status: "completed", duration_ms: 210, confidence: 0.97 },
      { name: "ClinicalReasoner", tier: "reasoning", status: "completed", duration_ms: 1120, confidence: 0.82 },
      { name: "DrugInteractionChecker", tier: "reasoning", status: "running", duration_ms: 0 },
      { name: "TreatmentRecommender", tier: "decision", status: "pending", duration_ms: 0 },
      { name: "PolicyGuard", tier: "orchestration", status: "pending", duration_ms: 0 },
    ],
  },
  {
    trace_id: "trc-1234abcd5678",
    status: "halted",
    trigger_event: "treatment_recommendation",
    patient_id: "PT-00091",
    started_at: new Date(Date.now() - 600000).toISOString(),
    hitl_required: true,
    agents: [
      { name: "ClinicalReasoner", tier: "reasoning", status: "completed", duration_ms: 1800, confidence: 0.78 },
      { name: "DiagnosisAssist", tier: "reasoning", status: "completed", duration_ms: 2200, confidence: 0.65 },
      { name: "TreatmentRecommender", tier: "decision", status: "halted", duration_ms: 0, output_summary: "Low confidence — HITL required" },
    ],
  },
  {
    trace_id: "trc-9876fedc5432",
    status: "failed",
    trigger_event: "scheduled_risk_assessment",
    patient_id: "PT-00415",
    started_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: new Date(Date.now() - 3540000).toISOString(),
    hitl_required: false,
    agents: [
      { name: "VitalIngestion", tier: "sensing", status: "completed", duration_ms: 280, confidence: 0.96 },
      { name: "RiskScorer", tier: "decision", status: "failed", duration_ms: 0, output_summary: "Missing required features" },
    ],
  },
];

const DEMO_HITL: HITLReviewItem[] = [
  {
    id: "hitl-001",
    trace_id: "trc-1234abcd5678",
    agent_name: "TreatmentRecommender",
    patient_id: "PT-00091",
    action: "Prescribe Metformin 500mg BID for newly diagnosed T2DM",
    confidence: 0.65,
    reason: "Confidence below 0.80 threshold for autonomous prescribing",
    context: { diagnosis: "Type 2 Diabetes Mellitus", hba1c: 7.8 },
    status: "pending",
    created_at: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: "hitl-002",
    trace_id: "trc-aabb1122ccdd",
    agent_name: "DiagnosisAssist",
    patient_id: "PT-00203",
    action: "Add differential diagnosis: Pulmonary Embolism",
    confidence: 0.58,
    reason: "High-risk differential requires physician confirmation",
    context: { symptoms: ["dyspnea", "chest pain", "tachycardia"], wells_score: 5 },
    status: "pending",
    created_at: new Date(Date.now() - 1200000).toISOString(),
  },
  {
    id: "hitl-003",
    trace_id: "trc-eeff3344gghh",
    agent_name: "AlertPrioritizer",
    patient_id: "PT-00378",
    action: "Escalate to critical: Troponin trend rising over 3 draws",
    confidence: 0.72,
    reason: "Escalation to critical priority requires human review per policy",
    context: { troponin_values: [0.04, 0.12, 0.28], trend: "rising" },
    status: "pending",
    created_at: new Date(Date.now() - 1800000).toISOString(),
  },
];

const DEMO_AUDIT = [
  { id: "aud-001", timestamp: new Date(Date.now() - 60000).toISOString(), agent: "VitalIngestion", action: "Ingested 12 vital readings", patient_id: "PT-00142", confidence: 0.99, policy_check: "pass", trace_id: "trc-a1b2c3d4e5f6" },
  { id: "aud-002", timestamp: new Date(Date.now() - 120000).toISOString(), agent: "AnomalyDetector", action: "Detected HR anomaly", patient_id: "PT-00142", confidence: 0.94, policy_check: "pass", trace_id: "trc-a1b2c3d4e5f6" },
  { id: "aud-003", timestamp: new Date(Date.now() - 180000).toISOString(), agent: "ClinicalReasoner", action: "Assessment: elevated HR pattern", patient_id: "PT-00142", confidence: 0.87, policy_check: "pass", trace_id: "trc-a1b2c3d4e5f6" },
  { id: "aud-004", timestamp: new Date(Date.now() - 300000).toISOString(), agent: "TreatmentRecommender", action: "Halted — HITL required for prescribing", patient_id: "PT-00091", confidence: 0.65, policy_check: "review", trace_id: "trc-1234abcd5678" },
  { id: "aud-005", timestamp: new Date(Date.now() - 600000).toISOString(), agent: "DiagnosisAssist", action: "Proposed differential: PE", patient_id: "PT-00203", confidence: 0.58, policy_check: "review", trace_id: "trc-aabb1122ccdd" },
  { id: "aud-006", timestamp: new Date(Date.now() - 900000).toISOString(), agent: "RiskScorer", action: "Risk assessment failed — missing features", patient_id: "PT-00415", confidence: 0.0, policy_check: "fail", trace_id: "trc-9876fedc5432" },
  { id: "aud-007", timestamp: new Date(Date.now() - 1200000).toISOString(), agent: "PolicyGuard", action: "Governance check passed", patient_id: "PT-00142", confidence: 0.98, policy_check: "pass", trace_id: "trc-a1b2c3d4e5f6" },
  { id: "aud-008", timestamp: new Date(Date.now() - 1800000).toISOString(), agent: "AlertPrioritizer", action: "Escalation pending review", patient_id: "PT-00378", confidence: 0.72, policy_check: "review", trace_id: "trc-eeff3344gghh" },
];

// ── Tier config ──────────────────────────────────────────────────────────────

const TIER_CONFIG: Record<string, { label: string; color: string; bg: string; text: string; ring: string; dot: string; gradient: string }> = {
  sensing:       { label: "Sensing",       color: "blue",    bg: "bg-blue-50",    text: "text-blue-700",    ring: "ring-blue-500/20",    dot: "bg-blue-500",    gradient: "from-blue-400 to-blue-600" },
  reasoning:     { label: "Reasoning",     color: "purple",  bg: "bg-purple-50",  text: "text-purple-700",  ring: "ring-purple-500/20",  dot: "bg-purple-500",  gradient: "from-purple-400 to-purple-600" },
  decision:      { label: "Decision",      color: "amber",   bg: "bg-amber-50",   text: "text-amber-700",   ring: "ring-amber-500/20",   dot: "bg-amber-500",   gradient: "from-amber-400 to-amber-600" },
  orchestration: { label: "Orchestration", color: "emerald", bg: "bg-emerald-50", text: "text-emerald-700", ring: "ring-emerald-500/20", dot: "bg-emerald-500", gradient: "from-emerald-400 to-emerald-600" },
};

function getTierConfig(tier: string) {
  const t = tier.toLowerCase();
  if (t in TIER_CONFIG) return TIER_CONFIG[t];
  if (t.includes("sens") || t === "ingestion" || t === "normalization") return TIER_CONFIG.sensing;
  if (t.includes("reason") || t === "interpretation" || t === "analysis") return TIER_CONFIG.reasoning;
  if (t.includes("decis") || t === "scoring" || t === "action") return TIER_CONFIG.decision;
  if (t.includes("orch") || t === "governance" || t === "audit") return TIER_CONFIG.orchestration;
  return TIER_CONFIG.sensing;
}

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

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function truncateId(id: string, len = 12): string {
  return id.length > len ? id.slice(0, len) + "..." : id;
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

// ── Sub-components ───────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { classes: string; label: string; pulse?: boolean }> = {
    running:   { classes: "bg-blue-50 text-blue-700 ring-blue-500/20",     label: "Running",   pulse: true },
    completed: { classes: "bg-emerald-50 text-emerald-700 ring-emerald-500/20", label: "Completed" },
    failed:    { classes: "bg-red-50 text-red-700 ring-red-500/20",        label: "Failed" },
    halted:    { classes: "bg-yellow-50 text-yellow-700 ring-yellow-500/20", label: "Halted" },
    pending:   { classes: "bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 ring-gray-500/20",     label: "Pending" },
  };
  const c = config[status] || config.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase ring-1 ring-inset ${c.classes}`}>
      {c.pulse && <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" /><span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" /></span>}
      {!c.pulse && status === "completed" && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />}
      {!c.pulse && status === "failed" && <span className="h-1.5 w-1.5 rounded-full bg-red-500" />}
      {!c.pulse && status === "halted" && <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />}
      {c.label}
    </span>
  );
}

function ConfidenceBar({ value, size = "md" }: { value: number; size?: "sm" | "md" }) {
  const pct = Math.round(value * 100);
  const color = pct >= 90 ? "bg-emerald-500" : pct >= 70 ? "bg-amber-500" : "bg-red-500";
  const h = size === "sm" ? "h-1.5" : "h-2";
  return (
    <div className="flex items-center gap-2">
      <div className={`flex-1 rounded-full bg-gray-100 dark:bg-gray-800 ${h}`}>
        <div className={`${h} rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-semibold tabular-nums ${pct >= 90 ? "text-emerald-600" : pct >= 70 ? "text-amber-600" : "text-red-600"}`}>{pct}%</span>
    </div>
  );
}

function AgentPipelineViz({ agents }: { agents: PipelineExecution["agents"] }) {
  return (
    <div className="mt-3 flex items-start gap-0 overflow-x-auto pb-2">
      {agents.map((agent, idx) => {
        const tc = getTierConfig(agent.tier);
        const stepStatusColor: Record<string, string> = {
          completed: "bg-emerald-500",
          running: "bg-blue-500",
          failed: "bg-red-500",
          halted: "bg-yellow-500",
          pending: "bg-gray-300",
        };
        const stepBorderColor: Record<string, string> = {
          completed: "border-emerald-500",
          running: "border-blue-500",
          failed: "border-red-500",
          halted: "border-yellow-500",
          pending: "border-gray-300 dark:border-gray-600",
        };
        const isActive = agent.status === "running";
        const dotColor = stepStatusColor[agent.status] || "bg-gray-300";
        const borderColor = stepBorderColor[agent.status] || "border-gray-300 dark:border-gray-600";

        return (
          <div key={agent.name} className="flex items-start">
            {/* Connector line */}
            {idx > 0 && (
              <div className="flex flex-col items-center justify-center pt-5 -mx-px">
                <div className={`h-0.5 w-6 ${agents[idx - 1].status === "completed" ? "bg-emerald-400" : "bg-gray-200"}`} />
              </div>
            )}
            {/* Agent step */}
            <div className="flex flex-col items-center group">
              <div
                className={`relative flex flex-col items-center justify-center rounded-xl border-2 ${borderColor} bg-white dark:bg-gray-900 px-3 py-2 min-w-[100px] transition-all duration-200 hover:shadow-md ${isActive ? "shadow-blue-100 shadow-md" : ""}`}
              >
                {isActive && (
                  <div className="absolute -top-1 -right-1">
                    <span className="relative flex h-3 w-3">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                      <span className="relative inline-flex h-3 w-3 rounded-full bg-blue-500" />
                    </span>
                  </div>
                )}
                <div className={`flex items-center gap-1.5 mb-1`}>
                  <span className={`h-2 w-2 rounded-full ${dotColor} flex-shrink-0`} />
                  <span className="text-[11px] font-bold text-gray-800 dark:text-gray-200 truncate max-w-[80px]">{agent.name}</span>
                </div>
                <span className={`inline-flex rounded-full px-1.5 py-0.5 text-[11px] font-bold uppercase ${tc.bg} ${tc.text} ring-1 ring-inset ${tc.ring}`}>
                  {tc.label}
                </span>
                {agent.status === "completed" && agent.duration_ms > 0 && (
                  <span className="mt-1 text-[11px] text-gray-500 dark:text-gray-400 tabular-nums">{formatDuration(agent.duration_ms)}</span>
                )}
                {agent.confidence != null && agent.status === "completed" && (
                  <div className="mt-1 w-full">
                    <ConfidenceBar value={agent.confidence} size="sm" />
                  </div>
                )}
              </div>
              {agent.output_summary && (
                <span className="mt-1 max-w-[110px] text-center text-[11px] text-gray-500 dark:text-gray-400 leading-tight">{agent.output_summary}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("pipelines");
  const [agents, setAgents] = useState<RegisteredAgent[]>([]);
  const [pipelines, setPipelines] = useState<PipelineExecution[]>([]);
  const [hitlQueue, setHitlQueue] = useState<HITLReviewItem[]>([]);
  const [agentActivity, setAgentActivity] = useState<AgentActivityResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Pipeline trigger form
  const [showTriggerForm, setShowTriggerForm] = useState(false);
  const [triggerEventType, setTriggerEventType] = useState("vital_ingestion");
  const [triggerPatientId, setTriggerPatientId] = useState("");
  const [triggering, setTriggering] = useState(false);

  // HITL resolution
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [resolveNotes, setResolveNotes] = useState<Record<string, string>>({});

  // Audit filters
  const [auditAgentFilter, setAuditAgentFilter] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      fetchAgents().then((data) => {
        const list = Array.isArray(data) ? data : (data as Record<string, unknown>)?.agents;
        if (Array.isArray(list)) setAgents(list as RegisteredAgent[]);
        else setAgents(DEMO_AGENTS);
      }),
      fetchPipelineExecutions({ limit: 20 }).then((data) => {
        if (data?.executions?.length) setPipelines(data.executions);
        else setPipelines(DEMO_PIPELINES);
      }),
      fetchHITLQueue().then((data) => {
        if (data?.items) setHitlQueue(data.items);
        else setHitlQueue(DEMO_HITL);
      }),
      fetchAgentActivity(50).then((data) => {
        setAgentActivity(data);
      }),
    ]);

    // Use demo data on failures
    if (results[0].status === "rejected") setAgents(DEMO_AGENTS);
    if (results[1].status === "rejected") setPipelines(DEMO_PIPELINES);
    if (results[2].status === "rejected") setHitlQueue(DEMO_HITL);

    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // ── Stats ────────────────────────────────────────────────────────────────

  const activePipelines = pipelines.filter((p) => p.status === "running").length;
  const totalAgents = agents.length;
  const hitlPending = hitlQueue.filter((h) => h.status === "pending").length;
  const decisionsToday = pipelines.filter((p) => {
    const d = new Date(p.started_at);
    const now = new Date();
    return d.toDateString() === now.toDateString();
  }).length;
  const avgConfidence = (() => {
    const confs = pipelines.flatMap((p) => p.agents.filter((a) => a.confidence != null).map((a) => a.confidence!));
    return confs.length > 0 ? confs.reduce((s, v) => s + v, 0) / confs.length : 0;
  })();

  // ── Trigger pipeline ────────────────────────────────────────────────────

  async function handleTriggerPipeline() {
    setTriggering(true);
    try {
      await triggerPipeline({
        event_type: triggerEventType,
        patient_id: triggerPatientId || undefined,
      });
      setShowTriggerForm(false);
      setTriggerPatientId("");
      loadData();
    } catch {
      // Demo mode — add a fake running pipeline
      const fakePipeline: PipelineExecution = {
        trace_id: `trc-${Math.random().toString(36).slice(2, 14)}`,
        status: "running",
        trigger_event: triggerEventType,
        patient_id: triggerPatientId || undefined,
        started_at: new Date().toISOString(),
        hitl_required: false,
        agents: [
          { name: "VitalIngestion", tier: "sensing", status: "running", duration_ms: 0 },
          { name: "ClinicalReasoner", tier: "reasoning", status: "pending", duration_ms: 0 },
          { name: "RiskScorer", tier: "decision", status: "pending", duration_ms: 0 },
        ],
      };
      setPipelines((prev) => [fakePipeline, ...prev]);
      setShowTriggerForm(false);
      setTriggerPatientId("");
    }
    setTriggering(false);
  }

  // ── HITL resolution ─────────────────────────────────────────────────────

  async function handleResolveHITL(itemId: string, action: "approve" | "reject") {
    setResolvingId(itemId);
    try {
      await resolveHITLItem(itemId, { action, notes: resolveNotes[itemId] || undefined });
      setHitlQueue((prev) => prev.map((h) => (h.id === itemId ? { ...h, status: action === "approve" ? "approved" : "rejected" } : h)));
    } catch {
      // Demo mode
      setHitlQueue((prev) => prev.map((h) => (h.id === itemId ? { ...h, status: action === "approve" ? "approved" : "rejected" } : h)));
    }
    setResolvingId(null);
  }

  // ── Agent registry grouping ─────────────────────────────────────────────

  const agentsByTier = (() => {
    const groups: Record<string, RegisteredAgent[]> = { sensing: [], reasoning: [], decision: [], orchestration: [] };
    for (const a of agents) {
      const tc = getTierConfig(a.tier);
      const key = Object.keys(TIER_CONFIG).find((k) => TIER_CONFIG[k] === tc) || "sensing";
      if (!groups[key]) groups[key] = [];
      groups[key].push(a);
    }
    return groups;
  })();

  // ── Audit data ──────────────────────────────────────────────────────────

  const auditEntries = DEMO_AUDIT.filter((e) => !auditAgentFilter || e.agent === auditAgentFilter);
  const uniqueAuditAgents = [...new Set(DEMO_AUDIT.map((e) => e.agent))];

  // ── Tabs ────────────────────────────────────────────────────────────────

  const tabs: { key: TabKey; label: string; icon: string; count?: number }[] = [
    { key: "pipelines", label: "Pipeline Monitor", icon: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" },
    { key: "registry", label: "Agent Registry", icon: "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" },
    { key: "hitl", label: "HITL Queue", icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z", count: hitlPending },
    { key: "audit", label: "Audit Trail", icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" },
  ];

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">AI Agent Orchestration</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Monitor pipelines, agent executions, and human-in-the-loop reviews</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 ring-1 ring-inset ring-emerald-500/20">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-xs font-semibold text-emerald-700">Live</span>
          </div>
          <button
            onClick={loadData}
            className="rounded-lg bg-white dark:bg-gray-900 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 shadow-sm ring-1 ring-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <svg className="inline h-3.5 w-3.5 mr-1 -mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* ── Stats Bar ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 animate-fade-in-up" style={{ animationDelay: "0.05s", animationFillMode: "both" }}>
        {[
          { label: "Active Pipelines", value: activePipelines, icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z", color: "blue", pulse: activePipelines > 0 },
          { label: "Total Agents", value: totalAgents, icon: "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z", color: "healthos" },
          { label: "HITL Pending", value: hitlPending, icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z", color: "amber", pulse: hitlPending > 0 },
          { label: "Decisions Today", value: decisionsToday, icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z", color: "emerald" },
          { label: "Avg Confidence", value: `${Math.round(avgConfidence * 100)}%`, icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z", color: "purple" },
        ].map((stat, i) => {
          const colorMap: Record<string, { bg: string; text: string; ring: string }> = {
            blue:     { bg: "bg-blue-50",     text: "text-blue-600",     ring: "ring-blue-500/20" },
            healthos: { bg: "bg-healthos-50", text: "text-healthos-600", ring: "ring-healthos-500/20" },
            amber:    { bg: "bg-amber-50",    text: "text-amber-600",    ring: "ring-amber-500/20" },
            emerald:  { bg: "bg-emerald-50",  text: "text-emerald-600",  ring: "ring-emerald-500/20" },
            purple:   { bg: "bg-purple-50",   text: "text-purple-600",   ring: "ring-purple-500/20" },
          };
          const c = colorMap[stat.color] || colorMap.healthos;
          return (
            <div key={stat.label} className="card card-hover relative overflow-hidden" style={{ animationDelay: `${i * 0.04}s` }}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{stat.label}</p>
                  <p className="mt-1.5 text-2xl font-bold tabular-nums text-gray-900 dark:text-gray-100">{stat.value}</p>
                </div>
                <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${c.bg} ring-1 ring-inset ${c.ring}`}>
                  {stat.pulse && (
                    <span className="absolute top-2 right-2 flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500" />
                    </span>
                  )}
                  <svg className={`h-4.5 w-4.5 ${c.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={stat.icon} />
                  </svg>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200 dark:border-gray-700 animate-fade-in-up" style={{ animationDelay: "0.1s", animationFillMode: "both" }}>
        <nav className="-mb-px flex gap-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`group flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-healthos-500 text-healthos-700"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              <svg className={`h-4 w-4 ${activeTab === tab.key ? "text-healthos-500" : "text-gray-500 dark:text-gray-400 group-hover:text-gray-500 dark:text-gray-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={tab.icon} />
              </svg>
              {tab.label}
              {tab.count != null && tab.count > 0 && (
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                  activeTab === tab.key ? "bg-healthos-100 text-healthos-700" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab Content ────────────────────────────────────────────────────── */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.15s", animationFillMode: "both" }}>

        {/* ── Pipeline Monitor ──────────────────────────────────────────── */}
        {activeTab === "pipelines" && (
          <div className="space-y-4">
            {/* Trigger button */}
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Pipeline Executions ({pipelines.length})</h2>
              <button
                onClick={() => setShowTriggerForm(!showTriggerForm)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-healthos-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-healthos-700 transition-colors"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
                Trigger Pipeline
              </button>
            </div>

            {/* Trigger form */}
            {showTriggerForm && (
              <div className="card animate-fade-in-up border-healthos-200 border">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Trigger New Pipeline</h3>
                <div className="flex flex-wrap gap-3 items-end">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Event Type</label>
                    <select
                      value={triggerEventType}
                      onChange={(e) => setTriggerEventType(e.target.value)}
                      className="rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-healthos-500"
                    >
                      <option value="vital_ingestion">Vital Ingestion</option>
                      <option value="lab_result_received">Lab Result Received</option>
                      <option value="treatment_recommendation">Treatment Recommendation</option>
                      <option value="scheduled_risk_assessment">Scheduled Risk Assessment</option>
                      <option value="alert_triage">Alert Triage</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Patient ID (optional)</label>
                    <input
                      type="text"
                      value={triggerPatientId}
                      onChange={(e) => setTriggerPatientId(e.target.value)}
                      placeholder="PT-00XXX"
                      className="rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-healthos-500"
                    />
                  </div>
                  <button
                    onClick={handleTriggerPipeline}
                    disabled={triggering}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                  >
                    {triggering ? "Triggering..." : "Execute"}
                  </button>
                  <button
                    onClick={() => setShowTriggerForm(false)}
                    className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Pipeline list */}
            {loading ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="card animate-pulse">
                    <div className="flex gap-4 items-center">
                      <div className="skeleton-text w-24" />
                      <div className="skeleton-text w-16" />
                      <div className="skeleton-text w-32" />
                    </div>
                    <div className="mt-4 flex gap-4">
                      {Array.from({ length: 4 }).map((_, j) => (
                        <div key={j} className="skeleton h-16 w-24 rounded-xl" />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {pipelines.map((pipeline, idx) => {
                  const totalDuration = pipeline.agents.reduce((s, a) => s + (a.duration_ms || 0), 0);
                  return (
                    <div
                      key={pipeline.trace_id}
                      className="card card-hover animate-fade-in-up"
                      style={{ animationDelay: `${idx * 0.05}s`, animationFillMode: "both" }}
                    >
                      {/* Header row */}
                      <div className="flex flex-wrap items-center gap-3 mb-1">
                        <span className="font-mono text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded px-2 py-0.5 ring-1 ring-inset ring-gray-200">
                          {truncateId(pipeline.trace_id)}
                        </span>
                        <StatusBadge status={pipeline.status} />
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          <span className="font-medium text-gray-700 dark:text-gray-300">{pipeline.trigger_event.replace(/_/g, " ")}</span>
                        </span>
                        {pipeline.patient_id && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-gray-50 dark:bg-gray-800 px-2 py-0.5 text-[11px] font-medium text-gray-600 dark:text-gray-400 ring-1 ring-inset ring-gray-200">
                            <svg className="h-3 w-3 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                            </svg>
                            {pipeline.patient_id}
                          </span>
                        )}
                        {pipeline.hitl_required && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700 ring-1 ring-inset ring-amber-500/20">
                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
                            </svg>
                            HITL Required
                          </span>
                        )}
                        <div className="ml-auto flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                          {totalDuration > 0 && (
                            <span className="tabular-nums">{formatDuration(totalDuration)}</span>
                          )}
                          <span>{timeAgo(pipeline.started_at)}</span>
                        </div>
                      </div>

                      {/* Agent pipeline visualization */}
                      <AgentPipelineViz agents={pipeline.agents} />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── Agent Registry ────────────────────────────────────────────── */}
        {activeTab === "registry" && (
          <div className="space-y-8">
            {(["sensing", "reasoning", "decision", "orchestration"] as const).map((tierKey) => {
              const tc = TIER_CONFIG[tierKey];
              const tierAgents = agentsByTier[tierKey] || [];
              if (tierAgents.length === 0) return null;

              return (
                <div key={tierKey}>
                  {/* Tier header */}
                  <div className="mb-4 flex items-center gap-3">
                    <div className={`h-1 w-8 rounded-full bg-gradient-to-r ${tc.gradient}`} />
                    <h3 className={`text-sm font-bold uppercase tracking-wider ${tc.text}`}>
                      {tc.label} Tier
                    </h3>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${tc.bg} ${tc.text} ring-1 ring-inset ${tc.ring}`}>
                      {tierAgents.length} agent{tierAgents.length !== 1 ? "s" : ""}
                    </span>
                  </div>

                  {/* Agent cards grid */}
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {tierAgents.map((agent, idx) => {
                      const agentStatus = agentActivity?.agent_statuses?.[agent.name] || "idle";
                      const isActive = agentStatus === "active" || agentStatus === "running";

                      return (
                        <div
                          key={agent.name}
                          className="card card-hover relative overflow-hidden animate-fade-in-up"
                          style={{ animationDelay: `${idx * 0.05}s`, animationFillMode: "both" }}
                        >
                          {/* Tier gradient bar */}
                          <div className={`absolute left-0 top-0 h-1 w-full bg-gradient-to-r ${tc.gradient}`} />

                          <div className="flex items-start gap-3">
                            {/* Status dot */}
                            <div className="relative mt-1 flex-shrink-0">
                              <span className={`block h-3 w-3 rounded-full ${isActive ? tc.dot : "bg-gray-300"}`} />
                              {isActive && (
                                <span className={`absolute inset-0 h-3 w-3 animate-ping rounded-full ${tc.dot} opacity-40`} />
                              )}
                            </div>

                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">{agent.name}</h4>
                              </div>
                              <div className="mt-1 flex items-center gap-2">
                                <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ${tc.bg} ${tc.text} ring-1 ring-inset ${tc.ring}`}>
                                  {agent.tier}
                                </span>
                                <span className="text-[11px] text-gray-500 dark:text-gray-400">v{agent.version}</span>
                                {agent.requires_hitl && (
                                  <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-50 px-1.5 py-0.5 text-[11px] font-bold text-amber-700 ring-1 ring-inset ring-amber-500/20">
                                    HITL
                                  </span>
                                )}
                              </div>
                              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{agent.description}</p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ── HITL Queue ────────────────────────────────────────────────── */}
        {activeTab === "hitl" && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Pending Human Reviews ({hitlQueue.filter((h) => h.status === "pending").length})
            </h2>

            {hitlQueue.filter((h) => h.status === "pending").length === 0 ? (
              <div className="card flex flex-col items-center justify-center py-8 sm:py-16">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 ring-1 ring-inset ring-emerald-500/20">
                  <svg className="h-8 w-8 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="mt-4 text-sm font-medium text-gray-700 dark:text-gray-300">All clear</p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">No pending human-in-the-loop reviews at this time</p>
              </div>
            ) : (
              <div className="space-y-4">
                {hitlQueue.map((item, idx) => {
                  const isPending = item.status === "pending";
                  const isResolved = item.status === "approved" || item.status === "rejected";

                  return (
                    <div
                      key={item.id}
                      className={`card animate-fade-in-up ${isResolved ? "opacity-60" : ""} ${isPending ? "ring-1 ring-amber-200" : ""}`}
                      style={{ animationDelay: `${idx * 0.05}s`, animationFillMode: "both" }}
                    >
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        {/* Left: details */}
                        <div className="flex-1 min-w-0 space-y-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2.5 py-0.5 text-[11px] font-bold text-purple-700 ring-1 ring-inset ring-purple-500/20">
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                              </svg>
                              {item.agent_name}
                            </span>
                            <span className="inline-flex items-center gap-1 rounded-full bg-gray-50 dark:bg-gray-800 px-2 py-0.5 text-[11px] font-medium text-gray-600 dark:text-gray-400 ring-1 ring-inset ring-gray-200">
                              <svg className="h-3 w-3 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                              </svg>
                              {item.patient_id}
                            </span>
                            {isResolved && (
                              <StatusBadge status={item.status === "approved" ? "completed" : "failed"} />
                            )}
                            <span className="text-[11px] text-gray-500 dark:text-gray-400">{timeAgo(item.created_at)}</span>
                          </div>

                          <div>
                            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{item.action}</p>
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                              <span className="font-medium">Reason:</span> {item.reason}
                            </p>
                          </div>

                          {/* Confidence bar */}
                          <div className="max-w-xs">
                            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">Confidence</p>
                            <ConfidenceBar value={item.confidence} />
                          </div>
                        </div>

                        {/* Right: actions */}
                        {isPending && (
                          <div className="flex flex-col gap-2 lg:min-w-[220px]">
                            <textarea
                              placeholder="Notes (optional)..."
                              value={resolveNotes[item.id] || ""}
                              onChange={(e) => setResolveNotes((prev) => ({ ...prev, [item.id]: e.target.value }))}
                              className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-xs shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-healthos-500 resize-none"
                              rows={2}
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleResolveHITL(item.id, "approve")}
                                disabled={resolvingId === item.id}
                                className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                              >
                                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                </svg>
                                Approve
                              </button>
                              <button
                                onClick={() => handleResolveHITL(item.id, "reject")}
                                disabled={resolvingId === item.id}
                                className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-red-700 disabled:opacity-50 transition-colors"
                              >
                                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                                Reject
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Resolved items */}
            {hitlQueue.filter((h) => h.status !== "pending").length > 0 && (
              <div className="mt-6">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">Recently Resolved</h3>
                <div className="space-y-2">
                  {hitlQueue.filter((h) => h.status !== "pending").map((item) => (
                    <div key={item.id} className="card opacity-60">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{item.agent_name}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">{item.patient_id}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs">{item.action}</span>
                        </div>
                        <StatusBadge status={item.status === "approved" ? "completed" : "failed"} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Audit Trail ───────────────────────────────────────────────── */}
        {activeTab === "audit" && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Audit Trail</h2>
              <div className="ml-auto flex items-center gap-2">
                <select
                  value={auditAgentFilter}
                  onChange={(e) => setAuditAgentFilter(e.target.value)}
                  className="rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-healthos-500"
                >
                  <option value="">All Agents</option>
                  {uniqueAuditAgents.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto">
                <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-gray-100 dark:border-gray-800 bg-gray-50/50">
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Timestamp</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Agent</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Action</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Patient</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Confidence</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Policy Check</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Trace ID</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {auditEntries.map((entry, idx) => {
                      const policyColor: Record<string, string> = {
                        pass: "bg-emerald-50 text-emerald-700 ring-emerald-500/20",
                        review: "bg-amber-50 text-amber-700 ring-amber-500/20",
                        fail: "bg-red-50 text-red-700 ring-red-500/20",
                      };
                      return (
                        <tr
                          key={entry.id}
                          className="hover:bg-gray-50/50 transition-colors animate-fade-in"
                          style={{ animationDelay: `${idx * 0.03}s`, animationFillMode: "both" }}
                        >
                          <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500 dark:text-gray-400 tabular-nums">{formatTimestamp(entry.timestamp)}</td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">{entry.agent}</span>
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400 max-w-xs truncate">{entry.action}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500 dark:text-gray-400 font-mono">{entry.patient_id}</td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <div className="w-20">
                              <ConfidenceBar value={entry.confidence} size="sm" />
                            </div>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ring-1 ring-inset ${policyColor[entry.policy_check] || policyColor.pass}`}>
                              {entry.policy_check}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-gray-500 dark:text-gray-400">{truncateId(entry.trace_id)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
