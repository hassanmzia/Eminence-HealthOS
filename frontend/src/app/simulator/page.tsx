"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Activity,
  Heart,
  Thermometer,
  Wind,
  Droplets,
  User,
  Play,
  Square,
  Settings2,
  AlertTriangle,
  CheckCircle2,
  Zap,
  RefreshCw,
  BrainCircuit,
  ShieldAlert,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import clsx from "clsx";
import Link from "next/link";

/* ── Vital Configuration ─────────────────────────────────────────────────── */

interface VitalConfig {
  key: string;
  label: string;
  unit: string;
  icon: React.ElementType;
  color: string;
  chartColor: string;
  min: number;
  max: number;
  normalLow: number;
  normalHigh: number;
  step: number;
  defaultBaseline: number;
}

const VITAL_CONFIGS: VitalConfig[] = [
  { key: "heartRate", label: "Heart Rate", unit: "bpm", icon: Heart, color: "text-red-500", chartColor: "#e11d48", min: 30, max: 200, normalLow: 60, normalHigh: 100, step: 1, defaultBaseline: 75 },
  { key: "systolicBP", label: "Systolic BP", unit: "mmHg", icon: Activity, color: "text-blue-500", chartColor: "#3b82f6", min: 60, max: 250, normalLow: 90, normalHigh: 140, step: 1, defaultBaseline: 125 },
  { key: "diastolicBP", label: "Diastolic BP", unit: "mmHg", icon: Activity, color: "text-indigo-500", chartColor: "#6366f1", min: 40, max: 150, normalLow: 60, normalHigh: 90, step: 1, defaultBaseline: 80 },
  { key: "spo2", label: "SpO2", unit: "%", icon: Droplets, color: "text-sky-500", chartColor: "#0ea5e9", min: 70, max: 100, normalLow: 95, normalHigh: 100, step: 1, defaultBaseline: 97 },
  { key: "temperature", label: "Temperature", unit: "\u00B0F", icon: Thermometer, color: "text-orange-500", chartColor: "#f97316", min: 95, max: 106, normalLow: 97.8, normalHigh: 99.1, step: 0.1, defaultBaseline: 98.6 },
  { key: "respRate", label: "Respiratory Rate", unit: "br/min", icon: Wind, color: "text-teal-500", chartColor: "#14b8a6", min: 6, max: 40, normalLow: 12, normalHigh: 20, step: 1, defaultBaseline: 16 },
  { key: "glucose", label: "Blood Glucose", unit: "mg/dL", icon: Droplets, color: "text-purple-500", chartColor: "#8b5cf6", min: 30, max: 500, normalLow: 70, normalHigh: 140, step: 1, defaultBaseline: 110 },
];

/* ── Simulation Profiles ─────────────────────────────────────────────────── */

interface SimulationProfile {
  name: string;
  description: string;
  overrides: Record<string, { baseline: number; variability: number; anomalyChance: number }>;
}

const PROFILES: SimulationProfile[] = [
  {
    name: "Healthy Patient",
    description: "Normal vital ranges with minimal variability",
    overrides: {
      heartRate: { baseline: 72, variability: 5, anomalyChance: 0 },
      systolicBP: { baseline: 118, variability: 6, anomalyChance: 0 },
      diastolicBP: { baseline: 76, variability: 4, anomalyChance: 0 },
      spo2: { baseline: 98, variability: 1, anomalyChance: 0 },
      temperature: { baseline: 98.6, variability: 0.3, anomalyChance: 0 },
      respRate: { baseline: 15, variability: 2, anomalyChance: 0 },
      glucose: { baseline: 100, variability: 12, anomalyChance: 0 },
    },
  },
  {
    name: "Hypertensive Crisis",
    description: "Dangerously elevated BP with tachycardia",
    overrides: {
      heartRate: { baseline: 110, variability: 8, anomalyChance: 0.3 },
      systolicBP: { baseline: 195, variability: 15, anomalyChance: 0.4 },
      diastolicBP: { baseline: 115, variability: 8, anomalyChance: 0.3 },
      spo2: { baseline: 94, variability: 2, anomalyChance: 0.2 },
      temperature: { baseline: 98.8, variability: 0.4, anomalyChance: 0 },
      respRate: { baseline: 22, variability: 3, anomalyChance: 0.1 },
      glucose: { baseline: 135, variability: 20, anomalyChance: 0.1 },
    },
  },
  {
    name: "Diabetic Emergency",
    description: "Severe hyperglycemia with dehydration signs",
    overrides: {
      heartRate: { baseline: 105, variability: 10, anomalyChance: 0.2 },
      systolicBP: { baseline: 100, variability: 10, anomalyChance: 0.1 },
      diastolicBP: { baseline: 65, variability: 6, anomalyChance: 0.1 },
      spo2: { baseline: 96, variability: 2, anomalyChance: 0.1 },
      temperature: { baseline: 99.2, variability: 0.5, anomalyChance: 0.1 },
      respRate: { baseline: 24, variability: 4, anomalyChance: 0.2 },
      glucose: { baseline: 380, variability: 40, anomalyChance: 0.5 },
    },
  },
  {
    name: "Respiratory Distress",
    description: "Low SpO2, elevated respiratory rate, tachycardia",
    overrides: {
      heartRate: { baseline: 115, variability: 10, anomalyChance: 0.3 },
      systolicBP: { baseline: 135, variability: 10, anomalyChance: 0.1 },
      diastolicBP: { baseline: 85, variability: 5, anomalyChance: 0.1 },
      spo2: { baseline: 88, variability: 3, anomalyChance: 0.4 },
      temperature: { baseline: 100.4, variability: 0.6, anomalyChance: 0.2 },
      respRate: { baseline: 30, variability: 5, anomalyChance: 0.3 },
      glucose: { baseline: 120, variability: 15, anomalyChance: 0 },
    },
  },
  {
    name: "Sepsis Onset",
    description: "Fever, tachycardia, hypotension, elevated RR",
    overrides: {
      heartRate: { baseline: 120, variability: 12, anomalyChance: 0.3 },
      systolicBP: { baseline: 88, variability: 12, anomalyChance: 0.3 },
      diastolicBP: { baseline: 55, variability: 8, anomalyChance: 0.3 },
      spo2: { baseline: 92, variability: 3, anomalyChance: 0.3 },
      temperature: { baseline: 102.8, variability: 0.8, anomalyChance: 0.2 },
      respRate: { baseline: 28, variability: 5, anomalyChance: 0.3 },
      glucose: { baseline: 165, variability: 30, anomalyChance: 0.2 },
    },
  },
  {
    name: "Bradycardia Event",
    description: "Dangerously low heart rate with normal other vitals",
    overrides: {
      heartRate: { baseline: 42, variability: 6, anomalyChance: 0.4 },
      systolicBP: { baseline: 95, variability: 8, anomalyChance: 0.1 },
      diastolicBP: { baseline: 60, variability: 5, anomalyChance: 0.1 },
      spo2: { baseline: 95, variability: 2, anomalyChance: 0.1 },
      temperature: { baseline: 97.5, variability: 0.4, anomalyChance: 0 },
      respRate: { baseline: 14, variability: 2, anomalyChance: 0 },
      glucose: { baseline: 105, variability: 10, anomalyChance: 0 },
    },
  },
];

/* ── Simulation Engine ───────────────────────────────────────────────────── */

interface VitalParams {
  baseline: number;
  variability: number;
  anomalyChance: number;
}

interface GeneratedReading {
  timestamp: string;
  values: Record<string, number>;
  alerts: string[];
}

function generateReading(
  params: Record<string, VitalParams>,
  timeLabel: string
): GeneratedReading {
  const values: Record<string, number> = {};
  const alerts: string[] = [];

  for (const config of VITAL_CONFIGS) {
    const p = params[config.key];
    if (!p) continue;

    const u1 = Math.max(1e-10, Math.random());
    const u2 = Math.random();
    const gaussian = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);

    let value = p.baseline + gaussian * p.variability;

    if (Math.random() < p.anomalyChance) {
      const direction = Math.random() > 0.5 ? 1 : -1;
      value += direction * p.variability * 2.5;
    }

    value = Math.max(config.min, Math.min(config.max, value));
    value = config.step < 1 ? Math.round(value * 10) / 10 : Math.round(value);
    values[config.key] = value;

    if (value > config.normalHigh) {
      alerts.push(`${config.label}: ${value} ${config.unit} (HIGH)`);
    } else if (value < config.normalLow) {
      alerts.push(`${config.label}: ${value} ${config.unit} (LOW)`);
    }
  }

  return { timestamp: timeLabel, values, alerts };
}

/* ── AI Recommendation Types & Generator ─────────────────────────────────── */

interface AIRecommendation {
  id: string;
  severity: "info" | "warning" | "critical";
  title: string;
  description: string;
  agent: string;
  timestamp: string;
  icdCode?: string;
  icdDisplay?: string;
  cptCodes?: { code: string; display: string }[];
  treatment?: string;
  contraindications?: string[];
  patientFactors?: string[];
}

function generateLocalRecommendations(readings: GeneratedReading[]): AIRecommendation[] {
  const recs: AIRecommendation[] = [];
  if (readings.length === 0) return recs;

  const latest = readings[readings.length - 1];
  const v = latest.values;
  let id = 0;

  // Heart Rate
  if (v.heartRate > 120) {
    recs.push({
      id: String(++id), severity: "critical", title: "Severe Tachycardia Detected",
      description: `Heart rate at ${v.heartRate} bpm. Consider immediate evaluation for arrhythmia, sepsis, or hypovolemia. 12-lead ECG recommended.`,
      agent: "Cardiac Monitor Agent", timestamp: latest.timestamp,
      icdCode: "R00.0", icdDisplay: "Tachycardia, unspecified",
      cptCodes: [{ code: "93000", display: "12-lead ECG with interpretation" }, { code: "99291", display: "Critical care, first 30-74 min" }],
      treatment: "IV Metoprolol 5mg q5min (max 15mg), continuous telemetry monitoring, fluid resuscitation if hypovolemic.",
    });
  } else if (v.heartRate > 100) {
    recs.push({
      id: String(++id), severity: "warning", title: "Tachycardia Alert",
      description: `Heart rate elevated at ${v.heartRate} bpm. Assess for pain, anxiety, fever, dehydration, or medication effects.`,
      agent: "Cardiac Monitor Agent", timestamp: latest.timestamp,
      icdCode: "R00.0", icdDisplay: "Tachycardia, unspecified",
      cptCodes: [{ code: "93000", display: "12-lead ECG with interpretation" }],
      treatment: "PO Metoprolol 25-50mg BID, address underlying cause (hydration, pain management, antipyretics).",
    });
  } else if (v.heartRate < 50) {
    recs.push({
      id: String(++id), severity: "critical", title: "Severe Bradycardia",
      description: `Heart rate critically low at ${v.heartRate} bpm. Check for heart block, medication effects, or vagal response.`,
      agent: "Cardiac Monitor Agent", timestamp: latest.timestamp,
      icdCode: "R00.1", icdDisplay: "Bradycardia, unspecified",
      cptCodes: [{ code: "93000", display: "12-lead ECG with interpretation" }, { code: "33210", display: "Temporary transvenous pacemaker insertion" }],
      treatment: "Atropine 1mg IV q3-5min (max 3mg), transcutaneous pacing if unresponsive, hold beta-blockers/CCBs.",
    });
  }

  // Blood Pressure
  if (v.systolicBP > 180 || v.diastolicBP > 120) {
    recs.push({
      id: String(++id), severity: "critical", title: "Hypertensive Emergency",
      description: `BP ${v.systolicBP}/${v.diastolicBP} mmHg. Assess for end-organ damage. Consider IV antihypertensives.`,
      agent: "BP Management Agent", timestamp: latest.timestamp,
      icdCode: "I16.1", icdDisplay: "Hypertensive emergency",
      cptCodes: [{ code: "99291", display: "Critical care, first 30-74 min" }],
      treatment: "IV Nicardipine 5mg/hr (titrate 2.5mg/hr q5min, max 15mg/hr). Target 25% MAP reduction in 1hr.",
    });
  } else if (v.systolicBP > 160 || v.diastolicBP > 100) {
    recs.push({
      id: String(++id), severity: "warning", title: "Hypertension Stage 2",
      description: `BP ${v.systolicBP}/${v.diastolicBP} mmHg. Review current antihypertensive regimen.`,
      agent: "BP Management Agent", timestamp: latest.timestamp,
      icdCode: "I10", icdDisplay: "Essential (primary) hypertension",
      cptCodes: [{ code: "99214", display: "Office visit, moderate complexity" }],
      treatment: "Lisinopril 10-20mg daily or Amlodipine 5-10mg daily. Recheck BP in 2-4 weeks.",
    });
  } else if (v.systolicBP < 90) {
    recs.push({
      id: String(++id), severity: "critical", title: "Hypotension Alert",
      description: `Systolic BP at ${v.systolicBP} mmHg. Assess for shock, dehydration, or sepsis.`,
      agent: "BP Management Agent", timestamp: latest.timestamp,
      icdCode: "I95.9", icdDisplay: "Hypotension, unspecified",
      cptCodes: [{ code: "99291", display: "Critical care, first 30-74 min" }, { code: "96360", display: "IV infusion, hydration" }],
      treatment: "NS bolus 500-1000mL IV, Trendelenburg position, Norepinephrine 0.1-0.5mcg/kg/min if unresponsive.",
    });
  }

  // SpO2
  if (v.spo2 < 90) {
    recs.push({
      id: String(++id), severity: "critical", title: "Severe Hypoxemia",
      description: `SpO2 at ${v.spo2}%. Initiate supplemental O2 immediately. Consider ABG, CXR, and possible intubation.`,
      agent: "Respiratory Agent", timestamp: latest.timestamp,
      icdCode: "J96.01", icdDisplay: "Acute respiratory failure with hypoxia",
      cptCodes: [{ code: "94760", display: "Pulse oximetry (continuous)" }, { code: "71046", display: "Chest X-ray, 2 views" }, { code: "31500", display: "Emergency endotracheal intubation" }],
      treatment: "High-flow O2 via non-rebreather mask 15L/min, target SpO2 > 94%. Prepare for intubation if not improving.",
    });
  } else if (v.spo2 < 94) {
    recs.push({
      id: String(++id), severity: "warning", title: "Desaturation Warning",
      description: `SpO2 at ${v.spo2}%. Apply supplemental O2 via nasal cannula. Monitor closely.`,
      agent: "Respiratory Agent", timestamp: latest.timestamp,
      icdCode: "R09.02", icdDisplay: "Hypoxemia",
      cptCodes: [{ code: "94760", display: "Pulse oximetry (continuous)" }, { code: "82803", display: "Arterial blood gas (ABG)" }],
      treatment: "Nasal cannula O2 2-4L/min, titrate to SpO2 > 94%. Obtain ABG if not improving.",
    });
  }

  // Glucose
  if (v.glucose > 300) {
    recs.push({
      id: String(++id), severity: "critical", title: "Severe Hyperglycemia",
      description: `Blood glucose at ${v.glucose} mg/dL. Check for DKA (ketones, anion gap). Start insulin protocol.`,
      agent: "Glycemic Control Agent", timestamp: latest.timestamp,
      icdCode: "E11.65", icdDisplay: "Type 2 DM with hyperglycemia",
      cptCodes: [{ code: "82947", display: "Blood glucose quantitative" }, { code: "80048", display: "Basic metabolic panel (BMP)" }],
      treatment: "Insulin IV drip 0.1 units/kg/hr, NS 1L/hr x 2hr then 250mL/hr. Monitor BG q1h.",
    });
  } else if (v.glucose > 200) {
    recs.push({
      id: String(++id), severity: "warning", title: "Hyperglycemia Alert",
      description: `Blood glucose elevated at ${v.glucose} mg/dL. Administer correction dose per sliding scale.`,
      agent: "Glycemic Control Agent", timestamp: latest.timestamp,
      icdCode: "R73.9", icdDisplay: "Hyperglycemia, unspecified",
      cptCodes: [{ code: "82947", display: "Blood glucose quantitative" }],
      treatment: "Rapid-acting insulin per sliding scale. Reassess in 2hr.",
    });
  } else if (v.glucose < 70) {
    recs.push({
      id: String(++id), severity: "critical", title: "Hypoglycemia Detected",
      description: `Blood glucose critically low at ${v.glucose} mg/dL. Administer glucose immediately.`,
      agent: "Glycemic Control Agent", timestamp: latest.timestamp,
      icdCode: "E16.2", icdDisplay: "Hypoglycemia, unspecified",
      cptCodes: [{ code: "82947", display: "Blood glucose quantitative" }, { code: "96374", display: "IV push, single drug" }],
      treatment: "If conscious: 15g oral glucose. If unconscious/NPO: D50W 25mL IV push or Glucagon 1mg IM. Hold insulin.",
    });
  }

  // Temperature
  if (v.temperature > 102) {
    recs.push({
      id: String(++id), severity: "critical", title: "High Fever",
      description: `Temperature ${v.temperature}\u00B0F. Obtain blood cultures x2, CBC, lactate. Sepsis screening recommended.`,
      agent: "Infection Control Agent", timestamp: latest.timestamp,
      icdCode: "R50.9", icdDisplay: "Fever, unspecified",
      cptCodes: [{ code: "87040", display: "Blood culture, aerobic" }, { code: "85025", display: "CBC with differential" }, { code: "83605", display: "Lactic acid (lactate)" }],
      treatment: "Acetaminophen 1000mg IV/PO q6h, blood cultures x2, empiric broad-spectrum antibiotics.",
    });
  } else if (v.temperature > 100.4) {
    recs.push({
      id: String(++id), severity: "warning", title: "Fever Detected",
      description: `Temperature ${v.temperature}\u00B0F. Administer antipyretics. Evaluate for infection source.`,
      agent: "Infection Control Agent", timestamp: latest.timestamp,
      icdCode: "R50.9", icdDisplay: "Fever, unspecified",
      cptCodes: [{ code: "85025", display: "CBC with differential" }, { code: "81001", display: "Urinalysis" }],
      treatment: "Acetaminophen 650-1000mg PO q6h. Obtain UA, CBC, CXR if new onset.",
    });
  }

  // Respiratory Rate
  if (v.respRate > 28) {
    recs.push({
      id: String(++id), severity: "critical", title: "Tachypnea -- Respiratory Failure Risk",
      description: `Respiratory rate at ${v.respRate} br/min. Assess for respiratory distress, metabolic acidosis, or anxiety.`,
      agent: "Respiratory Agent", timestamp: latest.timestamp,
      icdCode: "R06.82", icdDisplay: "Tachypnea, not elsewhere classified",
      cptCodes: [{ code: "82803", display: "Arterial blood gas (ABG)" }, { code: "99291", display: "Critical care, first 30-74 min" }],
      treatment: "Supplemental O2, obtain ABG stat. Consider BiPAP or intubation if worsening.",
    });
  } else if (v.respRate > 22) {
    recs.push({
      id: String(++id), severity: "warning", title: "Elevated Respiratory Rate",
      description: `Respiratory rate at ${v.respRate} br/min. Monitor closely.`,
      agent: "Respiratory Agent", timestamp: latest.timestamp,
      icdCode: "R06.82", icdDisplay: "Tachypnea, not elsewhere classified",
      cptCodes: [{ code: "94760", display: "Pulse oximetry (continuous)" }],
      treatment: "Continuous pulse oximetry, address underlying cause.",
    });
  }

  // Multi-vital: SIRS/Sepsis
  if (v.heartRate > 100 && v.systolicBP < 100 && v.temperature > 100.4 && v.respRate > 22) {
    recs.push({
      id: String(++id), severity: "critical", title: "SIRS/Sepsis Criteria Met",
      description: `Multiple abnormalities: HR ${v.heartRate}, BP ${v.systolicBP}/${v.diastolicBP}, Temp ${v.temperature}\u00B0F, RR ${v.respRate}. Activate sepsis bundle.`,
      agent: "Sepsis Screening Agent", timestamp: latest.timestamp,
      icdCode: "A41.9", icdDisplay: "Sepsis, unspecified organism",
      cptCodes: [{ code: "99291", display: "Critical care, first 30-74 min" }, { code: "87040", display: "Blood culture, aerobic" }, { code: "83605", display: "Lactic acid (lactate)" }],
      treatment: "SEP-1 Bundle: Blood cultures x2, Lactate level, NS 30mL/kg IV within 3hr, Broad-spectrum ABX within 1hr. Vasopressors if MAP < 65 after fluids.",
    });
  }

  // Normal
  if (recs.length === 0) {
    recs.push({
      id: "0", severity: "info", title: "All Vitals Within Normal Range",
      description: "No abnormalities detected. Continue routine monitoring per care plan.",
      agent: "Clinical Decision Support", timestamp: latest.timestamp,
      treatment: "Continue current care plan. Next routine vitals check per protocol.",
    });
  }

  return recs;
}

/* ── Placeholder patients ────────────────────────────────────────────────── */

const PLACEHOLDER_PATIENTS = [
  { id: "p1", name: "Maria Garcia" },
  { id: "p2", name: "James Wilson" },
  { id: "p3", name: "Susan Chen" },
  { id: "p4", name: "Robert Johnson" },
];

/* ── Page Component ──────────────────────────────────────────────────────── */

export default function VitalsSimulatorPage() {
  const [selectedPatientId, setSelectedPatientId] = useState("p1");
  const [selectedProfile, setSelectedProfile] = useState(0);
  const [params, setParams] = useState<Record<string, VitalParams>>(() => {
    const p: Record<string, VitalParams> = {};
    for (const cfg of VITAL_CONFIGS) {
      p[cfg.key] = {
        baseline: cfg.defaultBaseline,
        variability: (cfg.normalHigh - cfg.normalLow) * 0.15,
        anomalyChance: 0.05,
      };
    }
    return p;
  });
  const [readings, setReadings] = useState<GeneratedReading[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [intervalMs, setIntervalMs] = useState(2000);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [showConfig, setShowConfig] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const readingCountRef = useRef(0);

  const paramsRef = useRef(params);
  paramsRef.current = params;
  const intervalMsRef = useRef(intervalMs);
  intervalMsRef.current = intervalMs;

  const tick = useCallback(() => {
    readingCountRef.current += 1;
    const timeLabel = `T+${readingCountRef.current * (intervalMsRef.current / 1000)}s`;
    const reading = generateReading(paramsRef.current, timeLabel);

    setReadings((prev) => {
      const next = [...prev, reading];
      const trimmed = next.length > 60 ? next.slice(-60) : next;
      const recs = generateLocalRecommendations(trimmed);
      queueMicrotask(() => setRecommendations(recs));
      return trimmed;
    });
  }, []);

  const startSimulation = () => {
    if (isRunning) return;
    setIsRunning(true);
    readingCountRef.current = 0;
    setReadings([]);
    setRecommendations([]);
    tick();
    timerRef.current = setInterval(tick, intervalMs);
  };

  const stopSimulation = () => {
    setIsRunning(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    if (isRunning && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = setInterval(tick, intervalMs);
    }
  }, [intervalMs, tick, isRunning]);

  const applyProfile = (index: number) => {
    setSelectedProfile(index);
    const profile = PROFILES[index];
    const newParams: Record<string, VitalParams> = {};
    for (const cfg of VITAL_CONFIGS) {
      newParams[cfg.key] = profile.overrides[cfg.key] ?? {
        baseline: cfg.defaultBaseline,
        variability: (cfg.normalHigh - cfg.normalLow) * 0.15,
        anomalyChance: 0.05,
      };
    }
    setParams(newParams);
  };

  const latestReading = readings.length > 0 ? readings[readings.length - 1] : null;

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto animate-fade-in-up">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-600" />
            Vitals Simulator
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Generate realistic vital signs to test AI agent recommendations and alert thresholds
          </p>
          <Link
            href="/simulator/what-if"
            className="text-xs text-indigo-600 hover:text-indigo-700 mt-1 inline-block"
          >
            Switch to What-If Simulator &rarr;
          </Link>
        </div>
        <div className="flex items-center gap-3">
          {/* Patient selector */}
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <select
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              disabled={isRunning}
              className="pl-9 pr-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 appearance-none cursor-pointer disabled:opacity-50"
            >
              {PLACEHOLDER_PATIENTS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Config toggle */}
          <button
            onClick={() => setShowConfig(!showConfig)}
            className={clsx(
              "p-2 rounded-lg border transition-colors",
              showConfig
                ? "bg-indigo-600 text-white border-indigo-600"
                : "bg-white text-gray-400 border-gray-200 hover:text-gray-700"
            )}
            title="Advanced settings"
          >
            <Settings2 className="w-4 h-4" />
          </button>

          {/* Start/Stop */}
          {isRunning ? (
            <button
              onClick={stopSimulation}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
            >
              <Square className="w-4 h-4" /> Stop
            </button>
          ) : (
            <button
              onClick={startSimulation}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
            >
              <Play className="w-4 h-4" /> Start Simulation
            </button>
          )}
        </div>
      </div>

      {/* Simulation Profiles */}
      <div>
        <h2 className="text-sm font-bold text-gray-900 mb-3">Simulation Profiles</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {PROFILES.map((profile, i) => (
            <button
              key={profile.name}
              onClick={() => applyProfile(i)}
              disabled={isRunning}
              className={clsx(
                "p-3 rounded-xl border text-left transition-all disabled:opacity-50",
                selectedProfile === i
                  ? "border-indigo-500 bg-indigo-50 shadow-sm"
                  : "border-gray-200 bg-white hover:border-indigo-300 hover:shadow-sm"
              )}
            >
              <p className="text-xs font-semibold text-gray-900">{profile.name}</p>
              <p className="text-[10px] text-gray-500 mt-1 line-clamp-2">
                {profile.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Configuration */}
      {showConfig && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-gray-900">Advanced Configuration</h2>
            <div className="flex items-center gap-3">
              <label className="text-xs text-gray-500">Interval:</label>
              <select
                value={intervalMs}
                onChange={(e) => setIntervalMs(Number(e.target.value))}
                className="px-2 py-1 rounded border border-gray-200 bg-white text-xs"
              >
                <option value={1000}>1s</option>
                <option value={2000}>2s</option>
                <option value={5000}>5s</option>
                <option value={10000}>10s</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {VITAL_CONFIGS.map((cfg) => {
              const p = params[cfg.key];
              return (
                <div
                  key={cfg.key}
                  className="p-3 rounded-lg bg-gray-50 border border-gray-200"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <cfg.icon className={clsx("w-4 h-4", cfg.color)} />
                    <span className="text-xs font-semibold text-gray-900">
                      {cfg.label}
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-[10px] text-gray-500">
                        <span>Baseline</span>
                        <span className="font-mono">
                          {p.baseline} {cfg.unit}
                        </span>
                      </div>
                      <input
                        type="range"
                        min={cfg.min}
                        max={cfg.max}
                        step={cfg.step}
                        value={p.baseline}
                        onChange={(e) =>
                          setParams((prev) => ({
                            ...prev,
                            [cfg.key]: {
                              ...prev[cfg.key],
                              baseline: Number(e.target.value),
                            },
                          }))
                        }
                        disabled={isRunning}
                        className="w-full h-1.5 accent-indigo-500"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-gray-500">
                        <span>Variability</span>
                        <span className="font-mono">
                          +/-{p.variability.toFixed(1)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={(cfg.max - cfg.min) * 0.3}
                        step={cfg.step}
                        value={p.variability}
                        onChange={(e) =>
                          setParams((prev) => ({
                            ...prev,
                            [cfg.key]: {
                              ...prev[cfg.key],
                              variability: Number(e.target.value),
                            },
                          }))
                        }
                        disabled={isRunning}
                        className="w-full h-1.5 accent-indigo-500"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-gray-500">
                        <span>Anomaly Chance</span>
                        <span className="font-mono">
                          {Math.round(p.anomalyChance * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={p.anomalyChance}
                        onChange={(e) =>
                          setParams((prev) => ({
                            ...prev,
                            [cfg.key]: {
                              ...prev[cfg.key],
                              anomalyChance: Number(e.target.value),
                            },
                          }))
                        }
                        disabled={isRunning}
                        className="w-full h-1.5 accent-indigo-500"
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Live Vital Cards */}
      {latestReading && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {VITAL_CONFIGS.map((cfg) => {
            const value = latestReading.values[cfg.key];
            const status: "normal" | "warning" | "critical" =
              value > cfg.normalHigh * 1.3 || value < cfg.normalLow * 0.7
                ? "critical"
                : value > cfg.normalHigh || value < cfg.normalLow
                  ? "warning"
                  : "normal";

            return (
              <div
                key={cfg.key}
                className={clsx(
                  "rounded-xl border bg-white p-3 shadow-sm transition-all",
                  status === "critical" &&
                    "border-red-400 bg-red-50 animate-pulse",
                  status === "warning" && "border-amber-300 bg-amber-50",
                  status === "normal" && "border-emerald-200 bg-emerald-50/30"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <cfg.icon className={clsx("w-4 h-4", cfg.color)} />
                  {status !== "normal" && (
                    <AlertTriangle
                      className={clsx(
                        "w-3.5 h-3.5",
                        status === "critical"
                          ? "text-red-500"
                          : "text-amber-500"
                      )}
                    />
                  )}
                </div>
                <p className="text-xl font-bold font-mono text-gray-900">
                  {cfg.step < 1 ? value.toFixed(1) : value}
                </p>
                <p className="text-[10px] text-gray-500">{cfg.unit}</p>
                <p className="text-[10px] font-medium text-gray-900 mt-0.5">
                  {cfg.label}
                </p>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Charts */}
        <div className="lg:col-span-2 space-y-4">
          {readings.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {VITAL_CONFIGS.map((cfg) => (
                <div
                  key={cfg.key}
                  className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
                >
                  <h3 className="text-xs font-bold text-gray-900 mb-3 flex items-center gap-2">
                    <cfg.icon className={clsx("w-3.5 h-3.5", cfg.color)} />
                    {cfg.label}
                  </h3>
                  <div style={{ height: 140 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={readings}
                        margin={{ top: 5, right: 8, bottom: 0, left: 0 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="#e5e7eb"
                          strokeOpacity={0.4}
                        />
                        <XAxis
                          dataKey="timestamp"
                          tick={{ fontSize: 9, fill: "#6b7280" }}
                          tickLine={false}
                          axisLine={false}
                          interval="preserveStartEnd"
                        />
                        <YAxis
                          tick={{ fontSize: 9, fill: "#6b7280" }}
                          tickLine={false}
                          axisLine={false}
                          domain={["auto", "auto"]}
                        />
                        <Tooltip
                          formatter={(v: number) => [
                            `${cfg.step < 1 ? v.toFixed(1) : v} ${cfg.unit}`,
                            cfg.label,
                          ]}
                          contentStyle={{
                            background: "#fff",
                            border: "1px solid #e5e7eb",
                            borderRadius: 8,
                            fontSize: 11,
                          }}
                        />
                        <ReferenceLine
                          y={cfg.normalHigh}
                          stroke="#e11d48"
                          strokeDasharray="3 3"
                          strokeOpacity={0.5}
                        />
                        <ReferenceLine
                          y={cfg.normalLow}
                          stroke="#f59e0b"
                          strokeDasharray="3 3"
                          strokeOpacity={0.5}
                        />
                        <Line
                          type="monotone"
                          dataKey={(d: GeneratedReading) => d.values[cfg.key]}
                          stroke={cfg.chartColor}
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ))}
            </div>
          )}

          {readings.length === 0 && !isRunning && (
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm text-center py-16">
              <Zap className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-sm text-gray-500">
                Select a profile and click{" "}
                <strong>Start Simulation</strong> to generate vitals
              </p>
              <p className="text-xs text-gray-400 mt-2">
                AI agents will analyze the generated data and provide
                real-time recommendations
              </p>
            </div>
          )}
        </div>

        {/* AI Recommendations Panel */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm lg:sticky lg:top-6 self-start">
          <div className="flex items-center gap-2 mb-4">
            <BrainCircuit className="w-5 h-5 text-indigo-600" />
            <h2 className="text-sm font-bold text-gray-900">
              AI Recommendations
            </h2>
            {isRunning && (
              <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin ml-auto" />
            )}
          </div>

          {recommendations.length === 0 ? (
            <div className="text-center py-8">
              <BrainCircuit className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-xs text-gray-500">
                Recommendations will appear when simulation starts
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className={clsx(
                    "p-3 rounded-lg border",
                    rec.severity === "critical" &&
                      "border-red-300 bg-red-50",
                    rec.severity === "warning" &&
                      "border-amber-300 bg-amber-50",
                    rec.severity === "info" &&
                      "border-emerald-300 bg-emerald-50"
                  )}
                >
                  <div className="flex items-start gap-2">
                    {rec.severity === "critical" && (
                      <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    )}
                    {rec.severity === "warning" && (
                      <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    )}
                    {rec.severity === "info" && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-gray-900">
                        {rec.title}
                      </p>
                      <p className="text-[11px] text-gray-500 mt-1 leading-relaxed">
                        {rec.description}
                      </p>

                      {/* ICD-10 & CPT Codes */}
                      {rec.icdCode && (
                        <div className="mt-2 space-y-1.5">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded font-mono font-bold">
                              ICD-10: {rec.icdCode}
                            </span>
                            <span className="text-[10px] text-gray-500">
                              {rec.icdDisplay}
                            </span>
                          </div>
                          {rec.cptCodes && rec.cptCodes.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {rec.cptCodes.map((cpt) => (
                                <span
                                  key={cpt.code}
                                  className="text-[10px] px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded font-mono"
                                  title={cpt.display}
                                >
                                  CPT {cpt.code}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Contraindication Warnings */}
                      {rec.contraindications &&
                        rec.contraindications.length > 0 && (
                          <div className="mt-2 p-2 bg-red-50 rounded border border-red-200">
                            <p className="text-[10px] font-semibold text-red-700 mb-1 flex items-center gap-1">
                              <ShieldAlert className="w-3 h-3" />
                              Patient Safety Alerts
                            </p>
                            {rec.contraindications.map((ci, i) => (
                              <p
                                key={i}
                                className="text-[10px] text-red-600 leading-relaxed"
                              >
                                {ci}
                              </p>
                            ))}
                          </div>
                        )}

                      {/* Treatment Plan */}
                      {rec.treatment && (
                        <div className="mt-2 p-2 bg-gray-50 rounded border border-gray-200">
                          <p className="text-[10px] font-semibold text-gray-900 mb-0.5">
                            Recommended Treatment
                          </p>
                          <p className="text-[10px] text-gray-500 leading-relaxed">
                            {rec.treatment}
                          </p>
                        </div>
                      )}

                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 rounded font-medium text-gray-500">
                          {rec.agent}
                        </span>
                        <span className="text-[10px] text-gray-400">
                          {rec.timestamp}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Stats Footer */}
      {readings.length > 0 && (
        <div className="flex items-center gap-6 text-xs text-gray-500">
          <span>
            Readings generated:{" "}
            <strong className="text-gray-900">{readings.length}</strong>
          </span>
          <span>
            Alerts triggered:{" "}
            <strong className="text-gray-900">
              {readings.reduce((sum, r) => sum + r.alerts.length, 0)}
            </strong>
          </span>
          <span>
            AI recommendations:{" "}
            <strong className="text-gray-900">
              {recommendations.length}
            </strong>
          </span>
          {isRunning && (
            <span className="flex items-center gap-1">
              <RefreshCw className="w-3 h-3 animate-spin" /> Simulating every{" "}
              {intervalMs / 1000}s
            </span>
          )}
        </div>
      )}
    </div>
  );
}
