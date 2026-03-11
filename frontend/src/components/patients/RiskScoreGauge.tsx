"use client";

import { useState, useEffect } from "react";

interface RiskData {
  score: number;
  risk_level: string;
  factors: { name: string; contribution: number }[];
  recommendations: string[];
}

const DEMO_RISK: RiskData = {
  score: 0.82,
  risk_level: "critical",
  factors: [
    { name: "Critical anomalies", contribution: 0.35 },
    { name: "Elevated heart rate", contribution: 0.20 },
    { name: "Multiple vitals affected", contribution: 0.15 },
    { name: "Comorbidities (CHF, DM)", contribution: 0.12 },
  ],
  recommendations: [
    "Immediate clinical review recommended",
    "Consider initiating telehealth encounter",
    "Notify assigned care team",
  ],
};

const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  moderate: "#eab308",
  low: "#22c55e",
};

export function RiskScoreGauge({ patientId }: { patientId: string }) {
  const [risk, setRisk] = useState<RiskData | null>(null);

  useEffect(() => {
    // TODO: Replace with API call
    setRisk(DEMO_RISK);
  }, [patientId]);

  if (!risk) return <div className="card animate-pulse h-64" />;

  const percentage = Math.round(risk.score * 100);
  const color = RISK_COLORS[risk.risk_level] || RISK_COLORS.low;

  // SVG arc for gauge
  const radius = 60;
  const circumference = Math.PI * radius; // half circle
  const offset = circumference - (risk.score * circumference);

  return (
    <div className="card">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Risk Score</h2>

      {/* Gauge */}
      <div className="flex justify-center">
        <svg width="160" height="100" viewBox="0 0 160 100">
          {/* Background arc */}
          <path
            d="M 10 90 A 60 60 0 0 1 150 90"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Filled arc */}
          <path
            d="M 10 90 A 60 60 0 0 1 150 90"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${circumference}`}
            strokeDashoffset={offset}
          />
          {/* Score text */}
          <text x="80" y="80" textAnchor="middle" className="text-2xl font-bold" fill={color}>
            {percentage}
          </text>
          <text x="80" y="95" textAnchor="middle" className="text-xs" fill="#9ca3af">
            / 100
          </text>
        </svg>
      </div>

      {/* Contributing factors */}
      <div className="mt-4">
        <h3 className="text-xs font-medium uppercase text-gray-400">Contributing Factors</h3>
        <div className="mt-2 space-y-2">
          {risk.factors.map((f) => (
            <div key={f.name} className="flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${f.contribution * 100}%`, backgroundColor: color }}
                />
              </div>
              <span className="w-24 text-xs text-gray-600 truncate">{f.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="mt-4">
        <h3 className="text-xs font-medium uppercase text-gray-400">Recommendations</h3>
        <ul className="mt-1 space-y-1">
          {risk.recommendations.map((r) => (
            <li key={r} className="flex items-start gap-1 text-xs text-gray-600">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-gray-400" />
              {r}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
