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
  if (res.status === 401) {
    throw new Error("AUTH_REQUIRED");
  }
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

function buildDemoAssessment(patient: typeof DEMO_PATIENTS[0]): ClinicalAssessment {
  const conditionData: Record<string, { findings: ClinicalAssessment["assessment"] extends { findings?: infer F } ? F : never; diagnoses: ClinicalAssessment["assessment"] extends { diagnoses?: infer D } ? D : never; treatments: ClinicalAssessment["assessment"] extends { treatments?: infer T } ? T : never }> = {
    Hypertension: {
      findings: [
        { category: "Vitals", finding: "Blood pressure 158/94 mmHg", status: "abnormal", interpretation: "Stage 2 hypertension — above target 130/80 for diabetic patients" },
        { category: "Vitals", finding: "Heart rate 82 bpm", status: "normal", interpretation: "Regular rate and rhythm" },
        { category: "Labs", finding: "Serum creatinine 1.4 mg/dL", status: "borderline", interpretation: "Mildly elevated — monitor renal function given hypertension and diabetes" },
        { category: "Labs", finding: "Potassium 4.2 mEq/L", status: "normal", interpretation: "Within normal range" },
      ],
      diagnoses: [
        { diagnosis: "Essential Hypertension, Stage 2", icd10_code: "I10", confidence: 0.95, rationale: "Sustained BP >140/90 on multiple readings with end-organ risk factors", supporting_findings: ["BP 158/94", "Elevated creatinine"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Increase Lisinopril to 20mg daily", cpt_code: "99214", priority: "high", rationale: "Current BP above target on 10mg; ACE inhibitor preferred given concurrent diabetes" },
        { treatment_type: "Lifestyle", description: "DASH diet counseling, sodium restriction <2g/day", cpt_code: "97802", priority: "medium", rationale: "Dietary modification is first-line adjunct for hypertension management" },
      ],
    },
    "Type 2 Diabetes": {
      findings: [
        { category: "Labs", finding: "HbA1c 8.2%", status: "abnormal", interpretation: "Above target of 7.0% — indicates suboptimal glycemic control over past 3 months" },
        { category: "Labs", finding: "Fasting glucose 186 mg/dL", status: "abnormal", interpretation: "Elevated fasting glucose consistent with uncontrolled diabetes" },
        { category: "Labs", finding: "eGFR 58 mL/min", status: "borderline", interpretation: "CKD Stage 3a — consider renal-protective diabetes agents" },
      ],
      diagnoses: [
        { diagnosis: "Type 2 Diabetes Mellitus without complications", icd10_code: "E11.9", confidence: 0.92, rationale: "Elevated HbA1c and fasting glucose with established diabetes history", supporting_findings: ["HbA1c 8.2%", "FG 186 mg/dL"] },
        { diagnosis: "Chronic Kidney Disease, Stage 3a", icd10_code: "N18.31", confidence: 0.88, rationale: "eGFR 58 mL/min with diabetic and hypertensive nephropathy risk", supporting_findings: ["eGFR 58", "Cr 1.4"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Add Empagliflozin 10mg daily", cpt_code: "99214", priority: "high", rationale: "SGLT2 inhibitor provides glycemic control plus renal and cardiovascular protection" },
        { treatment_type: "Monitoring", description: "Repeat HbA1c in 3 months, renal panel in 6 weeks", cpt_code: "83036", priority: "medium", rationale: "Track glycemic response and renal function with new medication" },
      ],
    },
    "Atrial Fibrillation": {
      findings: [
        { category: "ECG", finding: "Irregular rhythm, absent P waves", status: "abnormal", interpretation: "Consistent with atrial fibrillation" },
        { category: "Vitals", finding: "Heart rate 112 bpm (irregular)", status: "abnormal", interpretation: "Rapid ventricular response in atrial fibrillation" },
        { category: "Labs", finding: "TSH 0.8 mIU/L", status: "normal", interpretation: "Thyroid function normal — rules out thyrotoxicosis as AF trigger" },
      ],
      diagnoses: [
        { diagnosis: "Atrial Fibrillation, Unspecified", icd10_code: "I48.91", confidence: 0.96, rationale: "ECG findings with irregular narrow-complex tachycardia and absent P waves", supporting_findings: ["Irregular rhythm", "Absent P waves", "HR 112"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Initiate Metoprolol succinate 50mg daily for rate control", cpt_code: "99214", priority: "high", rationale: "Rate control strategy for AF with rapid ventricular response; target HR <110 at rest" },
        { treatment_type: "Anticoagulation", description: "Start Apixaban 5mg BID (CHA₂DS₂-VASc = 2)", cpt_code: "99214", priority: "high", rationale: "Stroke prevention indicated with CHA₂DS₂-VASc ≥2 in female patient" },
      ],
    },
    "Heart Failure": {
      findings: [
        { category: "Labs", finding: "BNP 820 pg/mL", status: "abnormal", interpretation: "Significantly elevated — consistent with heart failure exacerbation" },
        { category: "Imaging", finding: "Ejection fraction 35%", status: "abnormal", interpretation: "Reduced EF indicating systolic dysfunction (HFrEF)" },
        { category: "Vitals", finding: "SpO2 93% on room air", status: "borderline", interpretation: "Mild hypoxemia — may indicate pulmonary congestion" },
      ],
      diagnoses: [
        { diagnosis: "Heart Failure with Reduced Ejection Fraction", icd10_code: "I50.2", confidence: 0.94, rationale: "EF 35% with elevated BNP and clinical signs of congestion", supporting_findings: ["EF 35%", "BNP 820", "SpO2 93%"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Optimize GDMT: Sacubitril/Valsartan 24/26mg BID", cpt_code: "99214", priority: "high", rationale: "ARNI therapy reduces mortality in HFrEF per ACC/AHA guidelines" },
        { treatment_type: "Medication", description: "Add Spironolactone 25mg daily", cpt_code: "99214", priority: "high", rationale: "MRA reduces mortality in NYHA II-IV HFrEF with EF ≤35%" },
      ],
    },
  };

  const allFindings: NonNullable<ClinicalAssessment["assessment"]>["findings"] = [];
  const allDiagnoses: NonNullable<ClinicalAssessment["assessment"]>["diagnoses"] = [];
  const allTreatments: NonNullable<ClinicalAssessment["assessment"]>["treatments"] = [];

  for (const cond of patient.conditions) {
    const data = conditionData[cond];
    if (data) {
      if (data.findings) allFindings.push(...data.findings);
      if (data.diagnoses) allDiagnoses.push(...data.diagnoses);
      if (data.treatments) allTreatments.push(...data.treatments);
    }
  }

  const reasoning = [
    `=== Step 1: Patient Intake ===`,
    `Agent [Supervisor] reviewing patient ${patient.name} (${patient.age}${patient.sex}, MRN: ${patient.mrn})`,
    `Known conditions: ${patient.conditions.join(", ")}`,
    `Routing to specialist agents for comprehensive assessment...`,
    ``,
    `=== Step 2: Clinical Findings ===`,
    `Agent [Diagnostician] analyzing vitals, labs, and imaging data`,
    `Found ${allFindings.length} relevant findings across ${patient.conditions.length} condition(s)`,
    ...allFindings.filter(f => f.status === "abnormal").map(f => `  ⚠ ${f.finding} — ${f.interpretation}`),
    ``,
    `=== Step 3: Differential Diagnosis ===`,
    `Agent [Diagnostician] generating differential diagnoses with ICD-10 codes`,
    ...allDiagnoses.map(d => `  → ${d.diagnosis} (${d.icd10_code}) — confidence ${(d.confidence * 100).toFixed(0)}%`),
    ``,
    `=== Step 4: Treatment Planning ===`,
    `Agent [Treatment Planner] formulating evidence-based treatment plan`,
    ...allTreatments.map(t => `  → [${t.priority.toUpperCase()}] ${t.description}`),
    ``,
    `=== Step 5: Safety Check ===`,
    `Agent [Safety Checker] verifying drug interactions and contraindications`,
    `QC Result: PASS — No critical drug interactions detected`,
    `QC Result: PASS — Allergy screening clear`,
    `QC Result: ${allFindings.some(f => f.status === "abnormal") ? "WARN" : "PASS"} — ${allFindings.filter(f => f.status === "abnormal").length} abnormal finding(s) flagged for review`,
    ``,
    `=== Step 6: Final Review ===`,
    `Agent [Supervisor] compiling final assessment`,
    `Human review: RECOMMENDED — Complex multi-condition patient`,
    `Total agents consulted: 5 | Confidence: ${(allDiagnoses.reduce((s, d) => s + d.confidence, 0) / Math.max(allDiagnoses.length, 1) * 100).toFixed(0)}%`,
  ];

  return {
    success: true,
    patient_id: patient.id,
    llm_provider: "demo-mode",
    assessment: {
      patient_summary: { patient_id: patient.id, name: patient.name, age: patient.age, sex: patient.sex },
      findings: allFindings,
      critical_findings: allFindings.filter(f => f.status === "abnormal").map(f => ({ finding: f.finding, interpretation: f.interpretation })),
      diagnoses: allDiagnoses,
      treatments: allTreatments,
      icd10_codes: allDiagnoses.map(d => ({ code: d.icd10_code, description: d.diagnosis, confidence: d.confidence })),
      cpt_codes: allTreatments.map(t => ({ code: t.cpt_code, description: t.description })),
      confidence: allDiagnoses.reduce((s, d) => s + d.confidence, 0) / Math.max(allDiagnoses.length, 1),
      reasoning,
      warnings: allFindings.filter(f => f.status === "abnormal").map(f => f.finding),
      requires_human_review: true,
      review_reason: "Multi-condition patient with abnormal findings requires clinician verification",
    },
  };
}

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
      const msg = e instanceof Error ? e.message : "Assessment failed";
      if (msg === "AUTH_REQUIRED") {
        // Fall back to demo assessment when not authenticated
        await new Promise((r) => setTimeout(r, 1500)); // simulate processing
        setAssessment(buildDemoAssessment(selectedPatient));
      } else {
        setError(msg);
      }
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
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        setLlmStatus({
          status: "demo",
          primary_provider: "claude-sonnet-4-6 (demo)",
          available_providers: ["claude-sonnet-4-6", "gpt-4o", "gemini-2.0-flash"],
          config: { temperature: 0.2, max_tokens: 4096, top_p: 0.9 },
        });
      } else {
        setLlmStatus({ status: "unavailable", error: "Orchestrator not reachable" });
      }
    }
  }, []);

  const loadMCPStatus = useCallback(async () => {
    try {
      const data = await apiFetch<{ mcp_servers: Record<string, MCPServerStatus> }>("/mcp/status");
      setMcpServers(data.mcp_servers || {});
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        setMcpServers({
          "fhir-server": { url: "http://localhost:8090", status: "demo" },
          "audit-server": { url: "http://localhost:8091", status: "demo" },
          "terminology-server": { url: "http://localhost:8092", status: "demo" },
        });
      }
    }
  }, []);

  const loadSimStatus = useCallback(async () => {
    try {
      const data = await apiFetch<SimulatorStatus>("/simulator/status");
      setSimStatus(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        setSimStatus({ running: false, devices_count: 6, observations_sent: 0, alerts_generated: 0, errors_count: 0 });
      } else {
        setSimStatus({ running: false, error: "Simulator not reachable" });
      }
    }
  }, []);

  const switchProvider = useCallback(async (provider: string) => {
    try {
      await apiFetch("/llm/switch?provider=" + encodeURIComponent(provider), { method: "POST" });
      await loadLLMStatus();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        // In demo mode, simulate switching
        setLlmStatus((prev) => prev ? { ...prev, primary_provider: provider } : prev);
      }
    }
  }, [loadLLMStatus]);

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
      {tab === "llm" && <LLMTab status={llmStatus} onRefresh={loadLLMStatus} onSwitch={switchProvider} />}
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
            <div key={section.stepNum} className="relative pl-10"> {/* Timeline dot */} <div className={`absolute left-0 top-0 flex h-[30px] w-[30px] items-center justify-center rounded-full bg-gradient-to-br ${stepConfig.gradient} shadow-sm ring-4 ring-white dark:ring-gray-900`}> <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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

const LLM_PROVIDERS = [
  {
    id: "claude",
    name: "Anthropic Claude",
    description: "Best-in-class reasoning and clinical safety. Recommended for production clinical assessments.",
    icon: (
      <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none">
        <path d="M16.5 3.5C14 3.5 12 5.5 12 8V16C12 18.5 14 20.5 16.5 20.5C19 20.5 21 18.5 21 16V8C21 5.5 19 3.5 16.5 3.5Z" fill="#D97706" fillOpacity={0.15} stroke="#D97706" strokeWidth={1.5} />
        <path d="M7.5 3.5C5 3.5 3 5.5 3 8V16C3 18.5 5 20.5 7.5 20.5C10 20.5 12 18.5 12 16V8C12 5.5 10 3.5 7.5 3.5Z" fill="#D97706" fillOpacity={0.15} stroke="#D97706" strokeWidth={1.5} />
      </svg>
    ),
    models: ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-20250414"],
    configKey: "claude_model",
    color: "amber",
    badge: "Recommended",
    requiresKey: true,
    keyName: "ANTHROPIC_API_KEY",
  },
  {
    id: "openai",
    name: "OpenAI ChatGPT",
    description: "Versatile general-purpose model. Strong at structured output and medical knowledge extraction.",
    icon: (
      <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none">
        <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.998 5.998 0 0 0-3.998 2.9 6.05 6.05 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073z" fill="#10A37F" fillOpacity={0.15} stroke="#10A37F" strokeWidth={1} />
        <circle cx="12" cy="12" r="3" fill="#10A37F" />
      </svg>
    ),
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-preview"],
    configKey: "openai_model",
    color: "emerald",
    badge: "Popular",
    requiresKey: true,
    keyName: "OPENAI_API_KEY",
  },
  {
    id: "ollama",
    name: "Ollama — DeepSeek R1",
    description: "Local inference with DeepSeek-R1:7b. No data leaves your infrastructure — ideal for PHI-sensitive workflows.",
    icon: (
      <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="6" width="18" height="12" rx="3" fill="#7C3AED" fillOpacity={0.15} stroke="#7C3AED" strokeWidth={1.5} />
        <circle cx="8" cy="12" r="1.5" fill="#7C3AED" />
        <circle cx="12" cy="12" r="1.5" fill="#7C3AED" />
        <circle cx="16" cy="12" r="1.5" fill="#7C3AED" />
        <path d="M3 9h18" stroke="#7C3AED" strokeWidth={0.5} opacity={0.5} />
        <path d="M3 15h18" stroke="#7C3AED" strokeWidth={0.5} opacity={0.5} />
      </svg>
    ),
    models: ["deepseek-r1:7b", "deepseek-r1:14b", "llama3.2", "mistral", "codellama"],
    configKey: "ollama_model",
    color: "violet",
    badge: "Local / Private",
    requiresKey: false,
    keyName: "localhost:12434",
  },
];

function LLMTab({ status, onRefresh, onSwitch }: { status: LLMStatus | null; onRefresh: () => void; onSwitch: (provider: string) => void }) {
  const [switching, setSwitching] = useState<string | null>(null);
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>({});

  const activeProvider = status?.primary_provider || "claude";

  const handleSwitch = async (providerId: string) => {
    setSwitching(providerId);
    await onSwitch(providerId);
    setSwitching(null);
  };

  const colorMap: Record<string, { ring: string; bg: string; text: string; badge: string; dot: string }> = {
    amber: { ring: "ring-amber-500/30", bg: "bg-amber-50 dark:bg-amber-950/30", text: "text-amber-700 dark:text-amber-400", badge: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300", dot: "bg-amber-500" },
    emerald: { ring: "ring-emerald-500/30", bg: "bg-emerald-50 dark:bg-emerald-950/30", text: "text-emerald-700 dark:text-emerald-400", badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300", dot: "bg-emerald-500" },
    violet: { ring: "ring-violet-500/30", bg: "bg-violet-50 dark:bg-violet-950/30", text: "text-violet-700 dark:text-violet-400", badge: "bg-violet-100 text-violet-800 dark:bg-violet-900/50 dark:text-violet-300", dot: "bg-violet-500" },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">LLM Provider Configuration</h3>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">Select your preferred LLM for clinical reasoning. Provider can be switched at any time.</p>
        </div>
        <button onClick={onRefresh} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" /></svg>
          Refresh
        </button>
      </div>

      {/* Status Summary */}
      {status && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-full bg-gray-100 dark:bg-gray-800 px-3 py-1.5">
            <span className={`inline-block h-2 w-2 rounded-full ${status.status === "available" || status.status === "demo" ? "bg-emerald-500" : "bg-red-500"}`} />
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 capitalize">{status.status === "demo" ? "Demo Mode" : status.status}</span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Temperature: <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{String(status.config?.temperature ?? 0.3)}</span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Max Tokens: <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{String(status.config?.max_tokens ?? 2000)}</span>
          </div>
        </div>
      )}

      {/* Provider Cards */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {LLM_PROVIDERS.map((provider) => {
          const isActive = activeProvider === provider.id || activeProvider === (provider.id === "claude" ? "claude" : provider.id === "openai" ? "openai" : "ollama");
          const isActiveMatch = activeProvider.includes(provider.id) || (provider.id === "claude" && activeProvider.includes("claude"));
          const active = isActive || isActiveMatch;
          const colors = colorMap[provider.color] || colorMap.amber;
          const currentModel = String(status?.config?.[provider.configKey] || provider.models[0]);
          const selected = selectedModels[provider.id] || currentModel;
          const isAvailable = status?.available_providers?.includes(provider.id) ?? false;

          return (
            <div
              key={provider.id}
              className={`relative rounded-2xl border-2 p-5 transition-all duration-200 ${
                active
                  ? `border-transparent ring-2 ${colors.ring} ${colors.bg} shadow-md`
                  : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm"
              }`}
            >
              {/* Active indicator */}
              {active && (
                <div className="absolute -top-2.5 right-4">
                  <span className={`inline-flex items-center gap-1 rounded-full ${colors.badge} px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider`}>
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" /></svg>
                    Active
                  </span>
                </div>
              )}

              {/* Provider header */}
              <div className="flex items-start gap-3">
                <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl ${active ? colors.bg : "bg-gray-100 dark:bg-gray-800"}`}>
                  {provider.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">{provider.name}</h4>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${colors.badge}`}>{provider.badge}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{provider.description}</p>
                </div>
              </div>

              {/* Model selector */}
              <div className="mt-4">
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5">Model</label>
                <select
                  value={selected}
                  onChange={(e) => setSelectedModels((prev) => ({ ...prev, [provider.id]: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  {provider.models.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* Connection info */}
              <div className="mt-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                {provider.requiresKey ? (
                  <>
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" /></svg>
                    <span>Requires <code className="rounded bg-gray-100 dark:bg-gray-700 px-1 py-0.5 font-mono text-[10px]">{provider.keyName}</code></span>
                  </>
                ) : (
                  <>
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" /></svg>
                    <span>Local — <code className="rounded bg-gray-100 dark:bg-gray-700 px-1 py-0.5 font-mono text-[10px]">{provider.keyName}</code></span>
                  </>
                )}
                {isAvailable && (
                  <span className="ml-auto flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">Connected</span>
                  </span>
                )}
              </div>

              {/* Action button */}
              <div className="mt-4">
                {active ? (
                  <div className={`flex items-center justify-center gap-2 rounded-lg ${colors.bg} px-4 py-2.5 text-sm font-semibold ${colors.text}`}>
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" /></svg>
                    Currently Active
                  </div>
                ) : (
                  <button
                    onClick={() => handleSwitch(provider.id)}
                    disabled={switching !== null}
                    className="w-full rounded-lg bg-gradient-to-r from-gray-800 to-gray-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:from-gray-700 hover:to-gray-800 hover:shadow-md disabled:opacity-50 dark:from-gray-600 dark:to-gray-700 dark:hover:from-gray-500 dark:hover:to-gray-600"
                  >
                    {switching === provider.id ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                        Switching...
                      </span>
                    ) : (
                      `Switch to ${provider.name.split(" ")[0]}`
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error */}
      {status?.error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          {status.error}
        </div>
      )}

      {/* Loading state */}
      {!status && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4 sm:p-8 text-center">
          <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-gray-300 dark:border-gray-600 border-t-healthos-600" />
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Loading LLM configuration...</p>
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
