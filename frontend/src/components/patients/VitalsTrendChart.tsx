"use client";

import { useState, useEffect } from "react";
import { fetchVitals, type VitalData } from "@/lib/api";

type VitalKey = "heart_rate" | "blood_pressure" | "spo2" | "glucose" | "temperature";

const VITAL_TABS: { key: VitalKey; label: string; unit: string; color: string }[] = [
  { key: "heart_rate", label: "Heart Rate", unit: "bpm", color: "#ef4444" },
  { key: "blood_pressure", label: "Blood Pressure", unit: "mmHg", color: "#3b82f6" },
  { key: "spo2", label: "SpO2", unit: "%", color: "#10b981" },
  { key: "glucose", label: "Glucose", unit: "mg/dL", color: "#f59e0b" },
  { key: "temperature", label: "Temp", unit: "F", color: "#8b5cf6" },
];

function extractValue(vital: VitalData): number | null {
  const v = vital.value;
  if (v.value != null) return Number(v.value);
  if (v.systolic != null) return Number(v.systolic);
  return null;
}

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const height = 120;
  const width = 500;
  const stepX = width / (data.length - 1);

  const points = data
    .map((v, i) => `${i * stepX},${height - ((v - min) / range) * (height - 20) - 10}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="none">
      <polyline fill="none" stroke={color} strokeWidth="2.5" points={points} />
      <circle
        cx={(data.length - 1) * stepX}
        cy={height - ((data[data.length - 1] - min) / range) * (height - 20) - 10}
        r="4"
        fill={color}
      />
    </svg>
  );
}

export function VitalsTrendChart({ patientId }: { patientId: string }) {
  const [activeTab, setActiveTab] = useState<VitalKey>("heart_rate");
  const [vitals, setVitals] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchVitals(patientId)
      .then((data) => {
        // Group values by vital_type, chronologically
        const grouped: Record<string, number[]> = {};
        // Data comes newest-first from API, reverse for chronological order
        const sorted = [...data].reverse();
        for (const v of sorted) {
          const val = extractValue(v);
          if (val != null) {
            if (!grouped[v.vital_type]) grouped[v.vital_type] = [];
            grouped[v.vital_type].push(val);
          }
        }
        setVitals(grouped);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [patientId]);

  const tab = VITAL_TABS.find((t) => t.key === activeTab)!;
  const data = vitals[activeTab] || [];
  const currentValue = data.length > 0 ? data[data.length - 1] : null;

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Vitals Trend</h2>
        <span className="text-sm text-gray-400">Recent readings</span>
      </div>

      {/* Vital type tabs */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
        {VITAL_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
              activeTab === t.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-40 items-center justify-center text-sm text-gray-400">
          Loading vitals...
        </div>
      ) : data.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-sm text-gray-400">
          No {tab.label.toLowerCase()} readings
        </div>
      ) : (
        <>
          {/* Current value */}
          <div className="mb-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold" style={{ color: tab.color }}>
              {currentValue}
            </span>
            <span className="text-sm text-gray-400">{tab.unit}</span>
          </div>

          {/* Chart */}
          <div className="h-32">
            <MiniSparkline data={data} color={tab.color} />
          </div>
        </>
      )}
    </div>
  );
}
