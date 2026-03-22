"use client";

import { useState } from "react";
import {
  FlaskConical,
  Play,
  User,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Loader2,
  RotateCcw,
} from "lucide-react";
import clsx from "clsx";
import Link from "next/link";

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface Patient {
  id: string;
  name: string;
}

interface SliderParam {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  defaultValue: number;
}

interface SimulationResult {
  baselineRisk: number;
  simulatedRisk: number;
  riskChange: number;
  factors: {
    label: string;
    baseline: string;
    simulated: string;
    impact: "positive" | "negative" | "neutral";
  }[];
}

const PARAMETERS: SliderParam[] = [
  { key: "hba1c", label: "HbA1c Threshold", min: 5.0, max: 14.0, step: 0.1, unit: "%", defaultValue: 7.5 },
  { key: "systolic_bp", label: "Systolic BP Target", min: 100, max: 180, step: 5, unit: "mmHg", defaultValue: 140 },
  { key: "diastolic_bp", label: "Diastolic BP Target", min: 60, max: 110, step: 5, unit: "mmHg", defaultValue: 90 },
  { key: "med_adherence", label: "Medication Adherence", min: 0, max: 100, step: 5, unit: "%", defaultValue: 75 },
  { key: "exercise_min", label: "Weekly Exercise", min: 0, max: 300, step: 15, unit: "min", defaultValue: 90 },
  { key: "bmi", label: "BMI Target", min: 18, max: 45, step: 0.5, unit: "kg/m\u00B2", defaultValue: 28 },
  { key: "ldl", label: "LDL Cholesterol", min: 40, max: 200, step: 5, unit: "mg/dL", defaultValue: 130 },
  { key: "smoking", label: "Smoking Cessation", min: 0, max: 100, step: 10, unit: "%", defaultValue: 0 },
];

const PLACEHOLDER_PATIENTS: Patient[] = [
  { id: "p1", name: "Maria Garcia" },
  { id: "p2", name: "James Wilson" },
  { id: "p3", name: "Susan Chen" },
  { id: "p4", name: "Robert Johnson" },
];

/* ── Page Component ────────────────────────────────────────────────────────── */

export default function WhatIfSimulatorPage() {
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [params, setParams] = useState<Record<string, number>>(() =>
    Object.fromEntries(PARAMETERS.map((p) => [p.key, p.defaultValue]))
  );
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleRun = () => {
    if (!selectedPatientId) return;
    setIsSimulating(true);
    // Simulate a short delay then produce placeholder results
    setTimeout(() => {
      setResult({
        baselineRisk: 68,
        simulatedRisk: 42,
        riskChange: -26,
        factors: [
          {
            label: "HbA1c Control",
            baseline: "9.2%",
            simulated: `${params.hba1c}%`,
            impact: params.hba1c < 8 ? "positive" : "negative",
          },
          {
            label: "Blood Pressure",
            baseline: "152/94",
            simulated: `${params.systolic_bp}/${params.diastolic_bp}`,
            impact: params.systolic_bp < 140 ? "positive" : "negative",
          },
          {
            label: "Medication Adherence",
            baseline: "62%",
            simulated: `${params.med_adherence}%`,
            impact: params.med_adherence > 70 ? "positive" : "negative",
          },
          {
            label: "Physical Activity",
            baseline: "30 min/wk",
            simulated: `${params.exercise_min} min/wk`,
            impact: params.exercise_min > 60 ? "positive" : "negative",
          },
          {
            label: "BMI",
            baseline: "32.1",
            simulated: `${params.bmi}`,
            impact: params.bmi < 30 ? "positive" : "neutral",
          },
          {
            label: "LDL Cholesterol",
            baseline: "168 mg/dL",
            simulated: `${params.ldl} mg/dL`,
            impact: params.ldl < 100 ? "positive" : "negative",
          },
        ],
      });
      setIsSimulating(false);
    }, 800);
  };

  const handleReset = () => {
    setParams(Object.fromEntries(PARAMETERS.map((p) => [p.key, p.defaultValue])));
    setResult(null);
  };

  const updateParam = (key: string, value: number) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6 max-w-7xl animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-indigo-600" />
            What-If Simulator
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Adjust clinical parameters and see projected risk changes
          </p>
          <Link
            href="/simulator"
            className="text-xs text-indigo-600 hover:text-indigo-700 mt-1 inline-block"
          >
            &larr; Back to Vitals Simulator
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-gray-400" />
            <select
              value={selectedPatientId ?? ""}
              onChange={(e) => setSelectedPatientId(e.target.value || null)}
              className="pl-9 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 appearance-none cursor-pointer"
            >
              <option value="">Select patient...</option>
              {PLACEHOLDER_PATIENTS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Parameter sliders */}
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-4">
            Clinical Parameters
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
            {PARAMETERS.map((param) => (
              <div key={param.key}>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-gray-900 dark:text-gray-100">
                    {param.label}
                  </label>
                  <span className="text-xs font-mono font-bold text-indigo-600">
                    {params[param.key]}
                    {param.unit}
                  </span>
                </div>
                <input
                  type="range"
                  min={param.min}
                  max={param.max}
                  step={param.step}
                  value={params[param.key]}
                  onChange={(e) =>
                    updateParam(param.key, parseFloat(e.target.value))
                  }
                  className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-indigo-500"
                />
                <div className="flex items-center justify-between mt-0.5 text-[11px] text-gray-500 dark:text-gray-400">
                  <span>
                    {param.min}
                    {param.unit}
                  </span>
                  <span>
                    {param.max}
                    {param.unit}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={handleRun}
              disabled={!selectedPatientId || isSimulating}
              className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSimulating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Run Simulation
            </button>
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700 dark:text-gray-300 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
          </div>
        </div>

        {/* Risk score display */}
        <div className="space-y-4">
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-sm text-center">
            <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-4">
              Risk Score
            </h2>
            {result ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center gap-4">
                  <div>
                    <p className="text-xl sm:text-3xl font-bold font-mono text-red-500">
                      {result.baselineRisk}%
                    </p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">Baseline</p>
                  </div>
                  <ArrowRight className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                  <div>
                    <p className="text-xl sm:text-3xl font-bold font-mono text-emerald-500">
                      {result.simulatedRisk}%
                    </p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">Simulated</p>
                  </div>
                </div>
                <div
                  className={clsx(
                    "inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-bold",
                    result.riskChange < 0
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-red-100 text-red-700"
                  )}
                >
                  {result.riskChange < 0 ? (
                    <TrendingDown className="w-4 h-4" />
                  ) : (
                    <TrendingUp className="w-4 h-4" />
                  )}
                  {result.riskChange > 0 ? "+" : ""}
                  {result.riskChange}%
                </div>
              </div>
            ) : (
              <div className="py-8">
                <FlaskConical className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Adjust parameters and run the simulation to see projected risk
                  changes
                </p>
              </div>
            )}
          </div>

          {/* Factor comparison */}
          {result && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-sm">
              <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-3">
                Before / After Comparison
              </h2>
              <div className="space-y-2.5">
                {result.factors.map((f) => (
                  <div
                    key={f.label}
                    className="flex items-center justify-between text-xs"
                  >
                    <span className="font-medium text-gray-900 dark:text-gray-100 w-28 flex-shrink-0">
                      {f.label}
                    </span>
                    <span className="font-mono text-gray-500 dark:text-gray-400">
                      {f.baseline}
                    </span>
                    <ArrowRight className="w-3 h-3 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                    <span
                      className={clsx(
                        "font-mono font-bold",
                        f.impact === "positive" && "text-emerald-600",
                        f.impact === "negative" && "text-red-600",
                        f.impact === "neutral" && "text-gray-900 dark:text-gray-100"
                      )}
                    >
                      {f.simulated}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
