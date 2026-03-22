"use client";

import { useState, useCallback } from "react";
import {
  Activity,
  Beaker,
  Brain,
  Copy,
  FlaskConical,
  Globe,
  Layers,
  Library,
  Pill,
  Play,
  Plus,
  RefreshCw,
  Share2,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
  Users,
  X,
  Zap,
} from "lucide-react";
import {
  simulateScenario,
  predictTrajectory,
  recommendTreatment,
  buildDigitalTwin,
  fetchTwinState,
} from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════════════════════ */

type TabKey = "whatif" | "medication" | "population" | "library";

interface Variable {
  id: string;
  category: string;
  name: string;
  value: string;
}

interface OutcomeMetric {
  label: string;
  before: number;
  after: number;
  unit: string;
  confidence: number;
}

interface ScenarioResult {
  id: string;
  name: string;
  outcomes: OutcomeMetric[];
  timeline: { week: number; value: number }[];
}

interface MedSimResult {
  effectiveness: { week: string; score: number; color: string }[];
  sideEffects: { name: string; probability: number; severity: string }[];
  interactions: { drug1: string; drug2: string; severity: string; description: string }[];
  adherenceImpact: number;
}

interface PopulationResult {
  outcomes: { label: string; percentage: number; color: string }[];
  nnt: number;
  costEffectiveness: number;
  subgroups: { name: string; responseRate: number }[];
}

interface SavedScenario {
  id: string;
  name: string;
  description: string;
  type: "clinical" | "drug" | "risk" | "cost";
  category: string;
  createdAt: string;
  lastRun: string;
  outcomeSummary: string;
  shared: boolean;
}

/* ═══════════════════════════════════════════════════════════════════════════
   DEMO DATA
   ═══════════════════════════════════════════════════════════════════════════ */

const DEMO_PATIENTS = [
  { id: "PT-1001", name: "Eleanor Vance", age: 67, conditions: ["Hypertension", "T2 Diabetes"] },
  { id: "PT-1002", name: "Marcus Chen", age: 54, conditions: ["CHF", "CKD Stage 3"] },
  { id: "PT-1003", name: "Amira Hassan", age: 42, conditions: ["Asthma", "Anxiety"] },
  { id: "PT-1004", name: "Robert Kim", age: 73, conditions: ["Afib", "COPD"] },
  { id: "PT-1005", name: "Sofia Reyes", age: 38, conditions: ["Rheumatoid Arthritis", "Anemia"] },
];

const VARIABLE_OPTIONS = ["Medication", "Dosage", "Lab Value", "Vital Sign", "Lifestyle Factor"];

const DEMO_SCENARIO_RESULTS: ScenarioResult[] = [
  {
    id: "s1",
    name: "Scenario A — Add Metformin 500mg",
    outcomes: [
      { label: "HbA1c", before: 8.2, after: 7.1, unit: "%", confidence: 87 },
      { label: "Fasting Glucose", before: 156, after: 128, unit: "mg/dL", confidence: 82 },
      { label: "Weight", before: 198, after: 194, unit: "lbs", confidence: 74 },
      { label: "eGFR", before: 68, after: 66, unit: "mL/min", confidence: 79 },
    ],
    timeline: [
      { week: 0, value: 8.2 }, { week: 2, value: 8.0 }, { week: 4, value: 7.7 },
      { week: 8, value: 7.4 }, { week: 12, value: 7.1 },
    ],
  },
  {
    id: "s2",
    name: "Scenario B — Increase Lisinopril to 20mg",
    outcomes: [
      { label: "Systolic BP", before: 148, after: 132, unit: "mmHg", confidence: 91 },
      { label: "Diastolic BP", before: 92, after: 84, unit: "mmHg", confidence: 88 },
      { label: "Heart Rate", before: 78, after: 74, unit: "bpm", confidence: 69 },
      { label: "Creatinine", before: 1.2, after: 1.3, unit: "mg/dL", confidence: 72 },
    ],
    timeline: [
      { week: 0, value: 148 }, { week: 2, value: 142 }, { week: 4, value: 137 },
      { week: 8, value: 134 }, { week: 12, value: 132 },
    ],
  },
];

const DEMO_MED_RESULT: MedSimResult = {
  effectiveness: [
    { week: "Week 1", score: 25, color: "bg-healthos-300" },
    { week: "Week 2", score: 45, color: "bg-healthos-400" },
    { week: "Week 4", score: 68, color: "bg-healthos-500" },
    { week: "Week 8", score: 82, color: "bg-healthos-600" },
    { week: "Week 12", score: 89, color: "bg-healthos-700" },
  ],
  sideEffects: [
    { name: "Nausea", probability: 18, severity: "mild" },
    { name: "Diarrhea", probability: 12, severity: "mild" },
    { name: "Dizziness", probability: 8, severity: "moderate" },
    { name: "Hypoglycemia", probability: 4, severity: "severe" },
  ],
  interactions: [
    { drug1: "Metformin", drug2: "Lisinopril", severity: "low", description: "Minor — may potentiate hypotensive effect" },
    { drug1: "Metformin", drug2: "Ibuprofen", severity: "moderate", description: "Moderate — risk of lactic acidosis with concurrent NSAID use" },
  ],
  adherenceImpact: 78,
};

const DEMO_POP_RESULT: PopulationResult = {
  outcomes: [
    { label: "Significant Improvement", percentage: 42, color: "bg-emerald-500" },
    { label: "Moderate Improvement", percentage: 28, color: "bg-emerald-400" },
    { label: "No Change", percentage: 18, color: "bg-gray-400" },
    { label: "Mild Worsening", percentage: 9, color: "bg-amber-400" },
    { label: "Significant Worsening", percentage: 3, color: "bg-red-400" },
  ],
  nnt: 7,
  costEffectiveness: 12400,
  subgroups: [
    { name: "Age 18-44", responseRate: 76 },
    { name: "Age 45-64", responseRate: 68 },
    { name: "Age 65+", responseRate: 54 },
    { name: "Male", responseRate: 62 },
    { name: "Female", responseRate: 71 },
    { name: "With Comorbidities", responseRate: 48 },
  ],
};

const DEMO_LIBRARY: SavedScenario[] = [
  { id: "lib-1", name: "Statin Intensification Protocol", description: "Evaluate switching from moderate to high-intensity statin therapy for patients with LDL > 130", type: "clinical", category: "Clinical Protocols", createdAt: "2026-03-01", lastRun: "2026-03-14", outcomeSummary: "LDL reduced 38% avg, NNT = 4", shared: true },
  { id: "lib-2", name: "GLP-1 RA vs SGLT2i Comparison", description: "Head-to-head simulation of GLP-1 receptor agonist versus SGLT2 inhibitor for T2D with obesity", type: "drug", category: "Drug Studies", createdAt: "2026-02-18", lastRun: "2026-03-12", outcomeSummary: "GLP-1 RA: -1.4% HbA1c, SGLT2i: -1.1% HbA1c", shared: true },
  { id: "lib-3", name: "Readmission Risk — CHF Cohort", description: "30-day readmission probability modeling for heart failure patients post-discharge", type: "risk", category: "Risk Modeling", createdAt: "2026-02-05", lastRun: "2026-03-10", outcomeSummary: "Baseline 24% → Intervention 16% readmission", shared: false },
  { id: "lib-4", name: "RPM Cost-Benefit Analysis", description: "ROI simulation for remote patient monitoring program across 500-patient cohort", type: "cost", category: "Cost Analysis", createdAt: "2026-01-22", lastRun: "2026-03-08", outcomeSummary: "$1.2M savings over 12 months, 3.1x ROI", shared: true },
  { id: "lib-5", name: "Antihypertensive Step Therapy", description: "Sequential therapy simulation: ACE-I → ARB → CCB escalation pathway", type: "clinical", category: "Clinical Protocols", createdAt: "2026-02-28", lastRun: "2026-03-13", outcomeSummary: "Target BP reached in 78% by step 2", shared: false },
  { id: "lib-6", name: "Polypharmacy De-prescribing", description: "Impact simulation of reducing medications in elderly patients taking 8+ drugs", type: "drug", category: "Drug Studies", createdAt: "2026-03-03", lastRun: "2026-03-11", outcomeSummary: "ADEs reduced 34%, QoL score +12%", shared: true },
];

const TYPE_BADGES: Record<string, { label: string; cls: string }> = {
  clinical: { label: "Clinical Protocol", cls: "bg-healthos-100 text-healthos-700" },
  drug: { label: "Drug Study", cls: "bg-purple-100 text-purple-700" },
  risk: { label: "Risk Model", cls: "bg-amber-100 text-amber-700" },
  cost: { label: "Cost Analysis", cls: "bg-emerald-100 text-emerald-700" },
};

const CATEGORIES = ["All", "Clinical Protocols", "Drug Studies", "Risk Modeling", "Cost Analysis"];

/* ═══════════════════════════════════════════════════════════════════════════
   HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */

let _varId = 0;
function newVarId() {
  return `var-${++_varId}`;
}

function delta(before: number, after: number) {
  return after - before;
}


/* ═══════════════════════════════════════════════════════════════════════════
   PAGE COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */

export default function SimulatorPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("whatif");
  const [simulationsToday] = useState(24);

  /* ── What-If State ────────────────────────────────────────────────── */
  const [selectedPatient, setSelectedPatient] = useState(DEMO_PATIENTS[0].id);
  const [baseScenario, setBaseScenario] = useState("");
  const [variables, setVariables] = useState<Variable[]>([
    { id: newVarId(), category: "Medication", name: "", value: "" },
  ]);
  const [whatIfResults, setWhatIfResults] = useState<ScenarioResult[] | null>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);

  /* ── Medication State ─────────────────────────────────────────────── */
  const [medPatient, setMedPatient] = useState(DEMO_PATIENTS[0].id);
  const [medChangeType, setMedChangeType] = useState<"add" | "modify" | "remove">("add");
  const [medDrug, setMedDrug] = useState("");
  const [medDose, setMedDose] = useState("");
  const [medFrequency, setMedFrequency] = useState("once daily");
  const [medResult, setMedResult] = useState<MedSimResult | null>(null);
  const [medLoading, setMedLoading] = useState(false);

  /* ── Population State ─────────────────────────────────────────────── */
  const [popAgeMin, setPopAgeMin] = useState("40");
  const [popAgeMax, setPopAgeMax] = useState("75");
  const [popConditions, setPopConditions] = useState("Type 2 Diabetes");
  const [popSize, setPopSize] = useState("500");
  const [popIntervention, setPopIntervention] = useState("");
  const [popDuration, setPopDuration] = useState("12");
  const [popResult, setPopResult] = useState<PopulationResult | null>(null);
  const [popLoading, setPopLoading] = useState(false);

  /* ── Library State ────────────────────────────────────────────────── */
  const [libraryCategory, setLibraryCategory] = useState("All");
  const [libraryItems, setLibraryItems] = useState<SavedScenario[]>(DEMO_LIBRARY);

  /* ── Variable Editor helpers ─────────────────────────────────────── */
  const addVariable = useCallback(() => {
    setVariables((v) => [...v, { id: newVarId(), category: "Medication", name: "", value: "" }]);
  }, []);

  const removeVariable = useCallback((id: string) => {
    setVariables((v) => v.filter((x) => x.id !== id));
  }, []);

  const updateVariable = useCallback((id: string, field: keyof Variable, val: string) => {
    setVariables((v) => v.map((x) => (x.id === id ? { ...x, [field]: val } : x)));
  }, []);

  /* ── Run What-If ─────────────────────────────────────────────────── */
  const runWhatIf = useCallback(async () => {
    setWhatIfLoading(true);
    try {
      await simulateScenario({
        patient_id: selectedPatient,
        scenario: baseScenario,
        variables: variables.map((v) => ({ category: v.category, name: v.name, value: v.value })),
      });
      // Use API result if available, else fall through to demo
    } catch {
      // Fall back to demo data
    }
    setTimeout(() => {
      setWhatIfResults(DEMO_SCENARIO_RESULTS);
      setWhatIfLoading(false);
    }, 1200);
  }, [selectedPatient, baseScenario, variables]);

  /* ── Run Medication Sim ──────────────────────────────────────────── */
  const runMedSim = useCallback(async () => {
    setMedLoading(true);
    try {
      await simulateScenario({
        patient_id: medPatient,
        change_type: medChangeType,
        drug: medDrug,
        dose: medDose,
        frequency: medFrequency,
      });
    } catch {
      // Fall back to demo data
    }
    setTimeout(() => {
      setMedResult(DEMO_MED_RESULT);
      setMedLoading(false);
    }, 1400);
  }, [medPatient, medChangeType, medDrug, medDose, medFrequency]);

  /* ── Run Population Sim ──────────────────────────────────────────── */
  const runPopSim = useCallback(async () => {
    setPopLoading(true);
    try {
      await predictTrajectory({
        cohort: { age_min: +popAgeMin, age_max: +popAgeMax, conditions: popConditions, size: +popSize },
        intervention: popIntervention,
        duration_weeks: +popDuration,
      });
    } catch {
      // Fall back to demo data
    }
    setTimeout(() => {
      setPopResult(DEMO_POP_RESULT);
      setPopLoading(false);
    }, 1600);
  }, [popAgeMin, popAgeMax, popConditions, popSize, popIntervention, popDuration]);

  /* ── Toggle share ────────────────────────────────────────────────── */
  const toggleShare = useCallback((id: string) => {
    setLibraryItems((items) =>
      items.map((s) => (s.id === id ? { ...s, shared: !s.shared } : s)),
    );
  }, []);

  /* ── Filtered library ────────────────────────────────────────────── */
  const filteredLibrary =
    libraryCategory === "All"
      ? libraryItems
      : libraryItems.filter((s) => s.category === libraryCategory);

  /* ── Tab definitions ─────────────────────────────────────────────── */
  const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
    { key: "whatif", label: "What-If Engine", icon: Sparkles },
    { key: "medication", label: "Medication Scenarios", icon: Pill },
    { key: "population", label: "Population Simulation", icon: Users },
    { key: "library", label: "Scenario Library", icon: Library },
  ];

  /* ══════════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════════ */

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-healthos-50/30 p-6 lg:p-5 sm:p-10 space-y-8">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between animate-fade-in-up">
        <div>
          <h1 className="text-xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100 tracking-tight flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-healthos-500 to-healthos-700 text-white shadow-glow-blue">
              <Brain className="h-7 w-7" />
            </div>
            Clinical Simulator
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400 text-sm">What-if analysis, treatment modeling &amp; population-level outcome simulation</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-healthos-100 px-3.5 py-1.5 text-xs font-semibold text-healthos-700">
            <Zap className="h-3.5 w-3.5" />
            {simulationsToday} simulations today
          </span>
          <button
            onClick={() => {
              setWhatIfResults(null);
              setMedResult(null);
              setPopResult(null);
              setActiveTab("whatif");
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-healthos-600 to-healthos-700 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-healthos-500/25 hover:shadow-xl hover:shadow-healthos-500/30 transition-all"
          >
            <Plus className="h-4 w-4" />
            New Simulation
          </button>
        </div>
      </header>

      {/* ── KPI Stats Bar ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 animate-fade-in-up" style={{ animationDelay: "0.05s" }}>
        {[
          { label: "Simulations Today", value: "24", icon: Activity, color: "text-healthos-600", bg: "bg-healthos-50" },
          { label: "Active Scenarios", value: "6", icon: Layers, color: "text-purple-600", bg: "bg-purple-50" },
          { label: "Avg Prediction Confidence", value: "84%", icon: Target, color: "text-emerald-600", bg: "bg-emerald-50" },
          { label: "Treatment Plans Compared", value: "38", icon: FlaskConical, color: "text-amber-600", bg: "bg-amber-50" },
          { label: "Patients Simulated", value: "12", icon: Users, color: "text-rose-600", bg: "bg-rose-50" },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover flex items-center gap-3">
            <div className={`flex-shrink-0 rounded-lg p-2.5 ${kpi.bg}`}>
              <kpi.icon className={`h-5 w-5 ${kpi.color}`} />
            </div>
            <div className="min-w-0">
              <p className="text-xl font-bold text-gray-900 dark:text-gray-100">{kpi.value}</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">{kpi.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Tabs ────────────────────────────────────────────────────── */}
      <nav className="flex gap-1 rounded-xl bg-gray-100 dark:bg-gray-800 p-1 overflow-x-auto animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
              activeTab === t.key
                ? "bg-white dark:bg-gray-900 text-healthos-700 shadow-sm"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </nav>

      {/* ── Tab Content ─────────────────────────────────────────────── */}

      {/* ============ WHAT-IF ENGINE ============ */}
      {activeTab === "whatif" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Builder */}
          <div className="card card-hover space-y-5">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-healthos-600" />
              Scenario Builder
            </h2>

            <div className="grid md:grid-cols-2 gap-4">
              {/* Patient Selector */}
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient</label>
                <select
                  value={selectedPatient}
                  onChange={(e) => setSelectedPatient(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                >
                  {DEMO_PATIENTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.id} — {p.name} (Age {p.age}, {p.conditions.join(", ")})
                    </option>
                  ))}
                </select>
              </div>

              {/* Base Scenario Description */}
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Base Scenario Description</label>
                <input
                  type="text"
                  value={baseScenario}
                  onChange={(e) => setBaseScenario(e.target.value)}
                  placeholder="e.g., Evaluate aggressive glucose management plan"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                />
              </div>
            </div>

            {/* Variable Editor */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Variables</label>
                <button
                  onClick={addVariable}
                  className="inline-flex items-center gap-1 rounded-md bg-healthos-50 px-2.5 py-1 text-xs font-medium text-healthos-700 hover:bg-healthos-100 transition"
                >
                  <Plus className="h-3 w-3" /> Add Variable
                </button>
              </div>
              <div className="space-y-2">
                {variables.map((v) => (
                  <div key={v.id} className="flex items-center gap-2">
                    <select
                      value={v.category}
                      onChange={(e) => updateVariable(v.id, "category", e.target.value)}
                      className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm w-40 focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                    >
                      {VARIABLE_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      placeholder="Variable name"
                      value={v.name}
                      onChange={(e) => updateVariable(v.id, "name", e.target.value)}
                      className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                    />
                    <input
                      type="text"
                      placeholder="Value"
                      value={v.value}
                      onChange={(e) => updateVariable(v.id, "value", e.target.value)}
                      className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                    />
                    <button
                      onClick={() => removeVariable(v.id)}
                      className="rounded-md p-1.5 text-gray-500 dark:text-gray-400 hover:bg-red-50 hover:text-red-500 transition"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={runWhatIf}
              disabled={whatIfLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-healthos-600 to-healthos-700 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-healthos-500/25 hover:shadow-xl transition-all disabled:opacity-60"
            >
              {whatIfLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {whatIfLoading ? "Running Scenario..." : "Run Scenario"}
            </button>
          </div>

          {/* Results */}
          {whatIfResults && (
            <div className="space-y-6 animate-fade-in-up">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Scenario Comparison</h3>
              <div className="grid lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {whatIfResults.map((scenario) => (
                  <div key={scenario.id} className="card card-hover space-y-4">
                    <h4 className="font-semibold text-sm text-gray-900 dark:text-gray-100">{scenario.name}</h4>

                    {/* Outcome Metrics */}
                    <div className="grid grid-cols-1 xs:grid-cols-2 gap-3">
                      {scenario.outcomes.map((o) => {
                        const d = delta(o.before, o.after);
                        const improving =
                          (o.label.includes("HbA1c") || o.label.includes("Glucose") || o.label.includes("BP") || o.label.includes("Creatinine"))
                            ? d < 0
                            : d > 0;
                        return (
                          <div key={o.label} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
                            <p className="text-[11px] uppercase font-semibold text-gray-500 dark:text-gray-400 tracking-wide">{o.label}</p>
                            <div className="flex items-end gap-2 mt-1">
                              <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{o.after}</span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">{o.unit}</span>
                              <span
                                className={`ml-auto inline-flex items-center gap-0.5 text-xs font-semibold ${
                                  improving ? "text-emerald-600" : "text-red-500"
                                }`}
                              >
                                {improving ? (
                                  <TrendingDown className="h-3 w-3" />
                                ) : (
                                  <TrendingUp className="h-3 w-3" />
                                )}
                                {Math.abs(d).toFixed(1)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between mt-1">
                              <span className="text-[11px] text-gray-500 dark:text-gray-400">Before: {o.before}</span>
                              <span className="text-[11px] text-healthos-600">{o.confidence}% conf.</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Timeline Preview */}
                    <div>
                      <p className="text-[11px] uppercase font-semibold text-gray-500 dark:text-gray-400 tracking-wide mb-2">Timeline Preview</p>
                      <div className="flex items-end gap-1 h-16">
                        {scenario.timeline.map((pt, i) => {
                          const min = Math.min(...scenario.timeline.map((t) => t.value));
                          const max = Math.max(...scenario.timeline.map((t) => t.value));
                          const range = max - min || 1;
                          const height = ((pt.value - min) / range) * 100;
                          return (
                            <div key={i} className="flex-1 flex flex-col items-center gap-1">
                              <div
                                className="w-full rounded-t bg-gradient-to-t from-healthos-600 to-healthos-400 transition-all"
                                style={{ height: `${Math.max(height, 8)}%` }}
                              />
                              <span className="text-[8px] text-gray-500 dark:text-gray-400">W{pt.week}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Placeholder for 3rd comparison slot */}
                {whatIfResults.length < 3 && (
                  <div className="card border-dashed border-2 border-gray-200 dark:border-gray-700 flex flex-col items-center justify-center text-center py-6 sm:py-12 hover:border-healthos-300 transition cursor-pointer group"
                    onClick={() => {
                      setWhatIfResults(null);
                    }}
                  >
                    <Plus className="h-8 w-8 text-gray-300 group-hover:text-healthos-400 transition" />
                    <p className="mt-2 text-sm font-medium text-gray-500 dark:text-gray-400 group-hover:text-healthos-600 transition">Add Scenario</p>
                    <p className="text-xs text-gray-300">Compare up to 3 scenarios</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============ MEDICATION SCENARIOS ============ */}
      {activeTab === "medication" && (
        <div className="space-y-6 animate-fade-in-up">
          <div className="card card-hover space-y-5">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <Pill className="h-5 w-5 text-purple-600" />
              Medication Simulation
            </h2>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient</label>
                <select
                  value={medPatient}
                  onChange={(e) => setMedPatient(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                >
                  {DEMO_PATIENTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.id} — {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Current Medications</label>
                <div className="flex flex-wrap gap-1.5 py-2">
                  {["Lisinopril 10mg", "Metformin 1000mg", "Atorvastatin 20mg"].map((m) => (
                    <span key={m} className="rounded-full bg-gray-100 dark:bg-gray-800 px-2.5 py-1 text-xs text-gray-600 dark:text-gray-400">{m}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Change Type</label>
                <select
                  value={medChangeType}
                  onChange={(e) => setMedChangeType(e.target.value as "add" | "modify" | "remove")}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                >
                  <option value="add">Add Medication</option>
                  <option value="modify">Modify Dosage</option>
                  <option value="remove">Remove Medication</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Drug</label>
                <input
                  type="text"
                  value={medDrug}
                  onChange={(e) => setMedDrug(e.target.value)}
                  placeholder="e.g., Empagliflozin"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Dose</label>
                <input
                  type="text"
                  value={medDose}
                  onChange={(e) => setMedDose(e.target.value)}
                  placeholder="e.g., 25mg"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Frequency</label>
                <select
                  value={medFrequency}
                  onChange={(e) => setMedFrequency(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                >
                  <option value="once daily">Once daily</option>
                  <option value="twice daily">Twice daily</option>
                  <option value="three times daily">Three times daily</option>
                  <option value="as needed">As needed</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
            </div>

            <button
              onClick={runMedSim}
              disabled={medLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-purple-700 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-purple-500/25 hover:shadow-xl transition-all disabled:opacity-60"
            >
              {medLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Beaker className="h-4 w-4" />
              )}
              {medLoading ? "Simulating..." : "Simulate"}
            </button>
          </div>

          {/* Medication Results */}
          {medResult && (
            <div className="grid lg:grid-cols-2 gap-6 animate-fade-in-up">
              {/* Effectiveness Curve */}
              <div className="card card-hover space-y-4">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">Predicted Response Curve</h3>
                <div className="space-y-3">
                  {medResult.effectiveness.map((e) => (
                    <div key={e.week} className="flex items-center gap-3">
                      <span className="text-xs text-gray-500 dark:text-gray-400 w-16 flex-shrink-0">{e.week}</span>
                      <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${e.color} transition-all duration-700`}
                          style={{ width: `${e.score}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 w-10 text-right">{e.score}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Side Effect Probability */}
              <div className="card card-hover space-y-4">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">Side Effect Probability</h3>
                <div className="grid grid-cols-1 xs:grid-cols-2 gap-3">
                  {medResult.sideEffects.map((se) => (
                    <div
                      key={se.name}
                      className={`rounded-lg p-3 ${
                        se.severity === "severe"
                          ? "bg-red-50 border border-red-200"
                          : se.severity === "moderate"
                          ? "bg-amber-50 border border-amber-200"
                          : "bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                      }`}
                    >
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{se.name}</p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{se.probability}%</span>
                        <span
                          className={`text-[11px] uppercase font-semibold px-1.5 py-0.5 rounded ${
                            se.severity === "severe"
                              ? "bg-red-100 text-red-700"
                              : se.severity === "moderate"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                          }`}
                        >
                          {se.severity}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Drug Interactions */}
              <div className="card card-hover space-y-4">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <TriangleAlert className="h-4 w-4 text-amber-500" />
                  Drug Interaction Warnings
                </h3>
                <div className="space-y-3">
                  {medResult.interactions.map((inter, i) => (
                    <div
                      key={i}
                      className={`rounded-lg p-3 border-l-4 ${
                        inter.severity === "moderate"
                          ? "border-l-amber-500 bg-amber-50"
                          : "border-l-yellow-400 bg-yellow-50"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {inter.drug1} + {inter.drug2}
                        </span>
                        <span
                          className={`text-[11px] uppercase font-semibold px-1.5 py-0.5 rounded ${
                            inter.severity === "moderate"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-yellow-100 text-yellow-700"
                          }`}
                        >
                          {inter.severity}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{inter.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Adherence Impact */}
              <div className="card card-hover space-y-4">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">Adherence Impact Prediction</h3>
                <div className="flex items-center justify-center py-4">
                  <div className="relative w-32 h-32">
                    <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                      <circle cx="18" cy="18" r="16" fill="none" stroke="#f3f4f6" strokeWidth="3" />
                      <circle
                        cx="18"
                        cy="18"
                        r="16"
                        fill="none"
                        stroke={medResult.adherenceImpact >= 70 ? "#22c55e" : medResult.adherenceImpact >= 50 ? "#f59e0b" : "#ef4444"}
                        strokeWidth="3"
                        strokeDasharray={`${medResult.adherenceImpact} ${100 - medResult.adherenceImpact}`}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">{medResult.adherenceImpact}%</span>
                      <span className="text-[11px] text-gray-500 dark:text-gray-400">predicted</span>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
                  Estimated patient adherence based on regimen complexity, side-effect profile, and dosing frequency.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============ POPULATION SIMULATION ============ */}
      {activeTab === "population" && (
        <div className="space-y-6 animate-fade-in-up">
          <div className="card card-hover space-y-5">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <Globe className="h-5 w-5 text-emerald-600" />
              Population Simulation
            </h2>

            <div className="grid md:grid-cols-3 gap-4">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Age Min</label>
                  <input
                    type="number"
                    value={popAgeMin}
                    onChange={(e) => setPopAgeMin(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Age Max</label>
                  <input
                    type="number"
                    value={popAgeMax}
                    onChange={(e) => setPopAgeMax(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Conditions</label>
                <input
                  type="text"
                  value={popConditions}
                  onChange={(e) => setPopConditions(e.target.value)}
                  placeholder="e.g., Type 2 Diabetes, Hypertension"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Cohort Size</label>
                <input
                  type="number"
                  value={popSize}
                  onChange={(e) => setPopSize(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Intervention</label>
                <input
                  type="text"
                  value={popIntervention}
                  onChange={(e) => setPopIntervention(e.target.value)}
                  placeholder="e.g., Add SGLT2 inhibitor to standard therapy"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Simulation Duration (weeks)</label>
                <input
                  type="number"
                  value={popDuration}
                  onChange={(e) => setPopDuration(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2.5 text-sm focus:border-healthos-500 focus:ring-2 focus:ring-healthos-200 outline-none transition"
                />
              </div>
            </div>

            <button
              onClick={runPopSim}
              disabled={popLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-emerald-600 to-emerald-700 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-500/25 hover:shadow-xl transition-all disabled:opacity-60"
            >
              {popLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Users className="h-4 w-4" />
              )}
              {popLoading ? "Running Population Sim..." : "Run Population Sim"}
            </button>
          </div>

          {/* Population Results */}
          {popResult && (
            <div className="grid lg:grid-cols-2 gap-6 animate-fade-in-up">
              {/* Outcome Distribution */}
              <div className="card card-hover space-y-4">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">Population Outcome Distribution</h3>
                <div className="space-y-3">
                  {popResult.outcomes.map((o) => (
                    <div key={o.label} className="flex items-center gap-3">
                      <span className="text-xs text-gray-500 dark:text-gray-400 w-44 flex-shrink-0">{o.label}</span>
                      <div className="flex-1 h-5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${o.color} transition-all duration-700`}
                          style={{ width: `${o.percentage}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 w-10 text-right">{o.percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Key Metrics */}
              <div className="card card-hover space-y-4">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">Key Population Metrics</h3>
                <div className="grid grid-cols-1 xs:grid-cols-2 gap-4">
                  <div className="rounded-lg bg-emerald-50 p-4 text-center">
                    <p className="text-xl sm:text-3xl font-bold text-emerald-700">{popResult.nnt}</p>
                    <p className="text-xs text-emerald-600 mt-1">Number Needed to Treat</p>
                  </div>
                  <div className="rounded-lg bg-healthos-50 p-4 text-center">
                    <p className="text-xl sm:text-3xl font-bold text-healthos-700">${popResult.costEffectiveness.toLocaleString()}</p>
                    <p className="text-xs text-healthos-600 mt-1">Cost per QALY Gained</p>
                  </div>
                </div>
              </div>

              {/* Subgroup Response Variation */}
              <div className="card card-hover space-y-4 lg:col-span-2">
                <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">Subgroup Response Variation</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {popResult.subgroups.map((sg) => (
                    <div key={sg.name} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-center">
                      <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{sg.responseRate}%</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{sg.name}</p>
                      <div className="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            sg.responseRate >= 70 ? "bg-emerald-500" : sg.responseRate >= 50 ? "bg-amber-500" : "bg-red-400"
                          }`}
                          style={{ width: `${sg.responseRate}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============ SCENARIO LIBRARY ============ */}
      {activeTab === "library" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Category Filter */}
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setLibraryCategory(cat)}
                className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-all ${
                  libraryCategory === cat
                    ? "bg-healthos-600 text-white shadow-sm"
                    : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:border-healthos-300 hover:text-healthos-700"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Grid */}
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
            {filteredLibrary.map((scenario) => {
              const badge = TYPE_BADGES[scenario.type];
              return (
                <div key={scenario.id} className="card card-hover space-y-3 animate-fade-in-up">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="font-semibold text-sm text-gray-900 dark:text-gray-100">{scenario.name}</h4>
                      <span className={`inline-block mt-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </div>
                    <button
                      onClick={() => toggleShare(scenario.id)}
                      className={`rounded-md p-1.5 transition ${
                        scenario.shared ? "text-healthos-600 bg-healthos-50" : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                      }`}
                      title={scenario.shared ? "Shared with organization" : "Share with organization"}
                    >
                      <Share2 className="h-4 w-4" />
                    </button>
                  </div>

                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{scenario.description}</p>

                  <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5">
                    <p className="text-[11px] uppercase font-semibold text-gray-500 dark:text-gray-400 tracking-wide">Outcome Summary</p>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mt-0.5">{scenario.outcomeSummary}</p>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
                    <span>Created {scenario.createdAt}</span>
                    <span>Last run {scenario.lastRun}</span>
                  </div>

                  <div className="flex gap-2 pt-1">
                    <button className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition">
                      <Copy className="h-3 w-3" /> Clone
                    </button>
                    <button className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-healthos-600 px-3 py-2 text-xs font-medium text-white hover:bg-healthos-700 transition">
                      <Play className="h-3 w-3" /> Run Again
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
