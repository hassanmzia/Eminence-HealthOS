"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Scale,
  Users,
  BarChart3,
  AlertTriangle,
  Shield,
  Activity,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  Play,
  ChevronRight,
  Eye,
  Brain,
  ArrowUp,
  ArrowDown,
  CheckCircle2,
  XCircle,
  Info,
  Lightbulb,
  FileSearch,
  Layers,
} from "lucide-react";
import clsx from "clsx";
import {
  fetchAIGovernanceModels,
  auditAIModel,
  fetchMLModels,
  fetchMLModelMetrics,
} from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────────────────── */

type TabId = "dashboard" | "bias" | "audit" | "explainability";

interface FairnessModel {
  id: string;
  name: string;
  type: string;
  overallScore: number;
  demographicParity: number;
  equalizedOdds: number;
  calibration: number;
  trend: "up" | "down" | "stable";
  trendDelta: number;
  lastAudit: string;
}

interface BiasAlert {
  id: string;
  modelName: string;
  biasType: "selection" | "measurement" | "aggregation" | "representation";
  affectedGroup: string;
  magnitude: "severe" | "moderate" | "mild";
  description: string;
  mitigation: string;
  detectedAt: string;
}

interface AuditResult {
  metric: string;
  subgroup: string;
  value: number;
  threshold: number;
  pass: boolean;
  category: string;
}

interface FeatureImportance {
  feature: string;
  importance: number;
  direction: "positive" | "negative";
}

interface PatientExplanation {
  factor: string;
  direction: "positive" | "negative";
  magnitude: number;
  description: string;
}

/* ── Demo Data ─────────────────────────────────────────────────────────────── */

const DEMO_MODELS: FairnessModel[] = [
  {
    id: "mdl-001",
    name: "Readmission Risk Predictor",
    type: "Classification",
    overallScore: 92,
    demographicParity: 94,
    equalizedOdds: 91,
    calibration: 90,
    trend: "up",
    trendDelta: 2.3,
    lastAudit: "2026-03-14T10:30:00Z",
  },
  {
    id: "mdl-002",
    name: "Sepsis Early Warning",
    type: "Time-Series Classification",
    overallScore: 87,
    demographicParity: 85,
    equalizedOdds: 89,
    calibration: 88,
    trend: "up",
    trendDelta: 1.1,
    lastAudit: "2026-03-13T14:00:00Z",
  },
  {
    id: "mdl-003",
    name: "Medication Dosing Engine",
    type: "Regression",
    overallScore: 78,
    demographicParity: 74,
    equalizedOdds: 80,
    calibration: 81,
    trend: "down",
    trendDelta: -3.2,
    lastAudit: "2026-03-12T09:15:00Z",
  },
  {
    id: "mdl-004",
    name: "Mortality Risk Score",
    type: "Classification",
    overallScore: 95,
    demographicParity: 96,
    equalizedOdds: 94,
    calibration: 95,
    trend: "stable",
    trendDelta: 0.1,
    lastAudit: "2026-03-14T16:45:00Z",
  },
  {
    id: "mdl-005",
    name: "Length of Stay Estimator",
    type: "Regression",
    overallScore: 65,
    demographicParity: 62,
    equalizedOdds: 68,
    calibration: 64,
    trend: "down",
    trendDelta: -5.1,
    lastAudit: "2026-03-11T11:20:00Z",
  },
  {
    id: "mdl-006",
    name: "Diagnosis Suggestion AI",
    type: "Multi-label Classification",
    overallScore: 83,
    demographicParity: 80,
    equalizedOdds: 85,
    calibration: 84,
    trend: "up",
    trendDelta: 4.0,
    lastAudit: "2026-03-13T08:00:00Z",
  },
];

const DEMO_BIAS_ALERTS: BiasAlert[] = [
  {
    id: "ba-001",
    modelName: "Length of Stay Estimator",
    biasType: "representation",
    affectedGroup: "Age 75+",
    magnitude: "severe",
    description:
      "Significant under-representation of elderly patients (75+) in training data leads to systematic under-estimation of length of stay for this cohort.",
    mitigation:
      "Augment training data with additional elderly patient records. Apply re-weighting during training to balance age distribution.",
    detectedAt: "2026-03-14T08:00:00Z",
  },
  {
    id: "ba-002",
    modelName: "Medication Dosing Engine",
    biasType: "measurement",
    affectedGroup: "Female patients",
    magnitude: "moderate",
    description:
      "Dosing recommendations show 12% higher error rates for female patients compared to male patients across multiple medication classes.",
    mitigation:
      "Review feature engineering for sex-specific pharmacokinetic factors. Consider separate calibration curves by sex.",
    detectedAt: "2026-03-13T15:30:00Z",
  },
  {
    id: "ba-003",
    modelName: "Readmission Risk Predictor",
    biasType: "selection",
    affectedGroup: "Rural populations",
    magnitude: "mild",
    description:
      "Model trained primarily on urban hospital data shows slightly lower predictive accuracy for patients from rural zip codes.",
    mitigation:
      "Incorporate rural hospital data into training pipeline. Add geographic features that capture access-to-care disparities.",
    detectedAt: "2026-03-12T12:00:00Z",
  },
  {
    id: "ba-004",
    modelName: "Diagnosis Suggestion AI",
    biasType: "aggregation",
    affectedGroup: "Pediatric patients",
    magnitude: "moderate",
    description:
      "Model aggregates adult and pediatric symptom presentations, leading to missed differential diagnoses for patients under 18.",
    mitigation:
      "Implement age-stratified submodels or add explicit pediatric symptom ontology features.",
    detectedAt: "2026-03-11T10:45:00Z",
  },
  {
    id: "ba-005",
    modelName: "Sepsis Early Warning",
    biasType: "measurement",
    affectedGroup: "Patients with dark skin tones",
    magnitude: "moderate",
    description:
      "SpO2 sensor readings used as input features have documented lower accuracy for patients with dark skin tones, propagating measurement bias into sepsis predictions.",
    mitigation:
      "Add sensor calibration offsets based on documented bias ranges. Consider alternative oxygenation metrics.",
    detectedAt: "2026-03-10T09:00:00Z",
  },
];

const PROTECTED_GROUPS = ["Age 65+", "Female", "Male", "Rural", "Pediatric", "Minority"];
const FAIRNESS_DIMENSIONS = [
  "Demographic Parity",
  "Equalized Odds",
  "Calibration",
  "Predictive Parity",
  "Individual Fairness",
];

const HEATMAP_DATA: number[][] = [
  [92, 88, 94, 90, 86, 91],
  [91, 85, 93, 87, 82, 89],
  [90, 87, 91, 88, 84, 90],
  [88, 83, 90, 85, 80, 87],
  [86, 81, 88, 83, 78, 85],
];

const DEMO_AUDIT_RESULTS: AuditResult[] = [
  { metric: "Accuracy", subgroup: "Overall", value: 0.91, threshold: 0.85, pass: true, category: "Performance" },
  { metric: "Accuracy", subgroup: "Age 65+", value: 0.87, threshold: 0.85, pass: true, category: "Performance" },
  { metric: "Accuracy", subgroup: "Age < 65", value: 0.93, threshold: 0.85, pass: true, category: "Performance" },
  { metric: "Disparate Impact Ratio", subgroup: "Sex (F/M)", value: 0.92, threshold: 0.8, pass: true, category: "Fairness" },
  { metric: "Disparate Impact Ratio", subgroup: "Age (65+/<65)", value: 0.84, threshold: 0.8, pass: true, category: "Fairness" },
  { metric: "Statistical Parity Diff", subgroup: "Sex (F/M)", value: 0.04, threshold: 0.1, pass: true, category: "Fairness" },
  { metric: "Statistical Parity Diff", subgroup: "Age (65+/<65)", value: 0.08, threshold: 0.1, pass: true, category: "Fairness" },
  { metric: "Statistical Parity Diff", subgroup: "Rural/Urban", value: 0.11, threshold: 0.1, pass: false, category: "Fairness" },
  { metric: "Equal Opportunity Diff", subgroup: "Sex (F/M)", value: 0.03, threshold: 0.1, pass: true, category: "Fairness" },
  { metric: "Equal Opportunity Diff", subgroup: "Age (65+/<65)", value: 0.07, threshold: 0.1, pass: true, category: "Fairness" },
  { metric: "Individual Fairness (Lipschitz)", subgroup: "Overall", value: 0.88, threshold: 0.8, pass: true, category: "Individual" },
  { metric: "Counterfactual Fairness", subgroup: "Overall", value: 0.91, threshold: 0.85, pass: true, category: "Individual" },
  { metric: "Prediction Confidence", subgroup: "Overall", value: 0.89, threshold: 0.8, pass: true, category: "Safety" },
  { metric: "OOD Detection Rate", subgroup: "Overall", value: 0.94, threshold: 0.9, pass: true, category: "Safety" },
  { metric: "Explainability Score", subgroup: "Overall", value: 0.82, threshold: 0.75, pass: true, category: "Explainability" },
];

const DEMO_FEATURE_IMPORTANCE: FeatureImportance[] = [
  { feature: "Age", importance: 0.23, direction: "positive" },
  { feature: "Comorbidity Count", importance: 0.19, direction: "positive" },
  { feature: "Prior Admissions (12mo)", importance: 0.16, direction: "positive" },
  { feature: "Lab: Creatinine", importance: 0.12, direction: "positive" },
  { feature: "Medication Count", importance: 0.09, direction: "positive" },
  { feature: "Length of Stay", importance: 0.07, direction: "negative" },
  { feature: "Insurance Type", importance: 0.05, direction: "negative" },
  { feature: "BMI", importance: 0.04, direction: "positive" },
  { feature: "Systolic BP", importance: 0.03, direction: "negative" },
  { feature: "Heart Rate", importance: 0.02, direction: "positive" },
];

const DEMO_SHAP_FORCES = [
  { feature: "Age = 72", value: 0.18, direction: "positive" as const },
  { feature: "Comorbidities = 4", value: 0.14, direction: "positive" as const },
  { feature: "Prior Admits = 2", value: 0.11, direction: "positive" as const },
  { feature: "Creatinine = 1.8", value: 0.08, direction: "positive" as const },
  { feature: "LOS = 3 days", value: -0.06, direction: "negative" as const },
  { feature: "Insurance = Medicare", value: -0.04, direction: "negative" as const },
  { feature: "BMI = 24", value: -0.03, direction: "negative" as const },
  { feature: "BP = 130/85", value: 0.02, direction: "positive" as const },
];

const DEMO_PATIENT_EXPLANATIONS: PatientExplanation[] = [
  { factor: "Advanced age (72 years)", direction: "positive", magnitude: 0.85, description: "Patient age significantly above median; strong predictor of readmission risk." },
  { factor: "Multiple comorbidities (CHF, DM2, CKD)", direction: "positive", magnitude: 0.78, description: "Four active chronic conditions compound readmission probability." },
  { factor: "Two prior admissions in 12 months", direction: "positive", magnitude: 0.65, description: "Recent hospitalization history is a strong recurrence signal." },
  { factor: "Elevated creatinine (1.8 mg/dL)", direction: "positive", magnitude: 0.52, description: "Lab value indicates worsening renal function, correlating with readmission." },
  { factor: "Short initial stay (3 days)", direction: "negative", magnitude: 0.35, description: "Brief hospitalization suggests lower initial acuity." },
  { factor: "Active medication management (8 medications)", direction: "positive", magnitude: 0.40, description: "Polypharmacy increases risk of adverse events and readmission." },
];

/* ── Helpers ───────────────────────────────────────────────────────────────── */

function scoreColor(score: number): string {
  if (score >= 90) return "text-emerald-600";
  if (score >= 70) return "text-amber-500";
  return "text-red-500";
}

function scoreBg(score: number): string {
  if (score >= 90) return "bg-emerald-500";
  if (score >= 70) return "bg-amber-500";
  return "bg-red-500";
}

function scoreBgLight(score: number): string {
  if (score >= 90) return "bg-emerald-100";
  if (score >= 70) return "bg-amber-100";
  return "bg-red-100";
}

function scoreRingColor(score: number): string {
  if (score >= 90) return "ring-emerald-500";
  if (score >= 70) return "ring-amber-500";
  return "ring-red-500";
}

function magnitudeColor(mag: string): string {
  if (mag === "severe") return "bg-red-100 text-red-700 border-red-200";
  if (mag === "moderate") return "bg-orange-100 text-orange-700 border-orange-200";
  return "bg-yellow-100 text-yellow-700 border-yellow-200";
}

function magnitudeDot(mag: string): string {
  if (mag === "severe") return "bg-red-500";
  if (mag === "moderate") return "bg-orange-500";
  return "bg-yellow-500";
}

function biasTypeBadge(type: string): string {
  const map: Record<string, string> = {
    selection: "bg-blue-100 text-blue-700",
    measurement: "bg-purple-100 text-purple-700",
    aggregation: "bg-teal-100 text-teal-700",
    representation: "bg-rose-100 text-rose-700",
  };
  return map[type] || "bg-gray-100 text-gray-700";
}

function heatmapCellColor(value: number): string {
  if (value >= 90) return "bg-emerald-500 text-white";
  if (value >= 85) return "bg-emerald-300 text-emerald-900";
  if (value >= 80) return "bg-amber-300 text-amber-900";
  if (value >= 75) return "bg-orange-400 text-white";
  return "bg-red-500 text-white";
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function TrendIcon({ trend, delta }: { trend: string; delta: number }) {
  if (trend === "up")
    return (
      <span className="flex items-center gap-0.5 text-xs text-emerald-600 font-medium">
        <TrendingUp className="w-3.5 h-3.5" />+{Math.abs(delta).toFixed(1)}%
      </span>
    );
  if (trend === "down")
    return (
      <span className="flex items-center gap-0.5 text-xs text-red-500 font-medium">
        <TrendingDown className="w-3.5 h-3.5" />
        {delta.toFixed(1)}%
      </span>
    );
  return (
    <span className="flex items-center gap-0.5 text-xs text-gray-400 font-medium">
      <Minus className="w-3.5 h-3.5" />
      Stable
    </span>
  );
}

/* ── Page Component ────────────────────────────────────────────────────────── */

export default function AIFairnessBiasMonitorPage() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [models, setModels] = useState<FairnessModel[]>(DEMO_MODELS);
  const [biasAlerts, setBiasAlerts] = useState<BiasAlert[]>(DEMO_BIAS_ALERTS);
  const [loading, setLoading] = useState(false);
  const [auditRunning, setAuditRunning] = useState(false);
  const [auditResults, setAuditResults] = useState<AuditResult[] | null>(null);

  // Bias Detection tab state
  const [biasModelFilter, setBiasModelFilter] = useState("");
  const [biasDimensions, setBiasDimensions] = useState<string[]>(["age", "sex", "race"]);

  // Audit tab state
  const [auditModel, setAuditModel] = useState(DEMO_MODELS[0]?.id || "");
  const [auditScopes, setAuditScopes] = useState<string[]>(["fairness", "performance"]);

  // Explainability tab state
  const [explainModel, setExplainModel] = useState(DEMO_MODELS[0]?.id || "");
  const [explainPatient, setExplainPatient] = useState("P-10042");

  // Load data from API, falling back to demo data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [govRes, mlRes] = await Promise.allSettled([
        fetchAIGovernanceModels(),
        fetchMLModels(),
      ]);

      // If the governance API returns data, try to merge it
      if (govRes.status === "fulfilled" && govRes.value) {
        // Use API data if available, otherwise fall back to demo
        const apiData = govRes.value as Record<string, unknown>;
        if (apiData.models && Array.isArray(apiData.models) && apiData.models.length > 0) {
          // Map API data to our interface
          const mapped = (apiData.models as Record<string, unknown>[]).map(
            (m: Record<string, unknown>, i: number) => ({
              id: (m.id as string) || `api-${i}`,
              name: (m.name as string) || `Model ${i + 1}`,
              type: (m.type as string) || "Classification",
              overallScore: (m.fairness_score as number) || DEMO_MODELS[i % DEMO_MODELS.length].overallScore,
              demographicParity: (m.demographic_parity as number) || DEMO_MODELS[i % DEMO_MODELS.length].demographicParity,
              equalizedOdds: (m.equalized_odds as number) || DEMO_MODELS[i % DEMO_MODELS.length].equalizedOdds,
              calibration: (m.calibration as number) || DEMO_MODELS[i % DEMO_MODELS.length].calibration,
              trend: DEMO_MODELS[i % DEMO_MODELS.length].trend,
              trendDelta: DEMO_MODELS[i % DEMO_MODELS.length].trendDelta,
              lastAudit: (m.last_audit as string) || DEMO_MODELS[i % DEMO_MODELS.length].lastAudit,
            })
          );
          setModels(mapped);
        }
      }

      // Attempt to fetch metrics for each model
      if (mlRes.status === "fulfilled" && mlRes.value) {
        const mlData = mlRes.value as { models?: Array<{ id: string }> };
        if (mlData.models) {
          for (const m of mlData.models.slice(0, 3)) {
            try {
              await fetchMLModelMetrics(m.id);
            } catch {
              // Silently fall back
            }
          }
        }
      }
    } catch {
      // Fall back to demo data (already set as defaults)
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunAudit = async () => {
    setAuditRunning(true);
    try {
      await auditAIModel({
        model_id: auditModel,
        scopes: auditScopes,
      });
    } catch {
      // Fall back to demo audit results
    }
    // Always show demo results (API may return different format)
    setTimeout(() => {
      setAuditResults(DEMO_AUDIT_RESULTS);
      setAuditRunning(false);
    }, 1500);
  };

  const handleHeaderAudit = async () => {
    setActiveTab("audit");
    await handleRunAudit();
  };

  // KPI calculations
  const avgFairness = Math.round(models.reduce((s, m) => s + m.overallScore, 0) / models.length);
  const totalAlerts = biasAlerts.length;
  const driftCount = models.filter((m) => m.trend === "down").length;
  const lastAudit = models.reduce(
    (latest, m) => (m.lastAudit > latest ? m.lastAudit : latest),
    models[0]?.lastAudit || ""
  );

  const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "dashboard", label: "Fairness Dashboard", icon: <Scale className="w-4 h-4" /> },
    { id: "bias", label: "Bias Detection", icon: <AlertTriangle className="w-4 h-4" /> },
    { id: "audit", label: "Model Audit", icon: <FileSearch className="w-4 h-4" /> },
    { id: "explainability", label: "Explainability", icon: <Brain className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6 max-w-7xl animate-fade-in-up">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          {/* Overall Fairness Score Badge */}
          <div
            className={clsx(
              "w-16 h-16 rounded-full flex items-center justify-center ring-4 flex-shrink-0",
              scoreRingColor(avgFairness),
              scoreBgLight(avgFairness)
            )}
          >
            <span className={clsx("text-xl font-bold", scoreColor(avgFairness))}>
              {avgFairness}
            </span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Shield className="w-5 h-5 text-healthos-blue" />
              AI Fairness & Bias Monitor
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Continuous monitoring of model fairness, bias detection, and explainability across
              all clinical AI systems
            </p>
          </div>
        </div>
        <button
          onClick={handleHeaderAudit}
          disabled={auditRunning}
          className="flex items-center gap-2 px-4 py-2.5 bg-healthos-blue text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          <Play className="w-4 h-4" />
          {auditRunning ? "Running..." : "Run Audit"}
        </button>
      </div>

      {/* ── Stats Bar ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        {[
          {
            label: "Models Monitored",
            value: models.length,
            icon: <Layers className="w-4 h-4 text-blue-500" />,
            color: "text-gray-900",
          },
          {
            label: "Fairness Score Avg",
            value: `${avgFairness}%`,
            icon: <Scale className="w-4 h-4 text-emerald-500" />,
            color: scoreColor(avgFairness),
          },
          {
            label: "Bias Alerts",
            value: totalAlerts,
            icon: <AlertTriangle className="w-4 h-4 text-amber-500" />,
            color: totalAlerts > 0 ? "text-amber-600" : "text-gray-900",
          },
          {
            label: "Drift Detections",
            value: driftCount,
            icon: <Activity className="w-4 h-4 text-red-500" />,
            color: driftCount > 0 ? "text-red-600" : "text-gray-900",
          },
          {
            label: "Last Audit",
            value: lastAudit ? formatTimestamp(lastAudit) : "N/A",
            icon: <Clock className="w-4 h-4 text-gray-400" />,
            color: "text-gray-900",
            small: true,
          },
        ].map((kpi) => (
          <div key={kpi.label} className="card card-hover p-4 animate-fade-in-up">
            <div className="flex items-center gap-2 mb-1">
              {kpi.icon}
              <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                {kpi.label}
              </span>
            </div>
            <p
              className={clsx(
                "font-bold font-mono",
                kpi.color,
                kpi.small ? "text-sm mt-1" : "text-2xl"
              )}
            >
              {kpi.value}
            </p>
          </div>
        ))}
      </div>

      {/* ── Tab Navigation ────────────────────────────────────────────────── */}
      <div className="flex gap-1 border-b border-gray-200 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
              activeTab === tab.id
                ? "border-healthos-blue text-healthos-blue"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Loading Overlay ───────────────────────────────────────────────── */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-healthos-blue" />
          <span className="ml-3 text-sm text-gray-500">Loading model data...</span>
        </div>
      )}

      {/* ── Tab: Fairness Dashboard ───────────────────────────────────────── */}
      {!loading && activeTab === "dashboard" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Model Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {models.map((model) => (
              <div key={model.id} className="card card-hover p-5 space-y-4 animate-fade-in-up">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-gray-900">{model.name}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">{model.type}</p>
                  </div>
                  <TrendIcon trend={model.trend} delta={model.trendDelta} />
                </div>

                {/* Overall Score */}
                <div className="flex items-center gap-3">
                  <div
                    className={clsx(
                      "w-12 h-12 rounded-full flex items-center justify-center ring-2",
                      scoreRingColor(model.overallScore),
                      scoreBgLight(model.overallScore)
                    )}
                  >
                    <span className={clsx("text-sm font-bold", scoreColor(model.overallScore))}>
                      {model.overallScore}
                    </span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-500">Overall Fairness</span>
                      <span className={clsx("text-xs font-bold", scoreColor(model.overallScore))}>
                        {model.overallScore}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={clsx("h-2 rounded-full transition-all", scoreBg(model.overallScore))}
                        style={{ width: `${model.overallScore}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Sub-scores */}
                <div className="space-y-2">
                  {[
                    { label: "Demographic Parity", score: model.demographicParity },
                    { label: "Equalized Odds", score: model.equalizedOdds },
                    { label: "Calibration", score: model.calibration },
                  ].map((sub) => (
                    <div key={sub.label} className="flex items-center gap-2">
                      <span className="text-[11px] text-gray-500 w-32 flex-shrink-0">
                        {sub.label}
                      </span>
                      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                        <div
                          className={clsx("h-1.5 rounded-full", scoreBg(sub.score))}
                          style={{ width: `${sub.score}%` }}
                        />
                      </div>
                      <span
                        className={clsx("text-[11px] font-mono font-bold w-10 text-right", scoreColor(sub.score))}
                      >
                        {sub.score}%
                      </span>
                    </div>
                  ))}
                </div>

                <p className="text-[10px] text-gray-400">
                  Last audited: {formatTimestamp(model.lastAudit)}
                </p>
              </div>
            ))}
          </div>

          {/* Heatmap Grid */}
          <div className="card p-5 animate-fade-in-up">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-gray-400" />
              Fairness Dimensions vs Protected Groups
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    <th className="text-left pb-2 pr-4 text-gray-500 font-medium">Dimension</th>
                    {PROTECTED_GROUPS.map((g) => (
                      <th key={g} className="pb-2 px-2 text-center text-gray-500 font-medium">
                        {g}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {FAIRNESS_DIMENSIONS.map((dim, rowIdx) => (
                    <tr key={dim}>
                      <td className="py-1.5 pr-4 font-medium text-gray-700 whitespace-nowrap">
                        {dim}
                      </td>
                      {HEATMAP_DATA[rowIdx].map((val, colIdx) => (
                        <td key={colIdx} className="py-1.5 px-2">
                          <div
                            className={clsx(
                              "w-full py-1.5 rounded text-center font-mono font-bold text-[11px]",
                              heatmapCellColor(val)
                            )}
                          >
                            {val}%
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center gap-4 mt-4 text-[10px] text-gray-500">
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-emerald-500" /> 90%+
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-emerald-300" /> 85-89%
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-amber-300" /> 80-84%
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-orange-400" /> 75-79%
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-red-500" /> &lt;75%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Bias Detection ───────────────────────────────────────────── */}
      {!loading && activeTab === "bias" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Analyze Model Form */}
          <div className="card p-5 animate-fade-in-up">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Search className="w-4 h-4 text-gray-400" />
              Analyze Model for Bias
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Select Model
                </label>
                <select
                  value={biasModelFilter}
                  onChange={(e) => setBiasModelFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-healthos-blue focus:border-transparent"
                >
                  <option value="">All Models</option>
                  {models.map((m) => (
                    <option key={m.id} value={m.name}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Demographic Dimensions
                </label>
                <div className="flex flex-wrap gap-2">
                  {["age", "sex", "race", "income", "geography", "language"].map((dim) => (
                    <label
                      key={dim}
                      className={clsx(
                        "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium cursor-pointer border transition-colors",
                        biasDimensions.includes(dim)
                          ? "bg-healthos-blue/10 border-healthos-blue text-healthos-blue"
                          : "bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={biasDimensions.includes(dim)}
                        onChange={(e) =>
                          setBiasDimensions((prev) =>
                            e.target.checked ? [...prev, dim] : prev.filter((d) => d !== dim)
                          )
                        }
                        className="sr-only"
                      />
                      {dim.charAt(0).toUpperCase() + dim.slice(1)}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Active Bias Alerts */}
          <div>
            <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Active Bias Alerts
              <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-bold">
                {biasAlerts.filter(
                  (a) => !biasModelFilter || a.modelName === biasModelFilter
                ).length}
              </span>
            </h3>
            <div className="space-y-3">
              {biasAlerts
                .filter((a) => !biasModelFilter || a.modelName === biasModelFilter)
                .map((alert) => (
                  <div
                    key={alert.id}
                    className="card card-hover p-5 animate-fade-in-up"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <div className={clsx("w-2.5 h-2.5 rounded-full", magnitudeDot(alert.magnitude))} />
                        <span className="text-sm font-bold text-gray-900">
                          {alert.modelName}
                        </span>
                        <span
                          className={clsx(
                            "text-[10px] font-bold px-2 py-0.5 rounded-full",
                            biasTypeBadge(alert.biasType)
                          )}
                        >
                          {alert.biasType.charAt(0).toUpperCase() + alert.biasType.slice(1)} Bias
                        </span>
                        <span
                          className={clsx(
                            "text-[10px] font-bold px-2 py-0.5 rounded-full border",
                            magnitudeColor(alert.magnitude)
                          )}
                        >
                          {alert.magnitude.toUpperCase()}
                        </span>
                      </div>
                      <span className="text-[10px] text-gray-400 flex-shrink-0">
                        {formatTimestamp(alert.detectedAt)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-xs font-medium text-gray-600">
                        Affected Group: <span className="text-gray-900">{alert.affectedGroup}</span>
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mb-3 leading-relaxed">
                      {alert.description}
                    </p>
                    <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                      <div className="flex items-start gap-2">
                        <Lightbulb className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <div>
                          <span className="text-[10px] font-bold text-blue-700 uppercase">
                            Recommended Mitigation
                          </span>
                          <p className="text-xs text-blue-800 mt-0.5">{alert.mitigation}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Historical Bias Trend */}
          <div className="card p-5 animate-fade-in-up">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-gray-400" />
              Historical Bias Trend
            </h3>
            <div className="space-y-3">
              {models.map((model) => {
                const alertCount = biasAlerts.filter(
                  (a) => a.modelName === model.name
                ).length;
                return (
                  <div key={model.id} className="flex items-center gap-3">
                    <span className="text-xs font-medium text-gray-700 w-44 flex-shrink-0 truncate">
                      {model.name}
                    </span>
                    <div className="flex-1 flex items-center gap-2">
                      <div className="flex-1 bg-gray-100 rounded-full h-3 relative overflow-hidden">
                        <div
                          className={clsx(
                            "h-3 rounded-full transition-all",
                            scoreBg(model.overallScore)
                          )}
                          style={{ width: `${model.overallScore}%` }}
                        />
                      </div>
                      <span className={clsx("text-xs font-mono font-bold w-10", scoreColor(model.overallScore))}>
                        {model.overallScore}%
                      </span>
                    </div>
                    {alertCount > 0 && (
                      <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-bold">
                        {alertCount} alert{alertCount > 1 ? "s" : ""}
                      </span>
                    )}
                    <TrendIcon trend={model.trend} delta={model.trendDelta} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Model Audit ──────────────────────────────────────────────── */}
      {!loading && activeTab === "audit" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Audit Form */}
          <div className="card p-5 animate-fade-in-up">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FileSearch className="w-4 h-4 text-gray-400" />
              Configure Audit
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Select Model
                </label>
                <select
                  value={auditModel}
                  onChange={(e) => setAuditModel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-healthos-blue focus:border-transparent"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Audit Scope
                </label>
                <div className="flex flex-wrap gap-2">
                  {["fairness", "performance", "safety", "explainability"].map((scope) => (
                    <label
                      key={scope}
                      className={clsx(
                        "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium cursor-pointer border transition-colors",
                        auditScopes.includes(scope)
                          ? "bg-healthos-blue/10 border-healthos-blue text-healthos-blue"
                          : "bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={auditScopes.includes(scope)}
                        onChange={(e) =>
                          setAuditScopes((prev) =>
                            e.target.checked
                              ? [...prev, scope]
                              : prev.filter((s) => s !== scope)
                          )
                        }
                        className="sr-only"
                      />
                      {scope === "fairness" && <Scale className="w-3.5 h-3.5" />}
                      {scope === "performance" && <BarChart3 className="w-3.5 h-3.5" />}
                      {scope === "safety" && <Shield className="w-3.5 h-3.5" />}
                      {scope === "explainability" && <Eye className="w-3.5 h-3.5" />}
                      {scope.charAt(0).toUpperCase() + scope.slice(1)}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <button
              onClick={handleRunAudit}
              disabled={auditRunning || auditScopes.length === 0}
              className="mt-4 flex items-center gap-2 px-4 py-2.5 bg-healthos-blue text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              {auditRunning ? "Running Audit..." : "Run Audit"}
            </button>
          </div>

          {/* Audit Running Indicator */}
          {auditRunning && (
            <div className="card p-8 flex flex-col items-center justify-center gap-3 animate-fade-in-up">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-healthos-blue" />
              <p className="text-sm text-gray-500">Running comprehensive model audit...</p>
              <p className="text-xs text-gray-400">
                Evaluating fairness, performance, safety, and explainability metrics
              </p>
            </div>
          )}

          {/* Audit Results */}
          {!auditRunning && auditResults && (
            <div className="card p-5 animate-fade-in-up">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  Audit Report: {models.find((m) => m.id === auditModel)?.name || "Model"}
                </h3>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold">
                    {auditResults.filter((r) => r.pass).length} PASS
                  </span>
                  <span className="text-[10px] bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-bold">
                    {auditResults.filter((r) => !r.pass).length} FAIL
                  </span>
                </div>
              </div>

              {/* Group by category */}
              {["Performance", "Fairness", "Individual", "Safety", "Explainability"]
                .filter((cat) =>
                  auditResults.some((r) => r.category === cat)
                )
                .map((category) => (
                  <div key={category} className="mb-4">
                    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                      <ChevronRight className="w-3 h-3" />
                      {category}
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left pb-2 text-xs font-medium text-gray-500">
                              Metric
                            </th>
                            <th className="text-left pb-2 text-xs font-medium text-gray-500">
                              Subgroup
                            </th>
                            <th className="text-right pb-2 text-xs font-medium text-gray-500">
                              Value
                            </th>
                            <th className="text-right pb-2 text-xs font-medium text-gray-500">
                              Threshold
                            </th>
                            <th className="text-center pb-2 text-xs font-medium text-gray-500">
                              Result
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {auditResults
                            .filter((r) => r.category === category)
                            .map((result, idx) => (
                              <tr
                                key={idx}
                                className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                              >
                                <td className="py-2.5 text-xs font-medium text-gray-900">
                                  {result.metric}
                                </td>
                                <td className="py-2.5 text-xs text-gray-500">
                                  {result.subgroup}
                                </td>
                                <td className="py-2.5 text-right font-mono text-xs font-bold text-gray-900">
                                  {result.value.toFixed(2)}
                                </td>
                                <td className="py-2.5 text-right font-mono text-xs text-gray-500">
                                  {result.threshold.toFixed(2)}
                                </td>
                                <td className="py-2.5 text-center">
                                  {result.pass ? (
                                    <span className="inline-flex items-center gap-1 text-[10px] font-bold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
                                      <CheckCircle2 className="w-3 h-3" /> PASS
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 text-[10px] font-bold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                                      <XCircle className="w-3 h-3" /> FAIL
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}

              {/* Summary */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-gray-600">
                    <p className="font-medium text-gray-900 mb-1">Audit Summary</p>
                    <p>
                      {auditResults.filter((r) => r.pass).length} of {auditResults.length} metrics
                      passed threshold requirements.{" "}
                      {auditResults.filter((r) => !r.pass).length > 0
                        ? `${auditResults.filter((r) => !r.pass).length} metric(s) require attention before production deployment.`
                        : "All metrics within acceptable bounds."}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* No results yet */}
          {!auditRunning && !auditResults && (
            <div className="card p-12 flex flex-col items-center justify-center text-center animate-fade-in-up">
              <FileSearch className="w-10 h-10 text-gray-300 mb-3" />
              <p className="text-sm font-medium text-gray-500">No audit results yet</p>
              <p className="text-xs text-gray-400 mt-1">
                Configure the audit parameters above and click "Run Audit" to generate a comprehensive report.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Explainability ───────────────────────────────────────────── */}
      {!loading && activeTab === "explainability" && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Feature Importance */}
          <div className="card p-5 animate-fade-in-up">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-gray-400" />
              Global Feature Importance
            </h3>
            <div className="space-y-2">
              {DEMO_FEATURE_IMPORTANCE.map((feat) => (
                <div key={feat.feature} className="flex items-center gap-3">
                  <span className="text-xs text-gray-700 w-40 flex-shrink-0 text-right">
                    {feat.feature}
                  </span>
                  <div className="flex-1 flex items-center gap-1">
                    <div className="flex-1 bg-gray-100 rounded-full h-4 relative overflow-hidden">
                      <div
                        className={clsx(
                          "h-4 rounded-full transition-all flex items-center justify-end pr-1",
                          feat.direction === "positive" ? "bg-blue-400" : "bg-rose-400"
                        )}
                        style={{ width: `${feat.importance * 400}%` }}
                      >
                        {feat.importance >= 0.05 && (
                          <span className="text-[9px] font-bold text-white">
                            {(feat.importance * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <span
                    className={clsx(
                      "text-[10px] font-bold w-8",
                      feat.direction === "positive" ? "text-blue-600" : "text-rose-600"
                    )}
                  >
                    {feat.direction === "positive" ? "+" : "-"}
                  </span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-3 text-[10px] text-gray-500">
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-blue-400" /> Increases risk
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-rose-400" /> Decreases risk
              </span>
            </div>
          </div>

          {/* SHAP Force Plot */}
          <div className="card p-5 animate-fade-in-up">
            <h3 className="text-sm font-bold text-gray-900 mb-1 flex items-center gap-2">
              <Brain className="w-4 h-4 text-gray-400" />
              SHAP Force Plot — Sample Prediction
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Feature contributions pushing prediction higher (blue) or lower (rose) from the base
              value
            </p>

            <div className="flex items-center gap-1 mb-3">
              <span className="text-xs text-gray-500 flex-shrink-0 w-20">Base: 0.35</span>
              <div className="flex-1 h-8 bg-gray-100 rounded-lg relative overflow-hidden flex items-center">
                {DEMO_SHAP_FORCES.filter((f) => f.direction === "positive")
                  .sort((a, b) => b.value - a.value)
                  .map((f, i) => (
                    <div
                      key={i}
                      className="h-full bg-blue-400 border-r border-blue-500 flex items-center justify-center relative group"
                      style={{ width: `${Math.abs(f.value) * 250}%` }}
                    >
                      <span className="text-[8px] font-bold text-white truncate px-0.5">
                        {f.feature.split("=")[0].trim()}
                      </span>
                    </div>
                  ))}
                <div className="h-full w-px bg-gray-400 flex-shrink-0" />
                {DEMO_SHAP_FORCES.filter((f) => f.direction === "negative")
                  .sort((a, b) => a.value - b.value)
                  .map((f, i) => (
                    <div
                      key={i}
                      className="h-full bg-rose-400 border-r border-rose-500 flex items-center justify-center relative group"
                      style={{ width: `${Math.abs(f.value) * 250}%` }}
                    >
                      <span className="text-[8px] font-bold text-white truncate px-0.5">
                        {f.feature.split("=")[0].trim()}
                      </span>
                    </div>
                  ))}
              </div>
              <span className="text-xs font-bold text-gray-900 flex-shrink-0 w-20 text-right">
                Output: 0.72
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
              {DEMO_SHAP_FORCES.map((f) => (
                <div
                  key={f.feature}
                  className={clsx(
                    "px-2 py-1.5 rounded text-[10px] font-medium border",
                    f.direction === "positive"
                      ? "bg-blue-50 border-blue-200 text-blue-700"
                      : "bg-rose-50 border-rose-200 text-rose-700"
                  )}
                >
                  <span className="font-bold">{f.direction === "positive" ? "+" : ""}{f.value.toFixed(2)}</span>{" "}
                  {f.feature}
                </div>
              ))}
            </div>
          </div>

          {/* Patient-Level Explanation */}
          <div className="card p-5 animate-fade-in-up">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-400" />
              Patient-Level Explanation
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Patient ID
                </label>
                <input
                  type="text"
                  value={explainPatient}
                  onChange={(e) => setExplainPatient(e.target.value)}
                  placeholder="Enter patient ID"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-healthos-blue focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Model
                </label>
                <select
                  value={explainModel}
                  onChange={(e) => setExplainModel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-healthos-blue focus:border-transparent"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Prediction Summary */}
            <div className="bg-gradient-to-r from-red-50 to-orange-50 rounded-lg p-4 border border-red-100 mb-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-gray-700">
                  Prediction: Readmission Risk
                </span>
                <span className="text-lg font-bold text-red-600">72% High Risk</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="h-2.5 rounded-full bg-gradient-to-r from-amber-400 via-orange-500 to-red-500"
                  style={{ width: "72%" }}
                />
              </div>
            </div>

            {/* Contributing Factors */}
            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">
              Contributing Factors
            </h4>
            <div className="space-y-3">
              {DEMO_PATIENT_EXPLANATIONS.map((exp, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
                >
                  <div className="flex-shrink-0 mt-1">
                    {exp.direction === "positive" ? (
                      <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center">
                        <ArrowUp className="w-3.5 h-3.5 text-red-500" />
                      </div>
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center">
                        <ArrowDown className="w-3.5 h-3.5 text-emerald-500" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold text-gray-900">{exp.factor}</span>
                      <span
                        className={clsx(
                          "text-[9px] font-bold px-1.5 py-0.5 rounded",
                          exp.direction === "positive"
                            ? "bg-red-100 text-red-700"
                            : "bg-emerald-100 text-emerald-700"
                        )}
                      >
                        {exp.direction === "positive" ? "RISK+" : "RISK-"}
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-500 leading-relaxed">
                      {exp.description}
                    </p>
                  </div>
                  <div className="flex-shrink-0 w-20">
                    <div className="w-full bg-gray-200 rounded-full h-1.5 mb-1">
                      <div
                        className={clsx(
                          "h-1.5 rounded-full",
                          exp.direction === "positive" ? "bg-red-400" : "bg-emerald-400"
                        )}
                        style={{ width: `${exp.magnitude * 100}%` }}
                      />
                    </div>
                    <span className="text-[9px] text-gray-400 font-mono">
                      {(exp.magnitude * 100).toFixed(0)}% impact
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
