"use client";

import { useState, useEffect } from "react";
import { fetchVitals, type VitalData } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";

type VitalKey = "heart_rate" | "blood_pressure" | "spo2" | "glucose" | "temperature";

interface VitalPoint {
  time: string;
  value: number;
}

const VITAL_TABS: { key: VitalKey; label: string; unit: string; color: string }[] = [
  { key: "heart_rate", label: "Heart Rate", unit: "bpm", color: "#ef4444" },
  { key: "blood_pressure", label: "Blood Pressure", unit: "mmHg", color: "#3b82f6" },
  { key: "spo2", label: "SpO2", unit: "%", color: "#10b981" },
  { key: "glucose", label: "Glucose", unit: "mg/dL", color: "#f59e0b" },
  { key: "temperature", label: "Temp", unit: "F", color: "#8b5cf6" },
];

const NORMAL_RANGES: Record<VitalKey, { low: number; high: number }> = {
  heart_rate: { low: 60, high: 100 },
  blood_pressure: { low: 90, high: 140 },
  spo2: { low: 95, high: 100 },
  glucose: { low: 70, high: 140 },
  temperature: { low: 97, high: 99.5 },
};

function extractValue(vital: VitalData): number | null {
  const v = vital.value;
  if (v.value != null) return Number(v.value);
  if (v.systolic != null) return Number(v.systolic);
  return null;
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
  unit: string;
  color: string;
}

function CustomTooltip({ active, payload, label, unit, color }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-md">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-semibold" style={{ color }}>
        {payload[0].value} <span className="font-normal text-gray-400">{unit}</span>
      </p>
    </div>
  );
}

export function VitalsTrendChart({ patientId }: { patientId: string }) {
  const [activeTab, setActiveTab] = useState<VitalKey>("heart_rate");
  const [vitals, setVitals] = useState<Record<string, VitalPoint[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchVitals(patientId)
      .then((data) => {
        const grouped: Record<string, VitalPoint[]> = {};
        // Data comes newest-first from API, reverse for chronological order
        const sorted = [...data].reverse();
        for (const v of sorted) {
          const val = extractValue(v);
          if (val != null) {
            if (!grouped[v.vital_type]) grouped[v.vital_type] = [];
            grouped[v.vital_type].push({
              time: formatTime(v.recorded_at),
              value: val,
            });
          }
        }
        setVitals(grouped);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [patientId]);

  const tab = VITAL_TABS.find((t) => t.key === activeTab)!;
  const data = vitals[activeTab] || [];
  const currentValue = data.length > 0 ? data[data.length - 1].value : null;
  const normalRange = NORMAL_RANGES[activeTab];

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
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10, fill: "#9ca3af" }}
                  tickLine={false}
                  axisLine={{ stroke: "#e5e7eb" }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "#9ca3af" }}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  content={<CustomTooltip unit={tab.unit} color={tab.color} />}
                />
                <ReferenceLine
                  y={normalRange.low}
                  stroke="#d1d5db"
                  strokeDasharray="4 4"
                  label={{ value: "Low", position: "left", fontSize: 9, fill: "#9ca3af" }}
                />
                <ReferenceLine
                  y={normalRange.high}
                  stroke="#d1d5db"
                  strokeDasharray="4 4"
                  label={{ value: "High", position: "left", fontSize: 9, fill: "#9ca3af" }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={tab.color}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: tab.color, strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: tab.color, strokeWidth: 2, stroke: "#fff" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
