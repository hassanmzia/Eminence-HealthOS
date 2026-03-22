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
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-500">
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
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
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
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
        <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">Select Patient</h3>
        <div className="space-y-2">
          {patients.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectPatient(p)}
              className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition-all ${
                selectedPatient.id === p.id
                  ? "border-healthos-500 bg-healthos-50 dark:bg-healthos-950/30"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-500"
              }`}
            >
              <div className="font-medium text-gray-900 dark:text-gray-100">{p.name}</div>
              <div className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
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
          <div className="flex items-center justify-center rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 sm:p-12 dark:bg-gray-800">
            <div className="text-center">
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
              <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Running multi-agent clinical assessment...</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Supervisor &rarr; Diagnostician &rarr; Treatment &rarr; Safety &rarr; Coding</p>
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
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
                <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Diagnoses</h4>
                <div className="space-y-3">
                  {assessment.assessment.diagnoses!.map((d, i) => (
                    <div key={i} className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4 dark:border-gray-600 dark:bg-gray-700/50">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-900 dark:text-gray-100">{d.diagnosis}</span>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-mono text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                            {d.icd10_code}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">{(d.confidence * 100).toFixed(0)}%</span>
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
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
                <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Treatment Recommendations</h4>
                <div className="space-y-2">
                  {assessment.assessment.treatments!.map((t, i) => (
                    <div key={i} className="flex items-start gap-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-3 dark:border-gray-600 dark:bg-gray-700/50">
                      <span className={`mt-0.5 inline-flex rounded px-2 py-0.5 text-xs font-semibold ${
                        t.priority === "immediate" || t.priority === "urgent"
                          ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                          : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 dark:bg-gray-600 dark:text-gray-300"
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
                        <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-500">{t.rationale}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reasoning Chain */}
            {(assessment.assessment.reasoning?.length ?? 0) > 0 && (
              <ReasoningChain steps={assessment.assessment.reasoning!} />
            )}
          </>
        )}

        {!assessment && !loading && !error && (
          <div className="flex items-center justify-center rounded-xl border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 p-6 sm:p-16">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <h3 className="mt-3 text-sm font-medium text-gray-900 dark:text-gray-200">No Assessment Yet</h3>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Select a patient and click &ldquo;Run AI Clinical Assessment&rdquo; to begin</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   REASONING CHAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */

const STEP_ICONS: Record<string, { icon: string; gradient: string }> = {
  "Triage Assessment":       { icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z", gradient: "from-amber-400 to-orange-500" },
  "Diagnostic Analysis":     { icon: "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z", gradient: "from-blue-400 to-indigo-500" },
  "Treatment Planning":      { icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5", gradient: "from-emerald-400 to-teal-500" },
  "Safety Validation":       { icon: "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z", gradient: "from-red-400 to-rose-500" },
  "Clinical Coding":         { icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5", gradient: "from-violet-400 to-purple-500" },
  "Validation & Aggregation":{ icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75", gradient: "from-cyan-400 to-blue-500" },
  "Quality Check":           { icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z", gradient: "from-emerald-400 to-green-500" },
};

const AGENT_COLORS: Record<string, string> = {
  Diagnostician: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Treatment: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  Safety: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  Coding: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
};

interface ReasoningSection {
  stepNum: string;
  title: string;
  lines: string[];
}

function parseReasoningSteps(steps: string[]): ReasoningSection[] {
  const sections: ReasoningSection[] = [];
  let current: ReasoningSection | null = null;

  for (const step of steps) {
    const headerMatch = step.match(/^=== Step (\d+): (.+?) ===$/);
    if (headerMatch) {
      if (current) sections.push(current);
      current = { stepNum: headerMatch[1], title: headerMatch[2], lines: [] };
    } else if (current) {
      current.lines.push(step);
    } else {
      // Line before any section header
      if (!sections.length) {
        current = { stepNum: "0", title: "Overview", lines: [step] };
      }
    }
  }
  if (current) sections.push(current);
  return sections;
}

function ReasoningLine({ line }: { line: string }) {
  // Agent step: [AgentName] Step N: Description
  const agentMatch = line.match(/^\[(\w+)\]\s+Step\s+\d+:\s+(.+)$/);
  if (agentMatch) {
    const agentName = agentMatch[1];
    const desc = agentMatch[2];
    const colorCls = AGENT_COLORS[agentName] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
    return (
      <div className="flex items-start gap-2.5 py-1">
        <span className={`mt-0.5 inline-flex shrink-0 items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${colorCls}`}>
          {agentName}
        </span>
        <span className="text-sm text-gray-600 dark:text-gray-300">{desc}</span>
      </div>
    );
  }

  // QC lines: QC PASS / QC FAIL / QC WARN / QC SKIP
  const qcMatch = line.match(/^QC\s+(PASS|FAIL|WARN|SKIP):\s+(.+)$/);
  if (qcMatch) {
    const type = qcMatch[1];
    const msg = qcMatch[2];
    const config: Record<string, { icon: string; cls: string; iconCls: string }> = {
      PASS: { icon: "M4.5 12.75l6 6 9-13.5", cls: "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/40", iconCls: "text-emerald-500" },
      FAIL: { icon: "M6 18L18 6M6 6l12 12", cls: "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/40", iconCls: "text-red-500" },
      WARN: { icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z", cls: "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40", iconCls: "text-amber-500" },
      SKIP: { icon: "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12", cls: "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800", iconCls: "text-gray-400" },
    };
    const c = config[type] || config.SKIP;
    return (
      <div className={`flex items-start gap-2.5 rounded-lg border p-2.5 ${c.cls}`}>
        <svg className={`mt-0.5 h-4 w-4 shrink-0 ${c.iconCls}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d={c.icon} />
        </svg>
        <div>
          <span className={`text-xs font-bold uppercase tracking-wide ${c.iconCls}`}>{type}</span>
          <p className="text-sm text-gray-700 dark:text-gray-300">{msg}</p>
        </div>
      </div>
    );
  }

  // Human review REQUIRED line
  if (line.startsWith("Human review REQUIRED:")) {
    return (
      <div className="flex items-start gap-2.5 rounded-lg border border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50 p-3 dark:border-amber-700 dark:from-amber-950/40 dark:to-orange-950/30">
        <svg className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
        <div>
          <span className="text-xs font-bold uppercase tracking-wide text-amber-600 dark:text-amber-400">Physician Review Required</span>
          <p className="text-sm font-medium text-amber-800 dark:text-amber-300">{line.replace("Human review REQUIRED: ", "")}</p>
        </div>
      </div>
    );
  }

  // Agents consulted line
  if (line.startsWith("Agents consulted:")) {
    const agentList = line.replace("Agents consulted: ", "").split(", ");
    return (
      <div className="flex flex-wrap items-center gap-2 py-1">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Agents consulted:</span>
        {agentList.map((a) => {
          const colorCls = AGENT_COLORS[a.charAt(0).toUpperCase() + a.slice(1)] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
          return (
            <span key={a} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold capitalize ${colorCls}`}>
              {a}
            </span>
          );
        })}
      </div>
    );
  }

  // Summary stats lines (Total findings, Treatment plan, Clinical codes, etc.)
  const statsMatch = line.match(/^(Total findings|No diagnoses|Treatment plan|Clinical codes|Overall diagnostic confidence|Quality check complete)[:].+$/);
  if (statsMatch) {
    // Parse key:value
    const colonIdx = line.indexOf(":");
    const label = line.slice(0, colonIdx);
    const value = line.slice(colonIdx + 1).trim();

    const isWarning = line.includes("0%") || line.includes("No diagnoses") || line.includes("0 recommendation");
    return (
      <div className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-800/60">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
        <span className={`text-sm font-semibold tabular-nums ${isWarning ? "text-amber-600 dark:text-amber-400" : "text-gray-900 dark:text-gray-100"}`}>
          {value}
        </span>
      </div>
    );
  }

  // Key: value pattern (e.g. "Urgency level: unknown")
  const kvMatch = line.match(/^(.+?):\s+(.+)$/);
  if (kvMatch) {
    return (
      <div className="flex items-center justify-between py-1">
        <span className="text-sm text-gray-500 dark:text-gray-400">{kvMatch[1]}</span>
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{kvMatch[2]}</span>
      </div>
    );
  }

  // Default fallback
  return <p className="py-0.5 text-sm text-gray-600 dark:text-gray-300">{line}</p>;
}

function ReasoningChain({ steps }: { steps: string[] }) {
  const sections = parseReasoningSteps(steps);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(sections.map((s) => s.stepNum)));

  const toggleSection = (stepNum: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(stepNum)) next.delete(stepNum);
      else next.add(stepNum);
      return next;
    });
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-healthos-400 to-healthos-600">
            <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">AI Reasoning Chain</h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">{sections.length} pipeline stages completed</p>
          </div>
        </div>
        <span className="rounded-full bg-healthos-50 px-2.5 py-1 text-[11px] font-bold text-healthos-700 ring-1 ring-inset ring-healthos-500/20 dark:bg-healthos-950/50 dark:text-healthos-400 dark:ring-healthos-500/30">
          {steps.length} steps
        </span>
      </div>

      <div className="relative space-y-3">
        {/* Vertical timeline line */}
        <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-gradient-to-b from-healthos-200 via-gray-200 to-gray-100 dark:from-healthos-800 dark:via-gray-700 dark:to-gray-800" />

        {sections.map((section, idx) => {
          const stepConfig = STEP_ICONS[section.title] || { icon: "M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25", gradient: "from-gray-400 to-gray-500" };
          const isExpanded = expandedSections.has(section.stepNum);
          const isLast = idx === sections.length - 1;

          return (
            <div key={section.stepNum} className="relative pl-10">
              {/* Timeline dot */}
              <div className={`absolute left-0 top-0 flex h-[30px] w-[30px] items-center justify-center rounded-full bg-gradient-to-br ${stepConfig.gradient} shadow-sm ring-4 ring-white dark:ring-gray-900`}>
                <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={stepConfig.icon} />
                </svg>
              </div>

              {/* Section card */}
              <div className={`rounded-lg border transition-all ${isExpanded ? "border-gray-200 bg-gray-50/50 dark:border-gray-700 dark:bg-gray-800/50" : "border-transparent hover:border-gray-100 dark:hover:border-gray-800"}`}>
                <button
                  onClick={() => toggleSection(section.stepNum)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold text-gray-400 dark:text-gray-500 tabular-nums">
                      {String(section.stepNum).padStart(2, "0")}
                    </span>
                    <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {section.title}
                    </span>
                    {section.lines.length > 0 && (
                      <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                        {section.lines.length}
                      </span>
                    )}
                  </div>
                  <svg
                    className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </button>

                {isExpanded && section.lines.length > 0 && (
                  <div className="space-y-1.5 px-3 pb-3">
                    <div className="h-px bg-gray-200 dark:bg-gray-700" />
                    {section.lines.map((line, i) => (
                      <ReasoningLine key={i} line={line} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
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
        <div key={agent.agent_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{agent.name}</h4>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-500">v{agent.version}</p>
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
                <span key={s} className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-500">
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
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 dark:text-gray-500 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      {status ? (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 shadow-sm dark:bg-gray-800">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Status</p>
              <p className={`mt-1 text-sm font-semibold ${status.status === "available" ? "text-emerald-600" : "text-red-600"}`}>
                {status.status}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Primary Provider</p>
              <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">{status.primary_provider || "N/A"}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Available Providers</p>
              <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{status.available_providers?.join(", ") || "None"}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Model</p>
              <p className="mt-1 text-sm text-gray-700 dark:text-gray-300 truncate">{String(status.config?.claude_model || status.config?.ollama_model || "N/A")}</p>
            </div>
          </div>
          {status.error && (
            <p className="mt-4 text-sm text-red-600 dark:text-red-400">{status.error}</p>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4 sm:p-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading LLM status...</p>
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
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 dark:text-gray-500 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      {entries.length > 0 ? (
        <>
          {entries.every(([, s]) => s.status === "unreachable") && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              All MCP servers are unreachable. Start the services with <code className="rounded bg-amber-100 px-1 py-0.5 dark:bg-amber-800">docker-compose up</code> or run them locally on the configured ports.
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {entries.map(([name, s]) => {
              const dotColor = s.status === "healthy" ? "bg-emerald-500" : s.status === "unreachable" ? "bg-amber-400" : "bg-red-500";
              const textColor = s.status === "healthy" ? "text-emerald-600" : s.status === "unreachable" ? "text-amber-600" : "text-red-600";
              return (
                <div key={name} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 capitalize">{name.replace(/-/g, " ")}</h4>
                    <span className={`inline-flex h-2 w-2 rounded-full ${dotColor}`} />
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-500 font-mono">{s.url}</p>
                  <p className={`mt-1 text-xs font-medium ${textColor}`}>
                    {s.status}{s.error ? `: ${s.error}` : ""}
                  </p>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 p-4 sm:p-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">No MCP servers connected. Start the clinical orchestrator to see server status.</p>
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
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 dark:text-gray-500 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 shadow-sm dark:bg-gray-800">
        {status ? (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Status</p>
                <p className={`mt-1 text-sm font-semibold ${status.running ? "text-emerald-600" : "text-gray-500 dark:text-gray-400"}`}>
                  {status.running ? "Running" : "Stopped"}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Interval</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.interval ?? 30}s</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Devices</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.devices_count ?? 0}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Observations Sent</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.observations_sent ?? 0}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Alerts Generated</p>
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
                className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                {actionLoading === "trigger" ? "..." : "Trigger Once"}
              </button>
              <button
                onClick={() => doAction("reset-stats")}
                disabled={!!actionLoading}
                className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                Reset Stats
              </button>
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading simulator status...</p>
        )}

        {status?.error && (
          <p className="mt-4 text-sm text-red-600 dark:text-red-400">{status.error}</p>
        )}
      </div>
    </div>
  );
}
