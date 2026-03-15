"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VitalDataPoint {
  time: string;
  value: number;
}

interface VitalConfig {
  label: string;
  unit: string;
  min: number;
  max: number;
  warningLow: number;
  warningHigh: number;
  criticalLow: number;
  criticalHigh: number;
  color: string;
}

interface Alert {
  id: string;
  severity: "info" | "warning" | "critical";
  message: string;
  patient: string;
  timestamp: Date;
}

type BedStatus = "occupied" | "available" | "cleaning" | "maintenance";

interface Bed {
  id: number;
  status: BedStatus;
  patientInitials: string | null;
}

interface SystemMetric {
  label: string;
  value: number;
  unit: string;
  prev: number;
}

interface RealTimeDashboardProps {
  refreshInterval?: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VITAL_CONFIGS: Record<string, VitalConfig> = {
  heartRate: {
    label: "Heart Rate",
    unit: "bpm",
    min: 40,
    max: 160,
    warningLow: 55,
    warningHigh: 110,
    criticalLow: 45,
    criticalHigh: 140,
    color: "#ef4444",
  },
  spo2: {
    label: "SpO2",
    unit: "%",
    min: 85,
    max: 100,
    warningLow: 92,
    warningHigh: 100,
    criticalLow: 88,
    criticalHigh: 101,
    color: "#3b82f6",
  },
  bloodPressure: {
    label: "Blood Pressure",
    unit: "mmHg",
    min: 60,
    max: 180,
    warningLow: 80,
    warningHigh: 140,
    criticalLow: 70,
    criticalHigh: 160,
    color: "#a855f7",
  },
  respiratoryRate: {
    label: "Respiratory Rate",
    unit: "br/min",
    min: 8,
    max: 30,
    warningLow: 10,
    warningHigh: 22,
    criticalLow: 8,
    criticalHigh: 28,
    color: "#10b981",
  },
};

const MAX_DATA_POINTS = 20;
const TOTAL_BEDS = 24;
const BED_COLS = 6;

const PATIENT_NAMES = [
  "Alice Monroe",
  "Ben Carter",
  "Clara Diaz",
  "David Kim",
  "Eva Singh",
  "Frank Osei",
  "Grace Liu",
  "Henry Patel",
  "Irene Novak",
  "Jake Torres",
  "Karen Wu",
  "Leo Marsh",
];

const ALERT_MESSAGES = [
  "Heart rate exceeded threshold",
  "SpO2 dropped below 90%",
  "Blood pressure spike detected",
  "Respiratory rate abnormal",
  "IV drip rate changed",
  "Patient requested assistance",
  "Medication reminder due",
  "Fall risk alert triggered",
  "Temperature elevated",
  "ECG anomaly detected",
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function rand(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomFloat(min: number, max: number, decimals = 1): number {
  return parseFloat((Math.random() * (max - min) + min).toFixed(decimals));
}

function timeLabel(): string {
  const d = new Date();
  return `${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

function statusColor(value: number, cfg: VitalConfig): string {
  if (value <= cfg.criticalLow || value >= cfg.criticalHigh) return "text-red-500";
  if (value <= cfg.warningLow || value >= cfg.warningHigh) return "text-yellow-500";
  return "text-green-500";
}

function statusDot(value: number, cfg: VitalConfig): string {
  if (value <= cfg.criticalLow || value >= cfg.criticalHigh) return "bg-red-500";
  if (value <= cfg.warningLow || value >= cfg.warningHigh) return "bg-yellow-500";
  return "bg-green-500";
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("");
}

function severityStyles(severity: Alert["severity"]): string {
  switch (severity) {
    case "critical":
      return "border-l-red-500 bg-red-500/10 dark:bg-red-900/20";
    case "warning":
      return "border-l-yellow-500 bg-yellow-500/10 dark:bg-yellow-900/20";
    default:
      return "border-l-blue-500 bg-blue-500/10 dark:bg-blue-900/20";
  }
}

function bedStatusStyle(status: BedStatus): string {
  switch (status) {
    case "occupied":
      return "bg-blue-500 dark:bg-blue-600 text-white";
    case "available":
      return "bg-green-500 dark:bg-green-600 text-white";
    case "cleaning":
      return "bg-yellow-400 dark:bg-yellow-500 text-gray-900";
    case "maintenance":
      return "bg-gray-400 dark:bg-gray-600 text-white";
  }
}

function generateInitialBeds(): Bed[] {
  const statuses: BedStatus[] = ["occupied", "available", "cleaning", "maintenance"];
  return Array.from({ length: TOTAL_BEDS }, (_, i) => {
    const status = Math.random() < 0.6 ? "occupied" : statuses[rand(0, 3)];
    return {
      id: i + 1,
      status,
      patientInitials:
        status === "occupied"
          ? initials(PATIENT_NAMES[rand(0, PATIENT_NAMES.length - 1)])
          : null,
    };
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function VitalChart({
  vitalKey,
  data,
  config,
}: {
  vitalKey: string;
  data: VitalDataPoint[];
  config: VitalConfig;
}) {
  const latest = data.length > 0 ? data[data.length - 1].value : 0;
  const colorClass = statusColor(latest, config);
  const dotClass = statusDot(latest, config);

  return (
    <div className="card flex flex-col gap-2 p-4 dark:bg-gray-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${dotClass} animate-pulse`} />
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {config.label}
          </span>
        </div>
        <span className={`text-lg font-bold tabular-nums ${colorClass}`}>
          {latest} <span className="text-xs font-normal text-gray-500">{config.unit}</span>
        </span>
      </div>

      <div className="text-[10px] text-gray-400 dark:text-gray-500 flex gap-3">
        <span>Normal: {config.warningLow}&ndash;{config.warningHigh}</span>
        <span>Critical: &lt;{config.criticalLow} / &gt;{config.criticalHigh}</span>
      </div>

      <div className="h-28 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#9ca3af" />
            <YAxis domain={[config.min, config.max]} tick={{ fontSize: 10 }} stroke="#9ca3af" />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
              labelStyle={{ fontWeight: 600 }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={config.color}
              strokeWidth={2}
              dot={false}
              isAnimationActive
              animationDuration={400}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function AlertCard({ alert }: { alert: Alert }) {
  const ts = alert.timestamp;
  const timeStr = `${ts.getHours().toString().padStart(2, "0")}:${ts.getMinutes().toString().padStart(2, "0")}:${ts.getSeconds().toString().padStart(2, "0")}`;

  return (
    <div
      className={`border-l-4 rounded-md px-3 py-2 mb-2 animate-[slideIn_0.3s_ease-out] ${severityStyles(alert.severity)}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {alert.severity}
        </span>
        <span className="text-[10px] text-gray-400">{timeStr}</span>
      </div>
      <p className="text-sm text-gray-800 dark:text-gray-100 mt-0.5">{alert.message}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Patient: {alert.patient}</p>
    </div>
  );
}

function AnimatedCounter({ value, unit }: { value: number; unit: string }) {
  const [display, setDisplay] = useState(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const start = display;
    const diff = value - start;
    if (diff === 0) return;
    const duration = 400;
    const startTime = performance.now();

    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      setDisplay(Math.round(start + diff * progress));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    };

    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <span className="text-2xl font-bold tabular-nums text-gray-900 dark:text-white">
      {display.toLocaleString()}
      <span className="text-xs font-normal text-gray-500 ml-1">{unit}</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function RealTimeDashboard({
  refreshInterval = 2000,
}: RealTimeDashboardProps) {
  // -- Vitals state --
  const [vitals, setVitals] = useState<Record<string, VitalDataPoint[]>>(() => {
    const initial: Record<string, VitalDataPoint[]> = {};
    for (const key of Object.keys(VITAL_CONFIGS)) {
      initial[key] = [];
    }
    return initial;
  });

  // -- Alerts state --
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const alertsEndRef = useRef<HTMLDivElement>(null);

  // -- Beds state --
  const [beds, setBeds] = useState<Bed[]>(generateInitialBeds);

  // -- System metrics --
  const [metrics, setMetrics] = useState<SystemMetric[]>([
    { label: "Active Sessions", value: 142, unit: "", prev: 142 },
    { label: "API Latency", value: 38, unit: "ms", prev: 38 },
    { label: "Queue Depth", value: 7, unit: "", prev: 7 },
    { label: "Throughput", value: 1240, unit: "req/s", prev: 1240 },
  ]);

  // -- Generate a vital data point --
  const generateVitalPoint = useCallback(
    (key: string): VitalDataPoint => {
      const cfg = VITAL_CONFIGS[key];
      const range = cfg.warningHigh - cfg.warningLow;
      const center = (cfg.warningHigh + cfg.warningLow) / 2;
      // Mostly in-range with occasional spikes
      const noise = (Math.random() - 0.5) * range * 0.8;
      const spike = Math.random() < 0.08 ? (Math.random() - 0.5) * range * 1.6 : 0;
      const raw = center + noise + spike;
      const value = Math.round(Math.max(cfg.min, Math.min(cfg.max, raw)));
      return { time: timeLabel(), value };
    },
    [],
  );

  // -- Vitals interval --
  useEffect(() => {
    const id = setInterval(() => {
      setVitals((prev) => {
        const next: Record<string, VitalDataPoint[]> = {};
        for (const key of Object.keys(VITAL_CONFIGS)) {
          const old = prev[key] ?? [];
          const updated = [...old, generateVitalPoint(key)];
          next[key] = updated.length > MAX_DATA_POINTS ? updated.slice(-MAX_DATA_POINTS) : updated;
        }
        return next;
      });
    }, refreshInterval);
    return () => clearInterval(id);
  }, [refreshInterval, generateVitalPoint]);

  // -- Alerts interval --
  useEffect(() => {
    const id = setInterval(() => {
      if (Math.random() < 0.6) {
        const severities: Alert["severity"][] = ["info", "warning", "critical"];
        const weights = [0.5, 0.35, 0.15];
        const r = Math.random();
        let severity: Alert["severity"] = "info";
        let cumulative = 0;
        for (let i = 0; i < weights.length; i++) {
          cumulative += weights[i];
          if (r <= cumulative) {
            severity = severities[i];
            break;
          }
        }

        const newAlert: Alert = {
          id: crypto.randomUUID(),
          severity,
          message: ALERT_MESSAGES[rand(0, ALERT_MESSAGES.length - 1)],
          patient: PATIENT_NAMES[rand(0, PATIENT_NAMES.length - 1)],
          timestamp: new Date(),
        };

        setAlerts((prev) => {
          const updated = [...prev, newAlert];
          return updated.length > 50 ? updated.slice(-50) : updated;
        });
      }
    }, refreshInterval * 1.5);
    return () => clearInterval(id);
  }, [refreshInterval]);

  // -- Auto-scroll alerts --
  useEffect(() => {
    alertsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [alerts]);

  // -- Beds interval (every 5s) --
  useEffect(() => {
    const id = setInterval(() => {
      setBeds((prev) => {
        const next = [...prev];
        const changeCount = rand(1, 3);
        for (let i = 0; i < changeCount; i++) {
          const idx = rand(0, TOTAL_BEDS - 1);
          const statuses: BedStatus[] = ["occupied", "available", "cleaning", "maintenance"];
          const newStatus = statuses[rand(0, 3)];
          next[idx] = {
            ...next[idx],
            status: newStatus,
            patientInitials:
              newStatus === "occupied"
                ? initials(PATIENT_NAMES[rand(0, PATIENT_NAMES.length - 1)])
                : null,
          };
        }
        return next;
      });
    }, 5000);
    return () => clearInterval(id);
  }, []);

  // -- System metrics interval --
  useEffect(() => {
    const id = setInterval(() => {
      setMetrics((prev) =>
        prev.map((m) => {
          let newVal: number;
          switch (m.label) {
            case "Active Sessions":
              newVal = Math.max(0, m.value + rand(-8, 8));
              break;
            case "API Latency":
              newVal = Math.max(5, m.value + rand(-12, 12));
              break;
            case "Queue Depth":
              newVal = Math.max(0, m.value + rand(-3, 3));
              break;
            case "Throughput":
              newVal = Math.max(100, m.value + rand(-80, 80));
              break;
            default:
              newVal = m.value;
          }
          return { ...m, prev: m.value, value: newVal };
        }),
      );
    }, refreshInterval);
    return () => clearInterval(id);
  }, [refreshInterval]);

  // -- Render --
  return (
    <div className="space-y-6">
      {/* Slide-in animation keyframe (injected once) */}
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-12px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          Real-Time Dashboard
        </h2>
        <span className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
          <span className="inline-block h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          Live &mdash; updating every {refreshInterval / 1000}s
        </span>
      </div>

      {/* 1. Live Vitals Monitor */}
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
          Live Vitals Monitor
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {Object.entries(VITAL_CONFIGS).map(([key, cfg]) => (
            <VitalChart key={key} vitalKey={key} data={vitals[key] ?? []} config={cfg} />
          ))}
        </div>
      </section>

      {/* 2. Active Alerts Feed */}
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
          Active Alerts Feed
        </h3>
        <div className="card dark:bg-gray-800 p-4 h-64 overflow-y-auto">
          {alerts.length === 0 && (
            <p className="text-sm text-gray-400 italic">Waiting for alerts&hellip;</p>
          )}
          {alerts.map((a) => (
            <AlertCard key={a.id} alert={a} />
          ))}
          <div ref={alertsEndRef} />
        </div>
      </section>

      {/* 3. Bed Occupancy Board */}
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
          Bed Occupancy Board
        </h3>
        <div className="card dark:bg-gray-800 p-4">
          {/* Legend */}
          <div className="flex flex-wrap gap-4 mb-4 text-xs text-gray-600 dark:text-gray-300">
            {(
              [
                ["occupied", "bg-blue-500", "Occupied"],
                ["available", "bg-green-500", "Available"],
                ["cleaning", "bg-yellow-400", "Cleaning"],
                ["maintenance", "bg-gray-400", "Maintenance"],
              ] as const
            ).map(([, bg, label]) => (
              <span key={label} className="flex items-center gap-1.5">
                <span className={`inline-block h-3 w-3 rounded ${bg}`} />
                {label}
              </span>
            ))}
          </div>

          {/* Grid 4 rows x 6 cols */}
          <div
            className="grid gap-2"
            style={{ gridTemplateColumns: `repeat(${BED_COLS}, minmax(0, 1fr))` }}
          >
            {beds.map((bed) => (
              <div
                key={bed.id}
                className={`relative flex flex-col items-center justify-center rounded-lg py-3 text-xs font-medium transition-colors duration-500 ${bedStatusStyle(bed.status)}`}
              >
                <span className="font-bold">{bed.id.toString().padStart(2, "0")}</span>
                {bed.patientInitials && (
                  <span className="text-[10px] mt-0.5 opacity-80">{bed.patientInitials}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. System Metrics */}
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
          System Metrics
        </h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {metrics.map((m) => {
            const delta = m.value - m.prev;
            const deltaColor =
              delta > 0
                ? "text-green-500"
                : delta < 0
                  ? "text-red-500"
                  : "text-gray-400";
            const arrow = delta > 0 ? "\u25B2" : delta < 0 ? "\u25BC" : "\u2014";

            return (
              <div
                key={m.label}
                className="card dark:bg-gray-800 p-4 flex flex-col gap-1"
              >
                <span className="text-xs text-gray-500 dark:text-gray-400">{m.label}</span>
                <AnimatedCounter value={m.value} unit={m.unit} />
                <span className={`text-xs ${deltaColor}`}>
                  {arrow} {Math.abs(delta)}
                </span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
