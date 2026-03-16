"use client";

import { useState, useEffect, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════════════════════ */

type TabKey = "assessment" | "agents" | "llm" | "mcp" | "simulator";

interface ClinicalAssessment {
  success: boolean;
  patient_id: string;
  assessment?: {
    patient_summary?: {
      patient_id: string;
      name: string;
      age: number;
      sex: string;
    };
    findings?: Array<{
      category: string;
      finding: string;
      status: string;
      interpretation: string;
    }>;
    critical_findings?: Array<Record<string, unknown>>;
    diagnoses?: Array<{
      diagnosis: string;
      icd10_code: string;
      confidence: number;
      rationale: string;
      supporting_findings: string[];
    }>;
    treatments?: Array<{
      treatment_type: string;
      description: string;
      cpt_code: string;
      priority: string;
      rationale: string;
    }>;
    icd10_codes?: Array<{ code: string; description: string; confidence: number }>;
    cpt_codes?: Array<{ code: string; description: string }>;
    confidence?: number;
    reasoning?: string[];
    warnings?: string[];
    requires_human_review?: boolean;
    review_reason?: string;
  };
  error?: string;
  llm_provider?: string;
}

interface AgentInfo {
  agent_id: string;
  name: string;
  description: string;
  version: string;
  specialties: string[];
  requires_human_approval: boolean;
}

interface LLMStatus {
  status: string;
  primary_provider?: string;
  available_providers?: string[];
  config?: Record<string, unknown>;
  error?: string;
}

interface MCPServerStatus {
  url: string;
  status: string;
  error?: string;
}

interface SimulatorStatus {
  running: boolean;
  interval?: number;
  devices_count?: number;
  observations_sent?: number;
  alerts_generated?: number;
  errors_count?: number;
  error?: string;
}

/* ═══════════════════════════════════════════════════════════════════════════
   API HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */

const API = "/api/v1/clinical-assessment";

function getAuth(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...getAuth(), ...opts?.headers },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

/* ═══════════════════════════════════════════════════════════════════════════
   DEMO DATA
   ═══════════════════════════════════════════════════════════════════════════ */

const DEMO_PATIENTS = [
  { id: "1", name: "John Williams", mrn: "MRN001", age: 71, sex: "M", conditions: ["Hypertension", "Type 2 Diabetes"] },
  { id: "2", name: "Maria Garcia", mrn: "MRN002", age: 58, sex: "F", conditions: ["Atrial Fibrillation"] },
  { id: "3", name: "Robert Johnson", mrn: "MRN003", age: 65, sex: "M", conditions: ["Heart Failure", "CKD Stage 3"] },
  { id: "4", name: "Emily Davis", mrn: "MRN004", age: 45, sex: "F", conditions: ["Asthma", "Anxiety"] },
];

const DEMO_AGENTS: AgentInfo[] = [
  { agent_id: "supervisor", name: "Clinical Supervisor", description: "Orchestrates multi-agent clinical pipeline", version: "2.0.0", specialties: ["triage", "routing"], requires_human_approval: true },
  { agent_id: "diagnostician", name: "Diagnostician", description: "Differential diagnosis with ICD-10 coding", version: "2.0.0", specialties: ["diagnosis", "ICD-10"], requires_human_approval: true },
  { agent_id: "treatment", name: "Treatment Planner", description: "Evidence-based treatment plans with CPT codes", version: "2.0.0", specialties: ["treatment", "CPT"], requires_human_approval: true },
  { agent_id: "safety", name: "Safety Checker", description: "Drug interactions, allergies, contraindications", version: "2.0.0", specialties: ["safety", "pharmacology"], requires_human_approval: false },
  { agent_id: "coding", name: "Medical Coder", description: "ICD-10 and CPT code validation", version: "2.0.0", specialties: ["coding", "billing"], requires_human_approval: false },
  { agent_id: "cardiology", name: "Cardiology Specialist", description: "Cardiovascular assessment, Framingham risk, GDMT", version: "2.0.0", specialties: ["cardiology", "echocardiography"], requires_human_approval: true },
];

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */

const TABS: { key: TabKey; label: string }[] = [
  { key: "assessment", label: "Clinical Assessment" },
  { key: "agents", label: "Specialist Agents" },
  { key: "llm", label: "LLM Configuration" },
  { key: "mcp", label: "MCP Servers" },
  { key: "simulator", label: "IoT Simulator" },
];

export default function ClinicalAssessmentPage() {
  const [tab, setTab] = useState<TabKey>("assessment");
  const [selectedPatient, setSelectedPatient] = useState(DEMO_PATIENTS[0]);
  const [assessment, setAssessment] = useState<ClinicalAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Agent state
  const [agents, setAgents] = useState<AgentInfo[]>(DEMO_AGENTS);

  // LLM state
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);

  // MCP state
  const [mcpServers, setMcpServers] = useState<Record<string, MCPServerStatus>>({});

  // Simulator state
  const [simStatus, setSimStatus] = useState<SimulatorStatus | null>(null);

  const runAssessment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<ClinicalAssessment>("/assess", {
        method: "POST",
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          include_diagnoses: true,
          include_treatments: true,
          include_codes: true,
        }),
      });
      setAssessment(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assessment failed");
    } finally {
      setLoading(false);
    }
  }, [selectedPatient]);

  const loadAgents = useCallback(async () => {
    try {
      const data = await apiFetch<{ agents: AgentInfo[] }>("/agents");
      if (data.agents?.length) setAgents(data.agents);
    } catch {
      /* use demo data */
    }
  }, []);

  const loadLLMStatus = useCallback(async () => {
    try {
      const data = await apiFetch<LLMStatus>("/llm/status");
      setLlmStatus(data);
    } catch {
      setLlmStatus({ status: "unavailable", error: "Orchestrator not reachable" });
    }
  }, []);

  const loadMCPStatus = useCallback(async () => {
    try {
      const data = await apiFetch<{ mcp_servers: Record<string, MCPServerStatus> }>("/mcp/status");
      setMcpServers(data.mcp_servers || {});
    } catch {
      /* empty */
    }
  }, []);

  const loadSimStatus = useCallback(async () => {
    try {
      const data = await apiFetch<SimulatorStatus>("/simulator/status");
      setSimStatus(data);
    } catch {
      setSimStatus({ running: false, error: "Simulator not reachable" });
    }
  }, []);

  useEffect(() => {
    if (tab === "agents") loadAgents();
    if (tab === "llm") loadLLMStatus();
    if (tab === "mcp") loadMCPStatus();
    if (tab === "simulator") loadSimStatus();
  }, [tab, loadAgents, loadLLMStatus, loadMCPStatus, loadSimStatus]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Clinical Decision Support
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          AI-powered multi-agent clinical assessment with specialist agents, LLM orchestration, and FHIR integration
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-6">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`whitespace-nowrap border-b-2 pb-3 pt-1 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "border-healthos-500 text-healthos-600 dark:text-healthos-400"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {tab === "assessment" && (
        <AssessmentTab
          patients={DEMO_PATIENTS}
          selectedPatient={selectedPatient}
          onSelectPatient={setSelectedPatient}
          assessment={assessment}
          loading={loading}
          error={error}
          onRunAssessment={runAssessment}
        />
      )}
      {tab === "agents" && <AgentsTab agents={agents} />}
      {tab === "llm" && <LLMTab status={llmStatus} onRefresh={loadLLMStatus} />}
      {tab === "mcp" && <MCPTab servers={mcpServers} onRefresh={loadMCPStatus} />}
      {tab === "simulator" && <SimulatorTab status={simStatus} onRefresh={loadSimStatus} />}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   ASSESSMENT TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function AssessmentTab({
  patients,
  selectedPatient,
  onSelectPatient,
  assessment,
  loading,
  error,
  onRunAssessment,
}: {
  patients: typeof DEMO_PATIENTS;
  selectedPatient: (typeof DEMO_PATIENTS)[0];
  onSelectPatient: (p: (typeof DEMO_PATIENTS)[0]) => void;
  assessment: ClinicalAssessment | null;
  loading: boolean;
  error: string | null;
  onRunAssessment: () => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Patient Picker */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">Select Patient</h3>
        <div className="space-y-2">
          {patients.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectPatient(p)}
              className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition-all ${
                selectedPatient.id === p.id
                  ? "border-healthos-500 bg-healthos-50 dark:bg-healthos-950/30"
                  : "border-gray-200 hover:border-gray-300 dark:border-gray-600 dark:hover:border-gray-500"
              }`}
            >
              <div className="font-medium text-gray-900 dark:text-gray-100">{p.name}</div>
              <div className="mt-0.5 text-xs text-gray-500">
                {p.mrn} &middot; {p.age}y {p.sex} &middot; {p.conditions.join(", ")}
              </div>
            </button>
          ))}
        </div>

        <button
          onClick={onRunAssessment}
          disabled={loading}
          className="mt-4 w-full rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-healthos-700 disabled:opacity-50"
        >
          {loading ? "Running Assessment..." : "Run AI Clinical Assessment"}
        </button>
      </div>

      {/* Results */}
      <div className="lg:col-span-2 space-y-4">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center rounded-xl border border-gray-200 bg-white p-12 dark:border-gray-700 dark:bg-gray-800">
            <div className="text-center">
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
              <p className="mt-3 text-sm text-gray-500">Running multi-agent clinical assessment...</p>
              <p className="mt-1 text-xs text-gray-400">Supervisor &rarr; Diagnostician &rarr; Treatment &rarr; Safety &rarr; Coding</p>
            </div>
          </div>
        )}

        {assessment?.assessment && !loading && (
          <>
            {/* Confidence & Provider */}
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                (assessment.assessment.confidence ?? 0) >= 0.8
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                  : (assessment.assessment.confidence ?? 0) >= 0.5
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                    : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              }`}>
                Confidence: {((assessment.assessment.confidence ?? 0) * 100).toFixed(0)}%
              </span>
              {assessment.llm_provider && (
                <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                  LLM: {assessment.llm_provider}
                </span>
              )}
              {assessment.assessment.requires_human_review && (
                <span className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  Requires Physician Review
                </span>
              )}
            </div>

            {/* Warnings */}
            {(assessment.assessment.warnings?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/30">
                <h4 className="text-sm font-semibold text-amber-800 dark:text-amber-300">Warnings</h4>
                <ul className="mt-1 list-inside list-disc text-sm text-amber-700 dark:text-amber-400">
                  {assessment.assessment.warnings!.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}

            {/* Diagnoses */}
            {(assessment.assessment.diagnoses?.length ?? 0) > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
                <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Diagnoses</h4>
                <div className="space-y-3">
                  {assessment.assessment.diagnoses!.map((d, i) => (
                    <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 p-4 dark:border-gray-600 dark:bg-gray-700/50">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-900 dark:text-gray-100">{d.diagnosis}</span>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-mono text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                            {d.icd10_code}
                          </span>
                          <span className="text-xs text-gray-500">{(d.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{d.rationale}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Treatments */}
            {(assessment.assessment.treatments?.length ?? 0) > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
                <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Treatment Recommendations</h4>
                <div className="space-y-2">
                  {assessment.assessment.treatments!.map((t, i) => (
                    <div key={i} className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-600 dark:bg-gray-700/50">
                      <span className={`mt-0.5 inline-flex rounded px-2 py-0.5 text-xs font-semibold ${
                        t.priority === "immediate" || t.priority === "urgent"
                          ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                          : "bg-gray-100 text-gray-600 dark:bg-gray-600 dark:text-gray-300"
                      }`}>
                        {t.priority}
                      </span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{t.description}</span>
                          {t.cpt_code && (
                            <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs font-mono text-green-700 dark:bg-green-900/30 dark:text-green-400">
                              CPT {t.cpt_code}
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{t.rationale}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reasoning Chain */}
            {(assessment.assessment.reasoning?.length ?? 0) > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
                <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Reasoning Chain</h4>
                <ol className="list-inside list-decimal space-y-1 text-sm text-gray-600 dark:text-gray-300">
                  {assessment.assessment.reasoning!.map((r, i) => <li key={i}>{r}</li>)}
                </ol>
              </div>
            )}
          </>
        )}

        {!assessment && !loading && !error && (
          <div className="flex items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 p-16 dark:border-gray-600 dark:bg-gray-800/50">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <h3 className="mt-3 text-sm font-medium text-gray-900 dark:text-gray-200">No Assessment Yet</h3>
              <p className="mt-1 text-xs text-gray-500">Select a patient and click &ldquo;Run AI Clinical Assessment&rdquo; to begin</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   AGENTS TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function AgentsTab({ agents }: { agents: AgentInfo[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {agents.map((agent) => (
        <div key={agent.agent_id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{agent.name}</h4>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">v{agent.version}</p>
            </div>
            {agent.requires_human_approval && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                HITL
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{agent.description}</p>
          {agent.specialties.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {agent.specialties.map((s) => (
                <span key={s} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   LLM TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function LLMTab({ status, onRefresh }: { status: LLMStatus | null; onRefresh: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">LLM Provider Configuration</h3>
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      {status ? (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Status</p>
              <p className={`mt-1 text-sm font-semibold ${status.status === "available" ? "text-emerald-600" : "text-red-600"}`}>
                {status.status}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Primary Provider</p>
              <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">{status.primary_provider || "N/A"}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Available Providers</p>
              <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{status.available_providers?.join(", ") || "None"}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Model</p>
              <p className="mt-1 text-sm text-gray-700 dark:text-gray-300 truncate">{String(status.config?.claude_model || status.config?.ollama_model || "N/A")}</p>
            </div>
          </div>
          {status.error && (
            <p className="mt-4 text-sm text-red-600 dark:text-red-400">{status.error}</p>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 text-center dark:border-gray-700 dark:bg-gray-800">
          <p className="text-sm text-gray-500">Loading LLM status...</p>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   MCP TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function MCPTab({ servers, onRefresh }: { servers: Record<string, MCPServerStatus>; onRefresh: () => void }) {
  const entries = Object.entries(servers);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">MCP Server Status</h3>
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      {entries.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {entries.map(([name, s]) => (
            <div key={name} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 capitalize">{name.replace(/-/g, " ")}</h4>
                <span className={`inline-flex h-2 w-2 rounded-full ${s.status === "healthy" ? "bg-emerald-500" : "bg-red-500"}`} />
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 font-mono">{s.url}</p>
              <p className={`mt-1 text-xs font-medium ${s.status === "healthy" ? "text-emerald-600" : "text-red-600"}`}>
                {s.status}{s.error ? `: ${s.error}` : ""}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center dark:border-gray-600 dark:bg-gray-800/50">
          <p className="text-sm text-gray-500">No MCP servers connected. Start the clinical orchestrator to see server status.</p>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIMULATOR TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function SimulatorTab({ status, onRefresh }: { status: SimulatorStatus | null; onRefresh: () => void }) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const doAction = async (action: string) => {
    setActionLoading(action);
    try {
      await apiFetch(`/simulator/${action}`, { method: "POST" });
      await new Promise((r) => setTimeout(r, 500));
      onRefresh();
    } catch {
      /* ignore */
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">IoT Device Simulator</h3>
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        {status ? (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Status</p>
                <p className={`mt-1 text-sm font-semibold ${status.running ? "text-emerald-600" : "text-gray-500"}`}>
                  {status.running ? "Running" : "Stopped"}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Interval</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.interval ?? 30}s</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Devices</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.devices_count ?? 0}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Observations Sent</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.observations_sent ?? 0}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Alerts Generated</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.alerts_generated ?? 0}</p>
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={() => doAction(status.running ? "stop" : "start")}
                disabled={!!actionLoading}
                className={`rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all disabled:opacity-50 ${
                  status.running
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-emerald-600 hover:bg-emerald-700"
                }`}
              >
                {actionLoading === "start" || actionLoading === "stop" ? "..." : status.running ? "Stop" : "Start"}
              </button>
              <button
                onClick={() => doAction("trigger")}
                disabled={!!actionLoading}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                {actionLoading === "trigger" ? "..." : "Trigger Once"}
              </button>
              <button
                onClick={() => doAction("reset-stats")}
                disabled={!!actionLoading}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                Reset Stats
              </button>
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-500">Loading simulator status...</p>
        )}

        {status?.error && (
          <p className="mt-4 text-sm text-red-600 dark:text-red-400">{status.error}</p>
        )}
      </div>
    </div>
  );
}
