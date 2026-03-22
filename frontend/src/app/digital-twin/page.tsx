"use client";

import { useState, useCallback } from "react";
import {
  buildDigitalTwin,
  fetchTwinState,
  simulateScenario,
  predictTrajectory,
  recommendTreatment,
} from "@/lib/api";

/* ── Types ──────────────────────────────────────────────────────────────────── */

interface BodySystem {
  name: string;
  icon: string;
  state: "stable" | "at-risk" | "critical";
  metrics: { label: string; value: string }[];
  lastUpdated: string;
}

interface Twin {
  id: string;
  patient: string;
  age: number;
  conditions: string[];
  healthScore: number;
  lastUpdated: string;
  trajectory: "improving" | "stable" | "declining";
  vitals: { hr: number; bp: string; bmi: number; hba1c: number; egfr: number };
  bodySystems: BodySystem[];
  medications: { name: string; dose: string; frequency: string }[];
  stateTimeline: { date: string; event: string; system: string; change: "improved" | "worsened" | "stable" }[];
}

interface SimulationResult {
  metric: string;
  before: string;
  after: string;
  confidence: number;
  delta: number;
  unit: string;
}

interface ForecastMilestone {
  label: string;
  months: number;
  healthScore: number;
  confidence: [number, number];
  riskLevel: "low" | "moderate" | "high" | "critical";
  keyValues: { label: string; predicted: string }[];
}

interface TreatmentRecommendation {
  id: string;
  action: "add" | "modify" | "remove";
  medication: string;
  currentDose?: string;
  recommendedDose?: string;
  rationale: string;
  expectedOutcome: string;
  costEffectiveness: number;
  evidenceLevel: "A" | "B" | "C" | "D";
}

/* ── Demo Data ──────────────────────────────────────────────────────────────── */

const DEMO_BODY_SYSTEMS: BodySystem[] = [
  {
    name: "Cardiovascular",
    icon: "\u2764",
    state: "at-risk",
    metrics: [
      { label: "BP", value: "138/86 mmHg" },
      { label: "HR", value: "78 bpm" },
      { label: "EF", value: "52%" },
    ],
    lastUpdated: "2026-03-15T08:30:00Z",
  },
  {
    name: "Respiratory",
    icon: "\u{1FAC1}",
    state: "stable",
    metrics: [
      { label: "SpO2", value: "97%" },
      { label: "RR", value: "16/min" },
      { label: "FEV1", value: "82%" },
    ],
    lastUpdated: "2026-03-15T08:30:00Z",
  },
  {
    name: "Metabolic",
    icon: "\u26A1",
    state: "at-risk",
    metrics: [
      { label: "HbA1c", value: "7.2%" },
      { label: "Glucose", value: "142 mg/dL" },
      { label: "BMI", value: "29.4" },
    ],
    lastUpdated: "2026-03-15T07:15:00Z",
  },
  {
    name: "Neurological",
    icon: "\u{1F9E0}",
    state: "stable",
    metrics: [
      { label: "MMSE", value: "28/30" },
      { label: "GCS", value: "15" },
      { label: "Pain", value: "2/10" },
    ],
    lastUpdated: "2026-03-14T16:00:00Z",
  },
  {
    name: "Renal",
    icon: "\u{1FAC0}",
    state: "critical",
    metrics: [
      { label: "eGFR", value: "48 mL/min" },
      { label: "Creatinine", value: "1.8 mg/dL" },
      { label: "BUN", value: "32 mg/dL" },
    ],
    lastUpdated: "2026-03-15T06:45:00Z",
  },
  {
    name: "Hepatic",
    icon: "\u{1F7E4}",
    state: "stable",
    metrics: [
      { label: "ALT", value: "28 U/L" },
      { label: "AST", value: "24 U/L" },
      { label: "Albumin", value: "3.9 g/dL" },
    ],
    lastUpdated: "2026-03-14T12:00:00Z",
  },
  {
    name: "Musculoskeletal",
    icon: "\u{1F9B4}",
    state: "stable",
    metrics: [
      { label: "DEXA", value: "T-score -1.2" },
      { label: "Vit D", value: "34 ng/mL" },
      { label: "Mobility", value: "Good" },
    ],
    lastUpdated: "2026-03-13T09:30:00Z",
  },
  {
    name: "Immunological",
    icon: "\u{1F6E1}",
    state: "stable",
    metrics: [
      { label: "WBC", value: "7.2 K/uL" },
      { label: "CRP", value: "1.4 mg/L" },
      { label: "ESR", value: "18 mm/hr" },
    ],
    lastUpdated: "2026-03-14T10:00:00Z",
  },
];

const DEMO_TIMELINE = [
  { date: "2026-03-15T08:30:00Z", event: "BP elevated to 142/90", system: "Cardiovascular", change: "worsened" as const },
  { date: "2026-03-14T14:00:00Z", event: "eGFR dropped to 48", system: "Renal", change: "worsened" as const },
  { date: "2026-03-13T10:00:00Z", event: "HbA1c improved to 7.2%", system: "Metabolic", change: "improved" as const },
  { date: "2026-03-12T08:00:00Z", event: "SpO2 normalized to 97%", system: "Respiratory", change: "improved" as const },
  { date: "2026-03-11T16:00:00Z", event: "Pain score reduced to 2/10", system: "Neurological", change: "improved" as const },
];

const DEMO_MEDICATIONS = [
  { name: "Metformin", dose: "1000mg", frequency: "BID" },
  { name: "Lisinopril", dose: "20mg", frequency: "QD" },
  { name: "Atorvastatin", dose: "40mg", frequency: "QD" },
  { name: "Amlodipine", dose: "5mg", frequency: "QD" },
  { name: "Aspirin", dose: "81mg", frequency: "QD" },
];

const SAMPLE_TWINS: Twin[] = [
  {
    id: "DT-001",
    patient: "Maria Santos",
    age: 67,
    conditions: ["Type 2 Diabetes", "Hypertension", "CKD Stage 3"],
    healthScore: 0.62,
    lastUpdated: "2026-03-15T08:30:00Z",
    trajectory: "stable",
    vitals: { hr: 78, bp: "138/86", bmi: 29.4, hba1c: 7.2, egfr: 48 },
    bodySystems: DEMO_BODY_SYSTEMS,
    medications: DEMO_MEDICATIONS,
    stateTimeline: DEMO_TIMELINE,
  },
  {
    id: "DT-002",
    patient: "James Chen",
    age: 54,
    conditions: ["CHF NYHA II", "Atrial Fibrillation"],
    healthScore: 0.55,
    lastUpdated: "2026-03-15T06:00:00Z",
    trajectory: "declining",
    vitals: { hr: 92, bp: "142/90", bmi: 31.2, hba1c: 5.8, egfr: 62 },
    bodySystems: DEMO_BODY_SYSTEMS.map((s) =>
      s.name === "Cardiovascular" ? { ...s, state: "critical" as const, metrics: [{ label: "BP", value: "142/90 mmHg" }, { label: "HR", value: "92 bpm" }, { label: "EF", value: "38%" }] } : s
    ),
    medications: [
      { name: "Carvedilol", dose: "25mg", frequency: "BID" },
      { name: "Furosemide", dose: "40mg", frequency: "QD" },
      { name: "Apixaban", dose: "5mg", frequency: "BID" },
      { name: "Lisinopril", dose: "10mg", frequency: "QD" },
    ],
    stateTimeline: [
      { date: "2026-03-15T06:00:00Z", event: "EF declined to 38%", system: "Cardiovascular", change: "worsened" },
      { date: "2026-03-14T12:00:00Z", event: "HR elevated to 92 bpm", system: "Cardiovascular", change: "worsened" },
      { date: "2026-03-13T08:00:00Z", event: "Weight gain +1.5kg", system: "Cardiovascular", change: "worsened" },
    ],
  },
  {
    id: "DT-003",
    patient: "Sarah Johnson",
    age: 45,
    conditions: ["Asthma", "Obesity"],
    healthScore: 0.74,
    lastUpdated: "2026-03-15T10:15:00Z",
    trajectory: "improving",
    vitals: { hr: 72, bp: "126/80", bmi: 32.1, hba1c: 5.4, egfr: 95 },
    bodySystems: DEMO_BODY_SYSTEMS.map((s) =>
      s.name === "Respiratory" ? { ...s, state: "at-risk" as const, metrics: [{ label: "SpO2", value: "95%" }, { label: "RR", value: "18/min" }, { label: "FEV1", value: "72%" }] } :
      s.name === "Renal" ? { ...s, state: "stable" as const, metrics: [{ label: "eGFR", value: "95 mL/min" }, { label: "Creatinine", value: "0.9 mg/dL" }, { label: "BUN", value: "14 mg/dL" }] } : s
    ),
    medications: [
      { name: "Fluticasone/Salmeterol", dose: "250/50mcg", frequency: "BID" },
      { name: "Albuterol PRN", dose: "90mcg", frequency: "PRN" },
      { name: "Semaglutide", dose: "1mg", frequency: "Weekly" },
    ],
    stateTimeline: [
      { date: "2026-03-15T10:15:00Z", event: "BMI trending down to 32.1", system: "Metabolic", change: "improved" },
      { date: "2026-03-14T08:00:00Z", event: "FEV1 improved to 72%", system: "Respiratory", change: "improved" },
    ],
  },
  {
    id: "DT-004",
    patient: "Robert Williams",
    age: 71,
    conditions: ["COPD", "Type 2 Diabetes", "CAD"],
    healthScore: 0.48,
    lastUpdated: "2026-03-15T12:45:00Z",
    trajectory: "declining",
    vitals: { hr: 88, bp: "148/92", bmi: 27.8, hba1c: 8.1, egfr: 42 },
    bodySystems: DEMO_BODY_SYSTEMS.map((s) =>
      s.name === "Cardiovascular" ? { ...s, state: "critical" as const, metrics: [{ label: "BP", value: "148/92 mmHg" }, { label: "HR", value: "88 bpm" }, { label: "EF", value: "44%" }] } :
      s.name === "Respiratory" ? { ...s, state: "critical" as const, metrics: [{ label: "SpO2", value: "92%" }, { label: "RR", value: "22/min" }, { label: "FEV1", value: "54%" }] } :
      s.name === "Metabolic" ? { ...s, state: "critical" as const, metrics: [{ label: "HbA1c", value: "8.1%" }, { label: "Glucose", value: "186 mg/dL" }, { label: "BMI", value: "27.8" }] } :
      s.name === "Renal" ? { ...s, state: "critical" as const, metrics: [{ label: "eGFR", value: "42 mL/min" }, { label: "Creatinine", value: "2.1 mg/dL" }, { label: "BUN", value: "38 mg/dL" }] } : s
    ),
    medications: [
      { name: "Tiotropium", dose: "18mcg", frequency: "QD" },
      { name: "Metformin", dose: "500mg", frequency: "BID" },
      { name: "Insulin Glargine", dose: "24 units", frequency: "QD" },
      { name: "Atorvastatin", dose: "80mg", frequency: "QD" },
      { name: "Aspirin", dose: "81mg", frequency: "QD" },
      { name: "Lisinopril", dose: "40mg", frequency: "QD" },
    ],
    stateTimeline: [
      { date: "2026-03-15T12:45:00Z", event: "SpO2 dropped to 92%", system: "Respiratory", change: "worsened" },
      { date: "2026-03-15T06:00:00Z", event: "Fasting glucose 186 mg/dL", system: "Metabolic", change: "worsened" },
      { date: "2026-03-14T14:00:00Z", event: "eGFR declined to 42", system: "Renal", change: "worsened" },
      { date: "2026-03-13T10:00:00Z", event: "BP spike 148/92", system: "Cardiovascular", change: "worsened" },
    ],
  },
];

const DEMO_SIMULATION_RESULTS: SimulationResult[] = [
  { metric: "Blood Pressure", before: "138/86", after: "128/78", confidence: 0.87, delta: -7.2, unit: "mmHg" },
  { metric: "HbA1c", before: "7.2%", after: "6.8%", confidence: 0.82, delta: -5.6, unit: "%" },
  { metric: "eGFR", before: "48", after: "51", confidence: 0.74, delta: 6.3, unit: "mL/min" },
  { metric: "Health Score", before: "62%", after: "71%", confidence: 0.79, delta: 14.5, unit: "%" },
  { metric: "10yr CV Risk", before: "18.4%", after: "14.2%", confidence: 0.71, delta: -22.8, unit: "%" },
];

const DEMO_FORECAST_MILESTONES: ForecastMilestone[] = [
  {
    label: "Now",
    months: 0,
    healthScore: 62,
    confidence: [62, 62],
    riskLevel: "moderate",
    keyValues: [{ label: "HbA1c", predicted: "7.2%" }, { label: "eGFR", predicted: "48" }],
  },
  {
    label: "3 mo",
    months: 3,
    healthScore: 65,
    confidence: [60, 70],
    riskLevel: "moderate",
    keyValues: [{ label: "HbA1c", predicted: "6.9%" }, { label: "eGFR", predicted: "47" }],
  },
  {
    label: "6 mo",
    months: 6,
    healthScore: 68,
    confidence: [58, 76],
    riskLevel: "moderate",
    keyValues: [{ label: "HbA1c", predicted: "6.7%" }, { label: "eGFR", predicted: "46" }],
  },
  {
    label: "12 mo",
    months: 12,
    healthScore: 70,
    confidence: [54, 80],
    riskLevel: "low",
    keyValues: [{ label: "HbA1c", predicted: "6.5%" }, { label: "eGFR", predicted: "45" }],
  },
  {
    label: "24 mo",
    months: 24,
    healthScore: 66,
    confidence: [48, 78],
    riskLevel: "moderate",
    keyValues: [{ label: "HbA1c", predicted: "6.6%" }, { label: "eGFR", predicted: "42" }],
  },
];

const DEMO_TREATMENT_RECS: TreatmentRecommendation[] = [
  {
    id: "TR-1",
    action: "add",
    medication: "Empagliflozin 10mg QD",
    rationale: "SGLT2 inhibitor shown to reduce cardiovascular events and slow CKD progression in T2DM patients with eGFR 25-75.",
    expectedOutcome: "Projected eGFR stabilization, 35% reduction in heart failure hospitalization risk.",
    costEffectiveness: 0.88,
    evidenceLevel: "A",
  },
  {
    id: "TR-2",
    action: "modify",
    medication: "Lisinopril",
    currentDose: "20mg QD",
    recommendedDose: "40mg QD",
    rationale: "Sub-optimal BP control at current dose. Target <130/80 per ACC/AHA guidelines for CKD patients.",
    expectedOutcome: "Projected BP reduction to 128/78 mmHg. Renal protective benefit with tighter control.",
    costEffectiveness: 0.92,
    evidenceLevel: "A",
  },
  {
    id: "TR-3",
    action: "add",
    medication: "Semaglutide 0.5mg weekly",
    rationale: "GLP-1 RA provides additional glycemic control, weight reduction, and cardiovascular benefit for patients with BMI >27.",
    expectedOutcome: "Expected HbA1c reduction of 0.8-1.2%, weight loss of 5-8%, 26% MACE reduction.",
    costEffectiveness: 0.76,
    evidenceLevel: "A",
  },
  {
    id: "TR-4",
    action: "remove",
    medication: "Amlodipine 5mg QD",
    rationale: "With Lisinopril uptitration and addition of SGLT2i, additional antihypertensive may cause hypotension. Peripheral edema reported.",
    expectedOutcome: "Reduced pill burden, elimination of peripheral edema side effect.",
    costEffectiveness: 0.95,
    evidenceLevel: "B",
  },
];

/* ── Helpers ────────────────────────────────────────────────────────────────── */

const stateColor = (state: string) =>
  state === "stable" ? "border-green-400 bg-green-50 text-green-700" :
  state === "at-risk" ? "border-yellow-400 bg-yellow-50 text-yellow-700" :
  "border-red-400 bg-red-50 text-red-700";

const stateDot = (state: string) =>
  state === "stable" ? "bg-green-500" : state === "at-risk" ? "bg-yellow-500" : "bg-red-500";

const trajectoryArrow = (t: string) =>
  t === "improving" ? { symbol: "\u2191", color: "text-green-600", label: "Improving" } :
  t === "stable" ? { symbol: "\u2192", color: "text-gray-600 dark:text-gray-400", label: "Stable" } :
  { symbol: "\u2193", color: "text-red-600", label: "Declining" };

const scoreColor = (s: number) =>
  s >= 0.7 ? "text-green-600" : s >= 0.5 ? "text-yellow-600" : "text-red-600";

const riskColor = (r: string) =>
  r === "low" ? "bg-green-100 text-green-700" :
  r === "moderate" ? "bg-yellow-100 text-yellow-700" :
  r === "high" ? "bg-orange-100 text-orange-700" :
  "bg-red-100 text-red-700";

const evidenceBadge = (level: string) =>
  level === "A" ? "bg-green-100 text-green-800" :
  level === "B" ? "bg-blue-100 text-blue-800" :
  level === "C" ? "bg-yellow-100 text-yellow-800" :
  "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200";

const actionBorder = (action: string) =>
  action === "add" ? "border-l-green-500" : action === "modify" ? "border-l-blue-500" : "border-l-red-500";

const actionLabel = (action: string) =>
  action === "add" ? { text: "ADD", color: "bg-green-100 text-green-700" } :
  action === "modify" ? { text: "MODIFY", color: "bg-blue-100 text-blue-700" } :
  { text: "REMOVE", color: "bg-red-100 text-red-700" };

const formatTimestamp = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

const changeIcon = (c: string) =>
  c === "improved" ? { symbol: "\u25B2", color: "text-green-500" } :
  c === "worsened" ? { symbol: "\u25BC", color: "text-red-500" } :
  { symbol: "\u25CF", color: "text-gray-500 dark:text-gray-400" };

type TabKey = "overview" | "simulation" | "forecasting" | "optimization";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Twin Overview" },
  { key: "simulation", label: "Scenario Simulation" },
  { key: "forecasting", label: "Trajectory Forecasting" },
  { key: "optimization", label: "Treatment Optimization" },
];

/* ── Page ───────────────────────────────────────────────────────────────────── */

export default function DigitalTwinPage() {
  const [twins, setTwins] = useState<Twin[]>(SAMPLE_TWINS);
  const [selectedTwin, setSelectedTwin] = useState<Twin>(SAMPLE_TWINS[0]);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [building, setBuilding] = useState(false);

  // Simulation state
  const [scenarioType, setScenarioType] = useState<"medication" | "lifestyle" | "treatment_stop">("medication");
  const [simForm, setSimForm] = useState<Record<string, string>>({});
  const [simRunning, setSimRunning] = useState(false);
  const [simResults, setSimResults] = useState<SimulationResult[] | null>(null);

  // Forecast state
  const [forecastCondition, setForecastCondition] = useState("");
  const [forecasting, setForecasting] = useState(false);
  const [forecastResults, setForecastResults] = useState<ForecastMilestone[] | null>(null);
  const [forecastAlerts, setForecastAlerts] = useState<string[]>([]);

  // Optimization state
  const [optimizing, setOptimizing] = useState(false);
  const [treatmentRecs, setTreatmentRecs] = useState<TreatmentRecommendation[] | null>(null);

  /* ── Handlers ─────────────────────────────────────────────────────────────── */

  const handleBuildTwin = useCallback(async () => {
    setBuilding(true);
    try {
      const result = await buildDigitalTwin({});
      const twinId = (result as Record<string, unknown>).twin_id as string || `DT-${String(twins.length + 1).padStart(3, "0")}`;
      const patientId = (result as Record<string, unknown>).patient_id as string || twinId;
      const healthScore = (result as Record<string, unknown>).overall_health_score as number ?? 0.75;
      const conditions = (result as Record<string, unknown>).active_conditions as string[] ?? [];

      const newTwin: Twin = {
        id: twinId,
        patient: `Patient ${patientId.slice(0, 8)}`,
        age: 0,
        conditions,
        healthScore,
        lastUpdated: new Date().toISOString(),
        trajectory: "stable",
        vitals: { hr: 72, bp: "120/80", bmi: 25.0, hba1c: 5.4, egfr: 90 },
        bodySystems: DEMO_BODY_SYSTEMS.map((s) => ({ ...s, state: "stable" as const })),
        medications: [],
        stateTimeline: [],
      };
      setTwins((prev) => [...prev, newTwin]);
      setSelectedTwin(newTwin);
    } catch {
      const newTwin: Twin = {
        id: `DT-${String(twins.length + 1).padStart(3, "0")}`,
        patient: "New Patient",
        age: 0,
        conditions: [],
        healthScore: 0.75,
        lastUpdated: new Date().toISOString(),
        trajectory: "stable",
        vitals: { hr: 72, bp: "120/80", bmi: 25.0, hba1c: 5.4, egfr: 90 },
        bodySystems: DEMO_BODY_SYSTEMS.map((s) => ({ ...s, state: "stable" as const })),
        medications: [],
        stateTimeline: [],
      };
      setTwins((prev) => [...prev, newTwin]);
      setSelectedTwin(newTwin);
    } finally {
      setBuilding(false);
    }
  }, [twins.length]);

  const handleFetchState = useCallback(async (twin: Twin) => {
    try {
      await fetchTwinState(twin.id);
    } catch {
      // demo mode — data already loaded
    }
    setSelectedTwin(twin);
  }, []);

  const handleRunSimulation = useCallback(async () => {
    setSimRunning(true);
    setSimResults(null);
    try {
      await simulateScenario({
        patient_id: selectedTwin.id,
        scenario_type: scenarioType,
        parameters: simForm,
      });
    } catch {
      // fallback to demo
    }
    // Always show demo results as fallback
    setTimeout(() => {
      setSimResults(DEMO_SIMULATION_RESULTS);
      setSimRunning(false);
    }, 1200);
  }, [selectedTwin.id, scenarioType, simForm]);

  const handleForecast = useCallback(async () => {
    setForecasting(true);
    setForecastResults(null);
    setForecastAlerts([]);
    try {
      await predictTrajectory({
        patient_id: selectedTwin.id,
        condition: forecastCondition || undefined,
        horizon_months: 24,
      });
    } catch {
      // fallback to demo
    }
    setTimeout(() => {
      setForecastResults(DEMO_FORECAST_MILESTONES);
      const alerts: string[] = [];
      if (selectedTwin.vitals.egfr < 50) alerts.push("Renal function trending toward Stage 4 CKD within 18 months without intervention.");
      if (selectedTwin.vitals.hba1c > 7.0) alerts.push("Glycemic control suboptimal. Risk of microvascular complications increases at 12-month horizon.");
      if (parseInt(selectedTwin.vitals.bp) > 140) alerts.push("Sustained hypertension detected. Cardiovascular event risk elevated over 24-month forecast.");
      if (alerts.length === 0) alerts.push("No critical deterioration patterns detected in the forecast window.");
      setForecastAlerts(alerts);
      setForecasting(false);
    }, 1500);
  }, [selectedTwin, forecastCondition]);

  const handleOptimize = useCallback(async () => {
    setOptimizing(true);
    setTreatmentRecs(null);
    try {
      await recommendTreatment({
        patient_id: selectedTwin.id,
        current_medications: selectedTwin.medications,
        conditions: selectedTwin.conditions,
      });
    } catch {
      // fallback to demo
    }
    setTimeout(() => {
      setTreatmentRecs(DEMO_TREATMENT_RECS);
      setOptimizing(false);
    }, 1800);
  }, [selectedTwin]);

  /* ── Stats ────────────────────────────────────────────────────────────────── */

  const stats = [
    { label: "Active Twins", value: twins.length.toString(), icon: "\u{1F9EC}" },
    { label: "Simulations Run", value: "147", icon: "\u{1F52C}" },
    { label: "Plans Optimized", value: "83", icon: "\u{1F4CA}" },
    { label: "Avg Accuracy", value: "91.4%", icon: "\u{1F3AF}" },
    { label: "Active Forecasts", value: "24", icon: "\u{1F52E}" },
  ];

  const traj = trajectoryArrow(selectedTwin.trajectory);

  /* ── Render ───────────────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Digital Twin & Simulation</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Patient digital twins, what-if scenarios, predictive trajectories & treatment optimization
            </p>
          </div>
          <span className="flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
            </span>
            {twins.length} Active Twins
          </span>
        </div>
        <button
          onClick={handleBuildTwin}
          disabled={building}
          className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 disabled:opacity-50 transition-colors"
        >
          {building ? "Building..." : "+ Build Twin"}
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {stats.map((s, i) => (
          <div key={s.label} className="card card-hover text-center animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>
            <div className="text-lg">{s.icon}</div>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{s.value}</p>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-1 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm" : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ─── Tab: Twin Overview ─────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Patient selector */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Select Patient Twin</h2>
              <button
                onClick={handleBuildTwin}
                disabled={building}
                className="rounded border border-healthos-300 bg-healthos-50 px-3 py-1.5 text-xs font-medium text-healthos-700 hover:bg-healthos-100 disabled:opacity-50"
              >
                {building ? "Building..." : "+ Build Twin"}
              </button>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {twins.map((twin) => (
                <button
                  key={twin.id}
                  onClick={() => handleFetchState(twin)}
                  className={`rounded-lg border-2 p-3 text-left transition-all ${
                    selectedTwin.id === twin.id
                      ? "border-healthos-500 bg-healthos-50 shadow-md"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{twin.patient}</span>
                    <span className={`text-sm font-bold ${scoreColor(twin.healthScore)}`}>
                      {(twin.healthScore * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">Age {twin.age} | {twin.id}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {twin.conditions.slice(0, 2).map((c) => (
                      <span key={c} className="rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[11px] text-gray-600 dark:text-gray-400">{c}</span>
                    ))}
                    {twin.conditions.length > 2 && (
                      <span className="rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[11px] text-gray-500 dark:text-gray-400">
                        +{twin.conditions.length - 2}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Overall health trajectory */}
          <div className="card card-hover">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{selectedTwin.patient}</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400">{selectedTwin.id} | Age {selectedTwin.age} | Updated {formatTimestamp(selectedTwin.lastUpdated)}</p>
              </div>
              <div className="flex items-center gap-3">
                <div className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${traj.color} bg-opacity-10`}>
                  <span className="text-lg">{traj.symbol}</span>
                  {traj.label}
                </div>
                <div className={`text-xl sm:text-3xl font-bold ${scoreColor(selectedTwin.healthScore)}`}>
                  {(selectedTwin.healthScore * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>

          {/* Body System Dashboard */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Body System Dashboard</h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {selectedTwin.bodySystems.map((sys, i) => (
                <div
                  key={sys.name}
                  className={`card card-hover border-l-4 animate-fade-in-up ${stateColor(sys.state)}`}
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{sys.icon}</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{sys.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2.5 w-2.5 rounded-full ${stateDot(sys.state)}`} />
                      <span className="text-xs font-medium capitalize">{sys.state}</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    {sys.metrics.map((m) => (
                      <div key={m.label} className="flex justify-between text-xs">
                        <span className="text-gray-500 dark:text-gray-400">{m.label}</span>
                        <span className="font-medium text-gray-800 dark:text-gray-200">{m.value}</span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 text-[11px] text-gray-500 dark:text-gray-400">Updated {formatTimestamp(sys.lastUpdated)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* State Change Timeline */}
          <div className="card">
            <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Recent State Changes</h3>
            <div className="space-y-3">
              {selectedTwin.stateTimeline.map((entry, i) => {
                const ci = changeIcon(entry.change);
                return (
                  <div key={i} className="flex items-start gap-3 animate-fade-in-up" style={{ animationDelay: `${i * 40}ms` }}>
                    <div className="flex flex-col items-center">
                      <span className={`text-xs font-bold ${ci.color}`}>{ci.symbol}</span>
                      {i < selectedTwin.stateTimeline.length - 1 && (
                        <div className="mt-1 h-6 w-px bg-gray-200" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{entry.event}</span>
                        <span className="rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[11px] text-gray-500 dark:text-gray-400">{entry.system}</span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{formatTimestamp(entry.date)}</p>
                    </div>
                  </div>
                );
              })}
              {selectedTwin.stateTimeline.length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No state changes recorded yet.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab: Scenario Simulation ──────────────────────────────────────── */}
      {activeTab === "simulation" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Scenario type selector */}
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Scenario Type</h3>
            <div className="flex gap-2">
              {([
                { key: "medication", label: "Medication Change", icon: "\u{1F48A}" },
                { key: "lifestyle", label: "Lifestyle Modification", icon: "\u{1F3C3}" },
                { key: "treatment_stop", label: "Treatment Stop", icon: "\u26D4" },
              ] as const).map((st) => (
                <button
                  key={st.key}
                  onClick={() => { setScenarioType(st.key); setSimForm({}); setSimResults(null); }}
                  className={`flex-1 rounded-lg border-2 p-3 text-center transition-all ${
                    scenarioType === st.key
                      ? "border-healthos-500 bg-healthos-50"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:border-gray-600"
                  }`}
                >
                  <div className="text-xl">{st.icon}</div>
                  <div className="mt-1 text-xs font-medium text-gray-700 dark:text-gray-300">{st.label}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Dynamic form */}
          <div className="card">
            <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-300">Scenario Parameters</h3>
            <p className="mb-2 text-xs text-gray-500 dark:text-gray-400">Patient: <span className="font-medium text-gray-800 dark:text-gray-200">{selectedTwin.patient}</span> ({selectedTwin.id})</p>

            {scenarioType === "medication" && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Drug Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Empagliflozin"
                    value={simForm.drug || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, drug: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Dose</label>
                  <input
                    type="text"
                    placeholder="e.g. 10mg"
                    value={simForm.dose || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, dose: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Duration</label>
                  <input
                    type="text"
                    placeholder="e.g. 6 months"
                    value={simForm.duration || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, duration: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  />
                </div>
              </div>
            )}

            {scenarioType === "lifestyle" && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Physical Activity</label>
                  <select
                    value={simForm.activity || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, activity: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="">Select...</option>
                    <option value="walking_30min">Walking 30 min/day</option>
                    <option value="moderate_45min">Moderate exercise 45 min/day</option>
                    <option value="vigorous_30min">Vigorous exercise 30 min/day</option>
                    <option value="cardiac_rehab">Cardiac rehabilitation program</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Dietary Change</label>
                  <select
                    value={simForm.diet || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, diet: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="">Select...</option>
                    <option value="dash">DASH Diet</option>
                    <option value="mediterranean">Mediterranean Diet</option>
                    <option value="low_carb">Low Carbohydrate</option>
                    <option value="calorie_restriction">Caloric Restriction (-500 kcal)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Sleep Target</label>
                  <select
                    value={simForm.sleep || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, sleep: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="">Select...</option>
                    <option value="7h">7 hours/night</option>
                    <option value="8h">8 hours/night</option>
                    <option value="sleep_hygiene">Sleep hygiene protocol</option>
                    <option value="cpap">CPAP therapy initiation</option>
                  </select>
                </div>
              </div>
            )}

            {scenarioType === "treatment_stop" && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Current Treatment to Stop</label>
                  <select
                    value={simForm.treatment || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, treatment: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="">Select treatment...</option>
                    {selectedTwin.medications.map((m) => (
                      <option key={m.name} value={m.name}>{m.name} {m.dose} {m.frequency}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Reason for Discontinuation</label>
                  <select
                    value={simForm.reason || ""}
                    onChange={(e) => setSimForm((p) => ({ ...p, reason: e.target.value }))}
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                  >
                    <option value="">Select reason...</option>
                    <option value="side_effects">Side effects</option>
                    <option value="cost">Cost / insurance</option>
                    <option value="non_adherence">Patient non-adherence</option>
                    <option value="contraindication">New contraindication</option>
                    <option value="therapeutic_goal">Therapeutic goal reached</option>
                  </select>
                </div>
              </div>
            )}

            <div className="mt-4 flex justify-end">
              <button
                onClick={handleRunSimulation}
                disabled={simRunning}
                className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 disabled:opacity-50 transition-colors"
              >
                {simRunning ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Running Simulation...
                  </span>
                ) : (
                  "Run Simulation"
                )}
              </button>
            </div>
          </div>

          {/* Simulation Results */}
          {simResults && (
            <div className="space-y-4 animate-fade-in-up">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Predicted Outcomes</h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {simResults.map((r, i) => (
                  <div
                    key={r.metric}
                    className="card card-hover animate-fade-in-up"
                    style={{ animationDelay: `${i * 80}ms` }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{r.metric}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                        r.delta < 0 && r.metric !== "10yr CV Risk" ? "bg-red-100 text-red-700" :
                        r.delta > 0 && r.metric !== "10yr CV Risk" ? "bg-green-100 text-green-700" :
                        r.delta < 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                      }`}>
                        {r.delta > 0 ? "+" : ""}{r.delta.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 text-center rounded-lg bg-gray-50 dark:bg-gray-800 p-2">
                        <p className="text-[11px] text-gray-500 dark:text-gray-400 uppercase">Before</p>
                        <p className="text-lg font-bold text-gray-600 dark:text-gray-400">{r.before}</p>
                      </div>
                      <span className="text-gray-500 dark:text-gray-400 text-lg">\u2192</span>
                      <div className="flex-1 text-center rounded-lg bg-healthos-50 p-2">
                        <p className="text-[11px] text-healthos-600 uppercase">After</p>
                        <p className="text-lg font-bold text-healthos-700">{r.after}</p>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="flex justify-between text-[11px] text-gray-500 dark:text-gray-400 mb-1">
                        <span>Confidence</span>
                        <span>{(r.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-800">
                        <div
                          className="h-1.5 rounded-full bg-healthos-500 transition-all duration-700"
                          style={{ width: `${r.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Timeline projection */}
              <div className="card">
                <h4 className="mb-3 text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">Timeline Projection</h4>
                <div className="flex items-center justify-between">
                  {["Baseline", "1 mo", "3 mo", "6 mo", "12 mo"].map((label, i) => (
                    <div key={label} className="flex flex-col items-center flex-1">
                      <div className={`h-3 w-3 rounded-full ${i === 0 ? "bg-gray-400" : "bg-healthos-500"}`} />
                      {i < 4 && <div className="w-full h-0.5 bg-gray-200 mt-1.5" />}
                      <span className="mt-2 text-[11px] font-medium text-gray-600 dark:text-gray-400">{label}</span>
                      <span className="text-xs font-bold text-gray-900 dark:text-gray-100">
                        {[62, 64, 67, 70, 71][i]}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── Tab: Trajectory Forecasting ───────────────────────────────────── */}
      {activeTab === "forecasting" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Controls */}
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Forecast Configuration</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Patient</label>
                <select
                  value={selectedTwin.id}
                  onChange={(e) => {
                    const twin = twins.find((t) => t.id === e.target.value);
                    if (twin) setSelectedTwin(twin);
                    setForecastResults(null);
                  }}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  {twins.map((t) => (
                    <option key={t.id} value={t.id}>{t.patient} ({t.id})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Condition Focus</label>
                <select
                  value={forecastCondition}
                  onChange={(e) => setForecastCondition(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  <option value="">All conditions</option>
                  {selectedTwin.conditions.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleForecast}
                  disabled={forecasting}
                  className="w-full rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 disabled:opacity-50 transition-colors"
                >
                  {forecasting ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Forecasting...
                    </span>
                  ) : (
                    "Forecast"
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Forecast Results */}
          {forecastResults && (
            <>
              {/* Milestone Timeline */}
              <div className="card animate-fade-in-up">
                <h3 className="mb-6 text-sm font-semibold text-gray-700 dark:text-gray-300">Progression Timeline</h3>
                <div className="relative">
                  {/* Connection line */}
                  <div className="absolute top-6 left-0 right-0 h-0.5 bg-gray-200 mx-8" />
                  <div className="flex justify-between relative">
                    {forecastResults.map((ms, i) => (
                      <div
                        key={ms.label}
                        className="flex flex-col items-center flex-1 animate-fade-in-up"
                        style={{ animationDelay: `${i * 100}ms` }}
                      >
                        {/* Node */}
                        <div className={`relative z-10 flex h-12 w-12 items-center justify-center rounded-full border-2 bg-white dark:bg-gray-900 ${
                          i === 0 ? "border-gray-400" : ms.riskLevel === "low" ? "border-green-400" : ms.riskLevel === "moderate" ? "border-yellow-400" : "border-red-400"
                        }`}>
                          <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{ms.healthScore}%</span>
                        </div>
                        <span className="mt-2 text-xs font-semibold text-gray-700 dark:text-gray-300">{ms.label}</span>
                        {/* Confidence range */}
                        <span className="text-[11px] text-gray-500 dark:text-gray-400">{ms.confidence[0]}-{ms.confidence[1]}%</span>
                        {/* Risk badge */}
                        <span className={`mt-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${riskColor(ms.riskLevel)}`}>
                          {ms.riskLevel}
                        </span>
                        {/* Key predictions */}
                        <div className="mt-2 space-y-0.5">
                          {ms.keyValues.map((kv) => (
                            <div key={kv.label} className="text-[11px] text-gray-500 dark:text-gray-400">
                              <span className="font-medium">{kv.label}:</span> {kv.predicted}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Deterioration Alerts */}
              <div className="card animate-fade-in-up" style={{ animationDelay: "200ms" }}>
                <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Deterioration Detection & Early Warnings</h3>
                <div className="space-y-2">
                  {forecastAlerts.map((alert, i) => {
                    const isWarning = !alert.includes("No critical");
                    return (
                      <div
                        key={i}
                        className={`flex items-start gap-3 rounded-lg border p-3 ${
                          isWarning ? "border-orange-200 bg-orange-50" : "border-green-200 bg-green-50"
                        }`}
                      >
                        <span className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-white ${
                          isWarning ? "bg-orange-500" : "bg-green-500"
                        }`}>
                          {isWarning ? "!" : "\u2713"}
                        </span>
                        <p className={`text-sm ${isWarning ? "text-orange-800" : "text-green-800"}`}>{alert}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {!forecastResults && !forecasting && (
            <div className="card text-center py-6 sm:py-12">
              <div className="text-2xl sm:text-4xl mb-3 opacity-30">{"\uD83D\uDD2E"}</div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Select a patient and click Forecast to generate trajectory predictions.</p>
            </div>
          )}
        </div>
      )}

      {/* ─── Tab: Treatment Optimization ───────────────────────────────────── */}
      {activeTab === "optimization" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Current treatment plan */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Current Treatment Plan</h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">{selectedTwin.patient} ({selectedTwin.id})</p>
              </div>
              <button
                onClick={handleOptimize}
                disabled={optimizing}
                className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-healthos-700 disabled:opacity-50 transition-colors"
              >
                {optimizing ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Optimizing...
                  </span>
                ) : (
                  "Optimize"
                )}
              </button>
            </div>
            {/* Medications */}
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {selectedTwin.medications.map((med) => (
                <div key={med.name} className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-healthos-100 text-healthos-700 text-xs font-bold">
                    Rx
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{med.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{med.dose} | {med.frequency}</p>
                  </div>
                </div>
              ))}
              {selectedTwin.medications.length === 0 && (
                <p className="col-span-full text-sm text-gray-500 dark:text-gray-400 text-center py-4">No medications on file.</p>
              )}
            </div>
            {/* Conditions */}
            <div className="mt-4 flex flex-wrap gap-2">
              {selectedTwin.conditions.map((c) => (
                <span key={c} className="rounded-lg bg-healthos-50 px-3 py-1.5 text-xs font-medium text-healthos-700">{c}</span>
              ))}
            </div>
          </div>

          {/* Optimization Results */}
          {treatmentRecs && (
            <div className="space-y-4 animate-fade-in-up">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Recommended Changes</h3>
              {treatmentRecs.map((rec, i) => {
                const al = actionLabel(rec.action);
                return (
                  <div
                    key={rec.id}
                    className={`card card-hover border-l-4 ${actionBorder(rec.action)} animate-fade-in-up`}
                    style={{ animationDelay: `${i * 100}ms` }}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className={`rounded px-2 py-0.5 text-[11px] font-bold uppercase ${al.color}`}>{al.text}</span>
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{rec.medication}</span>
                      </div>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${evidenceBadge(rec.evidenceLevel)}`}>
                        Evidence Level {rec.evidenceLevel}
                      </span>
                    </div>

                    {rec.action === "modify" && (
                      <div className="mb-3 flex items-center gap-3 text-sm">
                        <span className="rounded bg-gray-100 dark:bg-gray-800 px-2 py-1 text-gray-600 dark:text-gray-400">{rec.currentDose}</span>
                        <span className="text-gray-500 dark:text-gray-400">\u2192</span>
                        <span className="rounded bg-blue-100 px-2 py-1 font-medium text-blue-700">{rec.recommendedDose}</span>
                      </div>
                    )}

                    <div className="space-y-2">
                      <div>
                        <p className="text-[11px] font-semibold uppercase text-gray-500 dark:text-gray-400 tracking-wide">Rationale</p>
                        <p className="text-sm text-gray-700 dark:text-gray-300">{rec.rationale}</p>
                      </div>
                      <div>
                        <p className="text-[11px] font-semibold uppercase text-gray-500 dark:text-gray-400 tracking-wide">Expected Outcome</p>
                        <p className="text-sm text-gray-700 dark:text-gray-300">{rec.expectedOutcome}</p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center gap-4 pt-3 border-t border-gray-100 dark:border-gray-800">
                      <div className="flex-1">
                        <div className="flex justify-between text-[11px] text-gray-500 dark:text-gray-400 mb-1">
                          <span>Cost-Effectiveness</span>
                          <span>{(rec.costEffectiveness * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-800">
                          <div
                            className={`h-1.5 rounded-full transition-all duration-700 ${
                              rec.costEffectiveness >= 0.8 ? "bg-green-500" : rec.costEffectiveness >= 0.6 ? "bg-yellow-500" : "bg-red-500"
                            }`}
                            style={{ width: `${rec.costEffectiveness * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {!treatmentRecs && !optimizing && (
            <div className="card text-center py-6 sm:py-12">
              <div className="text-2xl sm:text-4xl mb-3 opacity-30">{"\uD83D\uDCCA"}</div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Click Optimize to analyze the current treatment plan and generate AI-powered recommendations.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
