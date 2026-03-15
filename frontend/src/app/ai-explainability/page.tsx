"use client";

import { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";

/* ------------------------------------------------------------------ */
/*  Demo Data                                                          */
/* ------------------------------------------------------------------ */

const models = [
  "Readmission Risk",
  "Sepsis Predictor",
  "Mortality Risk",
  "LOS Predictor",
  "Deterioration Index",
] as const;

type ModelName = (typeof models)[number];

interface ShapFeature {
  feature: string;
  value: number;
}

interface LimeFeature {
  feature: string;
  weight: number;
  currentValue: string;
  toggledValue: string;
}

interface ModelCard {
  purpose: string;
  trainingData: string;
  sampleSize: string;
  auc: number;
  f1: number;
  precision: number;
  recall: number;
  fairness: { group: string; disparity: number }[];
  limitations: string[];
  intendedUse: string;
  lastAudit: string;
}

const shapData: Record<ModelName, ShapFeature[]> = {
  "Readmission Risk": [
    { feature: "Prior Admissions (12mo)", value: 0.38 },
    { feature: "Discharge Disposition", value: 0.31 },
    { feature: "Length of Stay", value: 0.24 },
    { feature: "Charlson Comorbidity Idx", value: 0.21 },
    { feature: "Medication Count", value: 0.17 },
    { feature: "Age", value: 0.14 },
    { feature: "Insurance Type", value: -0.12 },
    { feature: "Follow-up Scheduled", value: -0.22 },
    { feature: "PCP Visit (30d)", value: -0.19 },
    { feature: "Hemoglobin A1c", value: 0.11 },
    { feature: "BNP Level", value: 0.09 },
    { feature: "Ejection Fraction", value: -0.15 },
    { feature: "BMI", value: 0.06 },
    { feature: "Smoking Status", value: 0.08 },
    { feature: "Social Support Score", value: -0.13 },
  ],
  "Sepsis Predictor": [
    { feature: "SIRS Criteria Met", value: 0.45 },
    { feature: "Lactate Level", value: 0.39 },
    { feature: "WBC Count", value: 0.33 },
    { feature: "Temperature", value: 0.28 },
    { feature: "Heart Rate", value: 0.22 },
    { feature: "Respiratory Rate", value: 0.19 },
    { feature: "MAP", value: -0.25 },
    { feature: "Platelet Count", value: -0.18 },
    { feature: "Creatinine", value: 0.16 },
    { feature: "Bilirubin", value: 0.12 },
    { feature: "Glasgow Coma Scale", value: -0.14 },
    { feature: "Procalcitonin", value: 0.35 },
    { feature: "Band Neutrophils", value: 0.2 },
    { feature: "CRP Level", value: 0.26 },
    { feature: "Urine Output", value: -0.17 },
  ],
  "Mortality Risk": [
    { feature: "APACHE II Score", value: 0.42 },
    { feature: "Age", value: 0.29 },
    { feature: "Ventilator Days", value: 0.35 },
    { feature: "Vasopressor Use", value: 0.31 },
    { feature: "GCS Score", value: -0.27 },
    { feature: "Albumin Level", value: -0.22 },
    { feature: "Creatinine", value: 0.18 },
    { feature: "Lactate Clearance", value: -0.24 },
    { feature: "Comorbidity Count", value: 0.2 },
    { feature: "ICU LOS", value: 0.15 },
    { feature: "PaO2/FiO2 Ratio", value: -0.19 },
    { feature: "DNR Status", value: 0.13 },
    { feature: "Surgical Admission", value: -0.1 },
    { feature: "Night Admission", value: 0.07 },
    { feature: "Weekend Admission", value: 0.05 },
  ],
  "LOS Predictor": [
    { feature: "Admission Diagnosis", value: 0.36 },
    { feature: "Procedure Complexity", value: 0.32 },
    { feature: "Comorbidity Index", value: 0.25 },
    { feature: "Age", value: 0.18 },
    { feature: "ED Wait Time", value: 0.14 },
    { feature: "Insurance Auth Delay", value: 0.21 },
    { feature: "Bed Availability", value: -0.11 },
    { feature: "Prior Surgeries", value: 0.16 },
    { feature: "BMI", value: 0.09 },
    { feature: "Functional Status", value: -0.2 },
    { feature: "Discharge Planning", value: -0.26 },
    { feature: "Care Coordination", value: -0.18 },
    { feature: "Social Work Consult", value: -0.08 },
    { feature: "PT/OT Ordered", value: 0.12 },
    { feature: "Antibiotic Course", value: 0.1 },
  ],
  "Deterioration Index": [
    { feature: "NEWS2 Score", value: 0.41 },
    { feature: "Heart Rate Variability", value: -0.29 },
    { feature: "SpO2 Trend", value: -0.34 },
    { feature: "Respiratory Rate", value: 0.27 },
    { feature: "Systolic BP Trend", value: -0.23 },
    { feature: "Urine Output", value: -0.19 },
    { feature: "Mental Status Change", value: 0.32 },
    { feature: "Lactate Trend", value: 0.25 },
    { feature: "WBC Trend", value: 0.15 },
    { feature: "Temperature", value: 0.13 },
    { feature: "Pain Score Trend", value: 0.09 },
    { feature: "Fluid Balance", value: 0.17 },
    { feature: "Time Since Last Vitals", value: 0.11 },
    { feature: "Nurse Concern Flag", value: 0.28 },
    { feature: "Medication Changes", value: 0.08 },
  ],
};

const limeData: Record<ModelName, { probability: number; confidence: [number, number]; features: LimeFeature[] }> = {
  "Readmission Risk": {
    probability: 0.73,
    confidence: [0.68, 0.78],
    features: [
      { feature: "Prior Admissions", weight: 0.18, currentValue: "3", toggledValue: "0" },
      { feature: "Discharge Disposition", weight: 0.14, currentValue: "Home alone", toggledValue: "Home w/ services" },
      { feature: "Follow-up Scheduled", weight: -0.12, currentValue: "No", toggledValue: "Yes" },
      { feature: "Medication Count", weight: 0.1, currentValue: "12", toggledValue: "5" },
      { feature: "Charlson Index", weight: 0.09, currentValue: "6", toggledValue: "2" },
      { feature: "Social Support", weight: -0.07, currentValue: "Low", toggledValue: "High" },
    ],
  },
  "Sepsis Predictor": {
    probability: 0.82,
    confidence: [0.76, 0.88],
    features: [
      { feature: "Lactate Level", weight: 0.22, currentValue: "4.2 mmol/L", toggledValue: "1.0 mmol/L" },
      { feature: "SIRS Criteria", weight: 0.19, currentValue: "3/4", toggledValue: "1/4" },
      { feature: "Procalcitonin", weight: 0.15, currentValue: "8.5 ng/mL", toggledValue: "0.3 ng/mL" },
      { feature: "WBC Count", weight: 0.13, currentValue: "18.2 K", toggledValue: "8.0 K" },
      { feature: "MAP", weight: -0.11, currentValue: "58 mmHg", toggledValue: "75 mmHg" },
      { feature: "Temperature", weight: 0.1, currentValue: "39.2 C", toggledValue: "37.0 C" },
    ],
  },
  "Mortality Risk": {
    probability: 0.45,
    confidence: [0.39, 0.51],
    features: [
      { feature: "APACHE II", weight: 0.2, currentValue: "28", toggledValue: "12" },
      { feature: "Ventilator Days", weight: 0.16, currentValue: "7", toggledValue: "0" },
      { feature: "Albumin", weight: -0.11, currentValue: "2.1 g/dL", toggledValue: "3.8 g/dL" },
      { feature: "Vasopressor Use", weight: 0.14, currentValue: "Yes", toggledValue: "No" },
      { feature: "GCS", weight: -0.09, currentValue: "9", toggledValue: "15" },
      { feature: "Lactate Clearance", weight: -0.08, currentValue: "Low", toggledValue: "High" },
    ],
  },
  "LOS Predictor": {
    probability: 0.68,
    confidence: [0.62, 0.74],
    features: [
      { feature: "Procedure Complexity", weight: 0.17, currentValue: "High", toggledValue: "Low" },
      { feature: "Comorbidity Index", weight: 0.13, currentValue: "5", toggledValue: "1" },
      { feature: "Discharge Planning", weight: -0.14, currentValue: "Pending", toggledValue: "Complete" },
      { feature: "Insurance Auth", weight: 0.1, currentValue: "Delayed", toggledValue: "Approved" },
      { feature: "Functional Status", weight: -0.09, currentValue: "Dependent", toggledValue: "Independent" },
      { feature: "Care Coordination", weight: -0.07, currentValue: "None", toggledValue: "Active" },
    ],
  },
  "Deterioration Index": {
    probability: 0.61,
    confidence: [0.55, 0.67],
    features: [
      { feature: "NEWS2 Score", weight: 0.21, currentValue: "9", toggledValue: "2" },
      { feature: "SpO2 Trend", weight: -0.16, currentValue: "Declining", toggledValue: "Stable" },
      { feature: "Mental Status", weight: 0.14, currentValue: "Changed", toggledValue: "Baseline" },
      { feature: "Nurse Concern", weight: 0.12, currentValue: "Flagged", toggledValue: "None" },
      { feature: "HR Variability", weight: -0.1, currentValue: "Low", toggledValue: "Normal" },
      { feature: "Fluid Balance", weight: 0.08, currentValue: "+2.5L", toggledValue: "Neutral" },
    ],
  },
};

const modelCards: Record<ModelName, ModelCard> = {
  "Readmission Risk": {
    purpose: "Predicts 30-day all-cause hospital readmission risk to enable targeted discharge planning and post-acute care interventions.",
    trainingData: "Electronic health records from 12 hospital sites (2018-2024), including demographics, diagnoses, procedures, labs, and social determinants.",
    sampleSize: "1.2M discharge encounters; 156K readmission events",
    auc: 0.84, f1: 0.76, precision: 0.79, recall: 0.73,
    fairness: [
      { group: "Age 65+", disparity: 0.03 },
      { group: "Black patients", disparity: 0.05 },
      { group: "Medicaid", disparity: 0.07 },
      { group: "Rural zip codes", disparity: 0.04 },
    ],
    limitations: ["Does not account for patient preference or goals of care", "Limited validation in pediatric populations", "Social determinant data may be incomplete in EHR"],
    intendedUse: "Clinical decision support for discharge planning teams. Not intended as sole determinant of care level.",
    lastAudit: "2026-01-15",
  },
  "Sepsis Predictor": {
    purpose: "Early detection of sepsis onset using real-time vital signs and laboratory data to enable rapid intervention.",
    trainingData: "ICU and ED encounter data from the MIMIC-IV dataset supplemented with institutional EHR data (2019-2025).",
    sampleSize: "890K encounters; 72K sepsis events (Sepsis-3 criteria)",
    auc: 0.91, f1: 0.82, precision: 0.85, recall: 0.79,
    fairness: [
      { group: "Age 65+", disparity: 0.02 },
      { group: "Female patients", disparity: 0.03 },
      { group: "Non-English speaking", disparity: 0.06 },
      { group: "Immunocompromised", disparity: 0.04 },
    ],
    limitations: ["Alert fatigue risk with high-sensitivity thresholds", "Performance degrades in post-surgical populations", "Requires minimum 2 hours of continuous vitals data"],
    intendedUse: "Real-time clinical surveillance in ICU and ED settings. Alerts require clinician review before action.",
    lastAudit: "2026-02-20",
  },
  "Mortality Risk": {
    purpose: "Estimates in-hospital mortality risk for ICU patients to support triage, goals-of-care discussions, and resource allocation.",
    trainingData: "Multi-center ICU data from 8 academic medical centers (2017-2024), including APACHE scores, labs, vitals, and treatment data.",
    sampleSize: "540K ICU admissions; 48K mortality events",
    auc: 0.88, f1: 0.74, precision: 0.81, recall: 0.68,
    fairness: [
      { group: "Age 80+", disparity: 0.06 },
      { group: "Hispanic patients", disparity: 0.04 },
      { group: "Uninsured", disparity: 0.08 },
      { group: "Transfer patients", disparity: 0.05 },
    ],
    limitations: ["Not validated for patients under 18", "Calibration drift observed after 6 months without retraining", "Does not incorporate palliative care status"],
    intendedUse: "Support tool for intensivists and palliative care teams. Must not be used to deny or withdraw treatment.",
    lastAudit: "2025-12-10",
  },
  "LOS Predictor": {
    purpose: "Forecasts expected length of stay at admission to optimize bed management, staffing, and discharge planning.",
    trainingData: "Admission records across medical, surgical, and observation units from 6 hospitals (2019-2025).",
    sampleSize: "2.1M admissions with actual LOS outcomes",
    auc: 0.81, f1: 0.72, precision: 0.75, recall: 0.69,
    fairness: [
      { group: "Age 65+", disparity: 0.04 },
      { group: "Black patients", disparity: 0.06 },
      { group: "Dual-eligible", disparity: 0.05 },
      { group: "Non-English speaking", disparity: 0.07 },
    ],
    limitations: ["Accuracy decreases for stays longer than 21 days", "Does not account for staffing-related delays", "Insurance authorization delays not fully captured"],
    intendedUse: "Operational planning tool for bed management and care coordination. Not for patient-facing communication.",
    lastAudit: "2026-01-28",
  },
  "Deterioration Index": {
    purpose: "Continuous monitoring score predicting clinical deterioration within 12 hours to enable rapid response activation.",
    trainingData: "Continuous monitoring data from telemetry and general ward patients across 10 facilities (2020-2025).",
    sampleSize: "3.4M patient-hours; 28K deterioration events (ICU transfer or code blue)",
    auc: 0.87, f1: 0.78, precision: 0.82, recall: 0.74,
    fairness: [
      { group: "Age 75+", disparity: 0.03 },
      { group: "Female patients", disparity: 0.02 },
      { group: "Obesity (BMI 35+)", disparity: 0.05 },
      { group: "Night shift", disparity: 0.04 },
    ],
    limitations: ["Requires continuous vital sign monitoring", "False positive rate increases during ambulation", "Limited validation in psychiatric units"],
    intendedUse: "Automated surveillance tool for nursing staff and rapid response teams. Supplements but does not replace clinical judgment.",
    lastAudit: "2026-02-05",
  },
};

/* Interaction heatmap grid data */
const interactionFeatures = ["Age", "Comorbidity", "Labs", "Vitals", "Meds", "LOS", "Procedures", "Social"];
const interactionMatrix = [
  [1.0, 0.72, 0.45, 0.38, 0.51, 0.62, 0.41, 0.29],
  [0.72, 1.0, 0.58, 0.44, 0.67, 0.55, 0.49, 0.35],
  [0.45, 0.58, 1.0, 0.71, 0.42, 0.36, 0.52, 0.18],
  [0.38, 0.44, 0.71, 1.0, 0.33, 0.29, 0.47, 0.15],
  [0.51, 0.67, 0.42, 0.33, 1.0, 0.48, 0.56, 0.22],
  [0.62, 0.55, 0.36, 0.29, 0.48, 1.0, 0.63, 0.31],
  [0.41, 0.49, 0.52, 0.47, 0.56, 0.63, 1.0, 0.24],
  [0.29, 0.35, 0.18, 0.15, 0.22, 0.31, 0.24, 1.0],
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function heatColor(v: number): string {
  if (v >= 0.8) return "bg-red-600 dark:bg-red-500";
  if (v >= 0.6) return "bg-orange-500 dark:bg-orange-400";
  if (v >= 0.4) return "bg-yellow-400 dark:bg-yellow-500";
  if (v >= 0.2) return "bg-blue-300 dark:bg-blue-400";
  return "bg-blue-100 dark:bg-blue-900";
}

function metricColor(v: number): string {
  if (v >= 0.85) return "text-emerald-600 dark:text-emerald-400";
  if (v >= 0.75) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AIExplainabilityPage() {
  const [selectedModel, setSelectedModel] = useState<ModelName>("Readmission Risk");
  const [activeTab, setActiveTab] = useState<"shap" | "lime" | "cards">("shap");
  const [toggledFeatures, setToggledFeatures] = useState<Set<string>>(new Set());

  const tabs = [
    { key: "shap" as const, label: "SHAP Analysis" },
    { key: "lime" as const, label: "LIME Explanations" },
    { key: "cards" as const, label: "Model Cards" },
  ];

  /* SHAP data sorted by absolute value */
  const sortedShap = useMemo(
    () => [...shapData[selectedModel]].sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
    [selectedModel],
  );

  /* LIME adjusted probability */
  const lime = limeData[selectedModel];
  const adjustedProbability = useMemo(() => {
    let delta = 0;
    lime.features.forEach((f) => {
      if (toggledFeatures.has(f.feature)) delta -= f.weight;
    });
    return Math.min(1, Math.max(0, lime.probability + delta));
  }, [lime, toggledFeatures]);

  const handleToggle = (feature: string) => {
    setToggledFeatures((prev) => {
      const next = new Set(prev);
      if (next.has(feature)) next.delete(feature);
      else next.add(feature);
      return next;
    });
  };

  /* Reset toggles when model changes */
  const handleModelChange = (model: ModelName) => {
    setSelectedModel(model);
    setToggledFeatures(new Set());
  };

  /* SHAP summary stats */
  const shapStats = useMemo(() => {
    const vals = sortedShap.map((d) => d.value);
    const pos = vals.filter((v) => v > 0);
    const neg = vals.filter((v) => v < 0);
    return {
      totalPositive: pos.reduce((s, v) => s + v, 0),
      totalNegative: neg.reduce((s, v) => s + v, 0),
      avgAbsolute: vals.reduce((s, v) => s + Math.abs(v), 0) / vals.length,
      topFeature: sortedShap[0]?.feature ?? "N/A",
    };
  }, [sortedShap]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">AI Explainability</h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            SHAP &amp; LIME explanations for clinical AI model predictions
          </p>
        </div>

        {/* Model selector */}
        <div className="flex items-center gap-3">
          <label htmlFor="model-select" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Model:
          </label>
          <select
            id="model-select"
            value={selectedModel}
            onChange={(e) => handleModelChange(e.target.value as ModelName)}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            {models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-5 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === t.key
                ? "bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border border-b-0 border-gray-200 dark:border-gray-700"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  SHAP Tab                                                        */}
      {/* ---------------------------------------------------------------- */}
      {activeTab === "shap" && (
        <div className="space-y-6">
          {/* Summary stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Top Feature", value: shapStats.topFeature, sub: "Highest absolute SHAP" },
              { label: "Positive Contribution", value: `+${shapStats.totalPositive.toFixed(2)}`, sub: "Sum of risk-increasing" },
              { label: "Negative Contribution", value: shapStats.totalNegative.toFixed(2), sub: "Sum of risk-decreasing" },
              { label: "Avg |SHAP|", value: shapStats.avgAbsolute.toFixed(3), sub: "Mean absolute impact" },
            ].map((s) => (
              <div key={s.label} className="card card-hover p-4">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{s.label}</p>
                <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white truncate">{s.value}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">{s.sub}</p>
              </div>
            ))}
          </div>

          {/* Horizontal bar chart */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Feature Importance &mdash; Top 15 SHAP Values
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              <span className="inline-block w-3 h-3 rounded-sm bg-red-500 mr-1 align-middle" /> Increases risk
              <span className="inline-block w-3 h-3 rounded-sm bg-blue-500 ml-4 mr-1 align-middle" /> Decreases risk
            </p>
            <div className="h-[480px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sortedShap} layout="vertical" margin={{ left: 160, right: 20, top: 5, bottom: 5 }}>
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                  <YAxis
                    type="category"
                    dataKey="feature"
                    width={150}
                    tick={{ fontSize: 12 }}
                    stroke="#9ca3af"
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: "8px", color: "#f9fafb" }}
                    formatter={(val: number) => [val.toFixed(3), "SHAP Value"]}
                  />
                  <Bar
                    dataKey="value"
                    radius={[4, 4, 4, 4]}
                    fill="#3b82f6"
                    isAnimationActive
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    shape={(props: any) => {
                      const { x, y, width, height, value } = props;
                      const color = value >= 0 ? "#ef4444" : "#3b82f6";
                      return <rect x={x} y={y} width={width} height={height} rx={4} fill={color} />;
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Feature interaction heatmap */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Feature Interaction Heatmap</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Pairwise SHAP interaction values between feature groups
            </p>
            <div className="overflow-x-auto">
              <div
                className="grid gap-1"
                style={{ gridTemplateColumns: `80px repeat(${interactionFeatures.length}, 1fr)` }}
              >
                {/* Header row */}
                <div />
                {interactionFeatures.map((f) => (
                  <div key={f} className="text-xs font-medium text-gray-500 dark:text-gray-400 text-center truncate px-1">
                    {f}
                  </div>
                ))}

                {/* Data rows */}
                {interactionMatrix.map((row, ri) => (
                  <>
                    <div key={`label-${ri}`} className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center">
                      {interactionFeatures[ri]}
                    </div>
                    {row.map((val, ci) => (
                      <div
                        key={`${ri}-${ci}`}
                        className={`${heatColor(val)} rounded-md flex items-center justify-center h-10 text-xs font-semibold text-white`}
                        title={`${interactionFeatures[ri]} x ${interactionFeatures[ci]}: ${val.toFixed(2)}`}
                      >
                        {val.toFixed(2)}
                      </div>
                    ))}
                  </>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/*  LIME Tab                                                        */}
      {/* ---------------------------------------------------------------- */}
      {activeTab === "lime" && (
        <div className="space-y-6">
          {/* Prediction overview */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="card card-hover p-6 flex flex-col items-center justify-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Prediction Probability
              </p>
              <p className="mt-2 text-5xl font-bold text-gray-900 dark:text-white">
                {(adjustedProbability * 100).toFixed(1)}%
              </p>
              <span
                className={`mt-2 badge-${adjustedProbability >= 0.7 ? "red" : adjustedProbability >= 0.4 ? "yellow" : "green"} px-3 py-1 rounded-full text-sm font-medium`}
              >
                {adjustedProbability >= 0.7 ? "High Risk" : adjustedProbability >= 0.4 ? "Moderate Risk" : "Low Risk"}
              </span>
              {toggledFeatures.size > 0 && (
                <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                  Original: {(lime.probability * 100).toFixed(1)}% | Delta:{" "}
                  {((adjustedProbability - lime.probability) * 100).toFixed(1)}%
                </p>
              )}
            </div>

            <div className="card card-hover p-6 flex flex-col items-center justify-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                95% Confidence Interval
              </p>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                {(lime.confidence[0] * 100).toFixed(0)}% &ndash; {(lime.confidence[1] * 100).toFixed(0)}%
              </p>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                Width: {((lime.confidence[1] - lime.confidence[0]) * 100).toFixed(0)} percentage points
              </p>
            </div>

            <div className="card card-hover p-6 flex flex-col items-center justify-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Model</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{selectedModel}</p>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Instance-level LIME explanation</p>
            </div>
          </div>

          {/* Feature contributions bar chart */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Feature Contributions</h2>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={lime.features.map((f) => ({
                    ...f,
                    adjustedWeight: toggledFeatures.has(f.feature) ? 0 : f.weight,
                  }))}
                  layout="vertical"
                  margin={{ left: 140, right: 20, top: 5, bottom: 5 }}
                >
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                  <YAxis type="category" dataKey="feature" width={130} tick={{ fontSize: 12 }} stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: "8px", color: "#f9fafb" }}
                    formatter={(val: number) => [val.toFixed(3), "Contribution"]}
                  />
                  <Bar
                    dataKey="adjustedWeight"
                    radius={[4, 4, 4, 4]}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    shape={(props: any) => {
                      const { x, y, width, height, payload } = props;
                      const toggled = toggledFeatures.has(payload.feature);
                      const color = toggled ? "#6b7280" : payload.weight >= 0 ? "#ef4444" : "#3b82f6";
                      return <rect x={x} y={y} width={Math.abs(width) || 2} height={height} rx={4} fill={color} opacity={toggled ? 0.3 : 1} />;
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* What-If panel */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">What-If Analysis</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Toggle feature values to simulate how the prediction would change.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {lime.features.map((f) => {
                const toggled = toggledFeatures.has(f.feature);
                return (
                  <div
                    key={f.feature}
                    className={`card-hover rounded-xl border p-4 transition-all cursor-pointer ${
                      toggled
                        ? "border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-950/40"
                        : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                    }`}
                    onClick={() => handleToggle(f.feature)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">{f.feature}</span>
                      <span
                        className={`text-xs font-mono px-2 py-0.5 rounded ${
                          f.weight >= 0
                            ? "badge-red bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300"
                            : "badge-blue bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                        }`}
                      >
                        {f.weight >= 0 ? "+" : ""}{f.weight.toFixed(3)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className={`px-2 py-1 rounded ${!toggled ? "bg-gray-200 dark:bg-gray-600 font-bold" : "bg-gray-100 dark:bg-gray-700"} text-gray-700 dark:text-gray-300`}>
                        {f.currentValue}
                      </span>
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                      <span className={`px-2 py-1 rounded ${toggled ? "bg-blue-200 dark:bg-blue-700 font-bold" : "bg-gray-100 dark:bg-gray-700"} text-gray-700 dark:text-gray-300`}>
                        {f.toggledValue}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                      {toggled ? "Toggled - click to revert" : "Click to simulate change"}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/*  Model Cards Tab                                                 */}
      {/* ---------------------------------------------------------------- */}
      {activeTab === "cards" && (
        <div className="space-y-6">
          {models.map((modelName) => {
            const mc = modelCards[modelName];
            const radarData = [
              { metric: "AUC", value: mc.auc * 100 },
              { metric: "F1", value: mc.f1 * 100 },
              { metric: "Precision", value: mc.precision * 100 },
              { metric: "Recall", value: mc.recall * 100 },
            ];

            return (
              <div
                key={modelName}
                className={`card card-hover p-6 transition-all ${
                  selectedModel === modelName ? "ring-2 ring-blue-500 dark:ring-blue-400" : ""
                }`}
              >
                <div className="flex flex-col lg:flex-row gap-6">
                  {/* Left column */}
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-gray-900 dark:text-white">{modelName}</h2>
                      <span className="badge-blue bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full">
                        v2.1
                      </span>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Purpose</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{mc.purpose}</p>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Training Data</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{mc.trainingData}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Sample: {mc.sampleSize}</p>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Intended Use</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{mc.intendedUse}</p>
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Limitations</h3>
                      <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400 space-y-1">
                        {mc.limitations.map((l, i) => (
                          <li key={i}>{l}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      Last Audit: {mc.lastAudit}
                    </div>
                  </div>

                  {/* Right column - metrics */}
                  <div className="lg:w-80 space-y-4">
                    {/* Radar chart */}
                    <div className="h-52">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={radarData}>
                          <PolarGrid stroke="#4b5563" />
                          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#9ca3af" }} />
                          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} stroke="#6b7280" />
                          <Radar
                            name="Score"
                            dataKey="value"
                            stroke="#3b82f6"
                            fill="#3b82f6"
                            fillOpacity={0.25}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Performance metrics */}
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { label: "AUC-ROC", value: mc.auc },
                        { label: "F1 Score", value: mc.f1 },
                        { label: "Precision", value: mc.precision },
                        { label: "Recall", value: mc.recall },
                      ].map((m) => (
                        <div key={m.label} className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-500 dark:text-gray-400">{m.label}</p>
                          <p className={`text-lg font-bold ${metricColor(m.value)}`}>{m.value.toFixed(2)}</p>
                        </div>
                      ))}
                    </div>

                    {/* Fairness metrics */}
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Fairness Metrics</h3>
                      <div className="space-y-2">
                        {mc.fairness.map((f) => (
                          <div key={f.group} className="flex items-center justify-between">
                            <span className="text-xs text-gray-600 dark:text-gray-400">{f.group}</span>
                            <div className="flex items-center gap-2">
                              <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    f.disparity <= 0.03
                                      ? "bg-emerald-500"
                                      : f.disparity <= 0.05
                                        ? "bg-yellow-500"
                                        : "bg-red-500"
                                  }`}
                                  style={{ width: `${Math.min(f.disparity * 1000, 100)}%` }}
                                />
                              </div>
                              <span
                                className={`text-xs font-mono ${
                                  f.disparity <= 0.03
                                    ? "badge-green text-emerald-600 dark:text-emerald-400"
                                    : f.disparity <= 0.05
                                      ? "badge-yellow text-yellow-600 dark:text-yellow-400"
                                      : "badge-red text-red-600 dark:text-red-400"
                                }`}
                              >
                                {f.disparity.toFixed(2)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
