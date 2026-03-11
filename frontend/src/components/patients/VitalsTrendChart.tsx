"use client";

import { useState } from "react";

type VitalKey = "heart_rate" | "blood_pressure" | "spo2" | "glucose" | "temperature";

const VITAL_TABS: { key: VitalKey; label: string; unit: string; color: string }[] = [
  { key: "heart_rate", label: "Heart Rate", unit: "bpm", color: "#ef4444" },
  { key: "blood_pressure", label: "Blood Pressure", unit: "mmHg", color: "#3b82f6" },
  { key: "spo2", label: "SpO2", unit: "%", color: "#10b981" },
  { key: "glucose", label: "Glucose", unit: "mg/dL", color: "#f59e0b" },
  { key: "temperature", label: "Temp", unit: "F", color: "#8b5cf6" },
];

// Demo sparkline data points
const DEMO_DATA: Record<VitalKey, number[]> = {
  heart_rate: [72, 75, 78, 82, 88, 92, 85, 80, 76, 74, 78, 95, 88, 82, 79],
  blood_pressure: [130, 128, 135, 140, 145, 142, 138, 132, 130, 134, 148, 155, 142, 138, 135],
  spo2: [98, 97, 96, 95, 94, 93, 95, 96, 97, 96, 92, 91, 94, 96, 97],
  glucose: [120, 135, 128, 142, 155, 148, 138, 125, 132, 145, 168, 155, 142, 135, 128],
  temperature: [98.4, 98.6, 98.8, 99.0, 99.2, 98.9, 98.6, 98.5, 98.7, 99.1, 99.8, 100.2, 99.5, 99.0, 98.7],
};

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
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
      {/* Last point indicator */}
      {data.length > 0 && (
        <circle
          cx={(data.length - 1) * stepX}
          cy={height - ((data[data.length - 1] - min) / range) * (height - 20) - 10}
          r="4"
          fill={color}
        />
      )}
    </svg>
  );
}

export function VitalsTrendChart({ patientId }: { patientId: string }) {
  const [activeTab, setActiveTab] = useState<VitalKey>("heart_rate");
  const tab = VITAL_TABS.find((t) => t.key === activeTab)!;
  const data = DEMO_DATA[activeTab];
  const currentValue = data[data.length - 1];

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Vitals Trend</h2>
        <span className="text-sm text-gray-400">Last 24 hours</span>
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
    </div>
  );
}
