"use client";

import { useState } from "react";
import {
  Scale,
  Users,
  BarChart3,
  AlertTriangle,
  Info,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import clsx from "clsx";

/* ── Types ─────────────────────────────────────────────────────────────────── */

type DemographicDimension = "age" | "sex" | "diagnosis";

const DIMENSION_OPTIONS: { value: DemographicDimension; label: string }[] = [
  { value: "age", label: "Age Groups" },
  { value: "sex", label: "Sex" },
  { value: "diagnosis", label: "Diagnosis Category" },
];

const SUBGROUP_COLORS = [
  "#3b82f6",
  "#16a34a",
  "#f59e0b",
  "#e11d48",
  "#8b5cf6",
  "#14b8a6",
];

interface SubgroupMetric {
  subgroup: string;
  accuracy: number;
  sensitivity: number;
  specificity: number;
  ppv: number;
  count: number;
}

interface DisparityMetric {
  name: string;
  value: number;
  threshold: number;
  status: "pass" | "warning" | "fail";
  description: string;
}

interface RiskDistribution {
  subgroup: string;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

/* ── Placeholder data by dimension ─────────────────────────────────────────── */

function getPlaceholderData(dimension: DemographicDimension) {
  const subgroupMetrics: SubgroupMetric[] =
    dimension === "age"
      ? [
          { subgroup: "18-34", accuracy: 0.91, sensitivity: 0.88, specificity: 0.93, ppv: 0.85, count: 187 },
          { subgroup: "35-49", accuracy: 0.89, sensitivity: 0.86, specificity: 0.91, ppv: 0.83, count: 312 },
          { subgroup: "50-64", accuracy: 0.92, sensitivity: 0.9, specificity: 0.93, ppv: 0.88, count: 428 },
          { subgroup: "65-74", accuracy: 0.87, sensitivity: 0.84, specificity: 0.89, ppv: 0.81, count: 246 },
          { subgroup: "75+", accuracy: 0.83, sensitivity: 0.79, specificity: 0.86, ppv: 0.77, count: 111 },
        ]
      : dimension === "sex"
        ? [
            { subgroup: "Male", accuracy: 0.9, sensitivity: 0.87, specificity: 0.92, ppv: 0.85, count: 612 },
            { subgroup: "Female", accuracy: 0.89, sensitivity: 0.86, specificity: 0.91, ppv: 0.84, count: 672 },
          ]
        : [
            { subgroup: "Diabetes", accuracy: 0.91, sensitivity: 0.89, specificity: 0.92, ppv: 0.87, count: 486 },
            { subgroup: "Hypertension", accuracy: 0.88, sensitivity: 0.85, specificity: 0.9, ppv: 0.82, count: 641 },
            { subgroup: "Heart Failure", accuracy: 0.86, sensitivity: 0.83, specificity: 0.88, ppv: 0.8, count: 127 },
            { subgroup: "CKD", accuracy: 0.84, sensitivity: 0.8, specificity: 0.87, ppv: 0.78, count: 198 },
            { subgroup: "COPD", accuracy: 0.87, sensitivity: 0.84, specificity: 0.89, ppv: 0.81, count: 89 },
          ];

  const disparityMetrics: DisparityMetric[] = [
    { name: "Statistical Parity Difference", value: 0.04, threshold: 0.1, status: "pass", description: "Difference in positive prediction rates across subgroups" },
    { name: "Equalized Odds Ratio", value: 0.92, threshold: 0.8, status: "pass", description: "Ratio of true positive rates across subgroups" },
    { name: "Predictive Parity Difference", value: 0.07, threshold: 0.1, status: "warning", description: "Difference in PPV across subgroups" },
    { name: "Calibration Difference", value: 0.03, threshold: 0.05, status: "pass", description: "Max difference in calibration slope across subgroups" },
  ];

  const riskDistributions: RiskDistribution[] =
    dimension === "age"
      ? [
          { subgroup: "18-34", low: 45, medium: 30, high: 18, critical: 7 },
          { subgroup: "35-49", low: 35, medium: 32, high: 22, critical: 11 },
          { subgroup: "50-64", low: 25, medium: 28, high: 30, critical: 17 },
          { subgroup: "65-74", low: 18, medium: 24, high: 34, critical: 24 },
          { subgroup: "75+", low: 12, medium: 20, high: 36, critical: 32 },
        ]
      : dimension === "sex"
        ? [
            { subgroup: "Male", low: 28, medium: 30, high: 26, critical: 16 },
            { subgroup: "Female", low: 30, medium: 29, high: 25, critical: 16 },
          ]
        : [
            { subgroup: "Diabetes", low: 22, medium: 28, high: 32, critical: 18 },
            { subgroup: "Hypertension", low: 30, medium: 30, high: 26, critical: 14 },
            { subgroup: "Heart Failure", low: 10, medium: 20, high: 38, critical: 32 },
            { subgroup: "CKD", low: 15, medium: 22, high: 35, critical: 28 },
            { subgroup: "COPD", low: 25, medium: 28, high: 30, critical: 17 },
          ];

  return { subgroupMetrics, disparityMetrics, riskDistributions };
}

/* ── Page Component ────────────────────────────────────────────────────────── */

export default function FairnessAnalysisPage() {
  const [dimension, setDimension] = useState<DemographicDimension>("age");

  const d = getPlaceholderData(dimension);

  const performanceChartData = d.subgroupMetrics.map((m) => ({
    subgroup: m.subgroup,
    Accuracy: +(m.accuracy * 100).toFixed(1),
    Sensitivity: +(m.sensitivity * 100).toFixed(1),
    Specificity: +(m.specificity * 100).toFixed(1),
    PPV: +(m.ppv * 100).toFixed(1),
  }));

  return (
    <div className="space-y-6 max-w-7xl animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Scale className="w-5 h-5 text-indigo-600" />
            AI Fairness Analysis
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Model performance and bias evaluation across demographic subgroups
          </p>
        </div>
        <div className="flex items-center gap-1">
          {DIMENSION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDimension(opt.value)}
              className={clsx(
                "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                dimension === opt.value
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {d.disparityMetrics.map((metric) => (
          <div
            key={metric.name}
            className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-center gap-2 mb-2">
              {metric.status === "pass" ? (
                <Scale className="w-4 h-4 text-emerald-500" />
              ) : metric.status === "warning" ? (
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-red-500" />
              )}
              <span
                className={clsx(
                  "text-[10px] font-bold px-1.5 py-0.5 rounded",
                  metric.status === "pass" && "bg-emerald-100 text-emerald-700",
                  metric.status === "warning" && "bg-amber-100 text-amber-700",
                  metric.status === "fail" && "bg-red-100 text-red-700"
                )}
              >
                {metric.status.toUpperCase()}
              </span>
            </div>
            <p className="text-2xl font-bold font-mono text-gray-900">
              {metric.value.toFixed(2)}
            </p>
            <p className="text-xs font-medium text-gray-900 mt-1">
              {metric.name}
            </p>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Threshold: {metric.threshold}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance comparison chart */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-gray-400" />
            Model Performance by Subgroup
          </h2>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={performanceChartData}
                margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#e5e7eb"
                  strokeOpacity={0.4}
                />
                <XAxis
                  dataKey="subgroup"
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  domain={[60, 100]}
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v: number) => [`${v}%`]}
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid #e5e7eb",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Accuracy" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Sensitivity" fill="#16a34a" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Specificity" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="PPV" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk score distribution */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-gray-400" />
            Risk Score Distribution by{" "}
            {DIMENSION_OPTIONS.find((o) => o.value === dimension)?.label}
          </h2>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={d.riskDistributions}
                margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#e5e7eb"
                  strokeOpacity={0.4}
                />
                <XAxis
                  dataKey="subgroup"
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v: number) => [`${v}%`]}
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid #e5e7eb",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="low" name="Low" stackId="risk" fill="#16a34a" />
                <Bar dataKey="medium" name="Medium" stackId="risk" fill="#f59e0b" />
                <Bar dataKey="high" name="High" stackId="risk" fill="#ea580c" />
                <Bar
                  dataKey="critical"
                  name="Critical"
                  stackId="risk"
                  fill="#e11d48"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Subgroup detail table */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Info className="w-4 h-4 text-gray-400" />
          Detailed Subgroup Metrics
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left">
                <th className="pb-2 text-xs font-medium text-gray-500">Subgroup</th>
                <th className="pb-2 text-xs font-medium text-gray-500 text-right">N</th>
                <th className="pb-2 text-xs font-medium text-gray-500 text-right">Accuracy</th>
                <th className="pb-2 text-xs font-medium text-gray-500 text-right">Sensitivity</th>
                <th className="pb-2 text-xs font-medium text-gray-500 text-right">Specificity</th>
                <th className="pb-2 text-xs font-medium text-gray-500 text-right">PPV</th>
              </tr>
            </thead>
            <tbody>
              {d.subgroupMetrics.map((m, i) => (
                <tr
                  key={m.subgroup}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <td className="py-2.5">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2.5 h-2.5 rounded-full"
                        style={{
                          background: SUBGROUP_COLORS[i % SUBGROUP_COLORS.length],
                        }}
                      />
                      <span className="font-medium text-gray-900">{m.subgroup}</span>
                    </div>
                  </td>
                  <td className="py-2.5 text-right font-mono text-gray-500">
                    {m.count.toLocaleString()}
                  </td>
                  <td className="py-2.5 text-right font-mono font-bold text-gray-900">
                    {(m.accuracy * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 text-right font-mono font-bold text-gray-900">
                    {(m.sensitivity * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 text-right font-mono font-bold text-gray-900">
                    {(m.specificity * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 text-right font-mono font-bold text-gray-900">
                    {(m.ppv * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Disparity descriptions */}
        <div className="mt-4 pt-4 border-t border-gray-200 space-y-2">
          {d.disparityMetrics.map((metric) => (
            <div key={metric.name} className="flex items-start gap-2 text-xs">
              <Info className="w-3 h-3 text-gray-400 mt-0.5 flex-shrink-0" />
              <span className="text-gray-500">
                <span className="font-medium text-gray-900">{metric.name}:</span>{" "}
                {metric.description}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
