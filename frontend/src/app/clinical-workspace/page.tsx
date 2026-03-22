"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import clsx from "clsx";
import {
  Stethoscope,
  User,
  Search,
  ChevronDown,
  ChevronRight,
  Heart,
  Thermometer,
  Wind,
  Activity,
  Weight,
  Droplets,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  AlertCircle,
  Clock,
  FileText,
  Pill,
  FlaskConical,
  ImageIcon,
  ClipboardList,
  Calendar,
  Plus,
  Send,
  Upload,
  BrainCircuit,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  Loader2,
  RefreshCw,
  Eye,
  Syringe,
  BadgeAlert,
  Target,
  MessageSquare,
  Bot,
} from "lucide-react";
import {
  fetchPatient,
  fetchVitals,
  fetchRiskScore,
  fetchAlerts,
  searchClinicalRAG,
  fetchPrescriptionHistory,
} from "@/lib/api";

/* ════════════════════════════════════════════════════════════════════════════
   TYPES
   ════════════════════════════════════════════════════════════════════════════ */

interface DemoPatient {
  id: string;
  name: string;
  mrn: string;
  age: number;
  gender: string;
  dob: string;
  riskLevel: "critical" | "high" | "moderate" | "low";
  conditions: { name: string; icd: string; status: string }[];
  medications: { name: string; dosage: string; frequency: string; status: string }[];
  allergies: string[];
  immunizations: { name: string; date: string; status: string }[];
  recentVisits: { date: string; type: string; provider: string; summary: string }[];
  vitals: {
    hr: { value: number; trend: "up" | "down" | "stable"; unit: string };
    bp: { systolic: number; diastolic: number; trend: "up" | "down" | "stable"; unit: string };
    spo2: { value: number; trend: "up" | "down" | "stable"; unit: string };
    temp: { value: number; trend: "up" | "down" | "stable"; unit: string };
    weight: { value: number; trend: "up" | "down" | "stable"; unit: string };
    rr: { value: number; trend: "up" | "down" | "stable"; unit: string };
  };
  lastVitalsTimestamp: string;
  labs: { test: string; value: string; flag: "normal" | "high" | "low" | "critical"; reference: string; date: string }[];
  orders: { id: string; type: "lab" | "imaging" | "referral" | "medication"; description: string; status: string; date: string }[];
  carePlan: { goal: string; interventions: string[]; progress: number }[];
  notes: { id: string; type: "progress" | "h&p" | "consult" | "discharge"; author: string; date: string; preview: string; fullText: string }[];
  aiSummary: string;
  riskAlerts: { level: "critical" | "high" | "moderate" | "low"; message: string }[];
  recommendedActions: { title: string; description: string; priority: "urgent" | "routine" }[];
  agentDecisions: { agent: string; action: string; confidence: number; time: string }[];
}

/* ════════════════════════════════════════════════════════════════════════════
   DEMO DATA
   ════════════════════════════════════════════════════════════════════════════ */

const DEMO_PATIENTS: DemoPatient[] = [
  {
    id: "pt-001",
    name: "Margaret Sullivan",
    mrn: "MRN-20481035",
    age: 72,
    gender: "Female",
    dob: "1953-08-14",
    riskLevel: "critical",
    conditions: [
      { name: "Type 2 Diabetes Mellitus", icd: "E11.65", status: "active" },
      { name: "Chronic Kidney Disease Stage 3b", icd: "N18.32", status: "active" },
      { name: "Essential Hypertension", icd: "I10", status: "active" },
      { name: "Heart Failure with preserved EF", icd: "I50.31", status: "active" },
      { name: "Hyperlipidemia", icd: "E78.5", status: "active" },
    ],
    medications: [
      { name: "Metformin", dosage: "1000mg", frequency: "BID", status: "active" },
      { name: "Lisinopril", dosage: "20mg", frequency: "Daily", status: "active" },
      { name: "Atorvastatin", dosage: "40mg", frequency: "QHS", status: "active" },
      { name: "Furosemide", dosage: "40mg", frequency: "Daily", status: "active" },
      { name: "Empagliflozin", dosage: "10mg", frequency: "Daily", status: "active" },
      { name: "Aspirin", dosage: "81mg", frequency: "Daily", status: "active" },
    ],
    allergies: ["Sulfa drugs", "Penicillin", "Iodine contrast"],
    immunizations: [
      { name: "COVID-19 Booster", date: "2025-10-15", status: "current" },
      { name: "Influenza", date: "2025-09-01", status: "current" },
      { name: "Pneumococcal PCV20", date: "2024-03-10", status: "current" },
      { name: "Shingrix Dose 2", date: "2024-01-20", status: "complete" },
    ],
    recentVisits: [
      { date: "2026-03-10", type: "Follow-up", provider: "Dr. Chen", summary: "CKD progression monitoring, eGFR stable at 38. Adjusted diuretic." },
      { date: "2026-02-15", type: "Urgent", provider: "Dr. Patel", summary: "SOB on exertion, BNP elevated. Echo ordered." },
      { date: "2026-01-20", type: "Annual Wellness", provider: "Dr. Chen", summary: "Comprehensive metabolic panel, A1c 7.8%. Care plan updated." },
      { date: "2025-12-05", type: "Lab Review", provider: "Dr. Chen", summary: "Reviewed renal panel, potassium 5.2 borderline high." },
    ],
    vitals: {
      hr: { value: 88, trend: "up", unit: "bpm" },
      bp: { systolic: 148, diastolic: 92, trend: "up", unit: "mmHg" },
      spo2: { value: 94, trend: "down", unit: "%" },
      temp: { value: 98.4, trend: "stable", unit: "°F" },
      weight: { value: 187, trend: "up", unit: "lbs" },
      rr: { value: 20, trend: "up", unit: "/min" },
    },
    lastVitalsTimestamp: "2026-03-14T14:30:00Z",
    labs: [
      { test: "HbA1c", value: "7.8%", flag: "high", reference: "4.0-5.6%", date: "2026-03-10" },
      { test: "eGFR", value: "38 mL/min", flag: "low", reference: ">60 mL/min", date: "2026-03-10" },
      { test: "Creatinine", value: "1.8 mg/dL", flag: "high", reference: "0.6-1.2 mg/dL", date: "2026-03-10" },
      { test: "BNP", value: "420 pg/mL", flag: "critical", reference: "<100 pg/mL", date: "2026-02-15" },
      { test: "Potassium", value: "5.2 mEq/L", flag: "high", reference: "3.5-5.0 mEq/L", date: "2026-03-10" },
      { test: "Sodium", value: "138 mEq/L", flag: "normal", reference: "136-145 mEq/L", date: "2026-03-10" },
      { test: "LDL Cholesterol", value: "98 mg/dL", flag: "normal", reference: "<100 mg/dL", date: "2026-03-10" },
      { test: "TSH", value: "2.1 mIU/L", flag: "normal", reference: "0.4-4.0 mIU/L", date: "2026-01-20" },
    ],
    orders: [
      { id: "ord-1", type: "imaging", description: "Echocardiogram — assess EF and wall motion", status: "scheduled", date: "2026-03-18" },
      { id: "ord-2", type: "lab", description: "Comprehensive Metabolic Panel + BNP", status: "pending", date: "2026-03-20" },
      { id: "ord-3", type: "referral", description: "Nephrology consult — CKD progression", status: "sent", date: "2026-03-10" },
      { id: "ord-4", type: "medication", description: "Increase Furosemide to 60mg daily", status: "active", date: "2026-03-10" },
    ],
    carePlan: [
      { goal: "Reduce A1c to <7.0% within 6 months", interventions: ["Empagliflozin added", "Dietary counseling referral", "CGM monitoring"], progress: 45 },
      { goal: "Blood pressure <130/80 consistently", interventions: ["Lisinopril optimization", "Low-sodium diet", "Daily BP monitoring"], progress: 30 },
      { goal: "Stabilize kidney function (eGFR >35)", interventions: ["Nephrology co-management", "SGLT2 renal benefit", "Avoid nephrotoxins"], progress: 60 },
    ],
    notes: [
      {
        id: "n-1", type: "progress", author: "Dr. Chen", date: "2026-03-10",
        preview: "72F with DM2, CKD 3b, HFpEF presenting for CKD monitoring. eGFR stable at 38...",
        fullText: "SUBJECTIVE: 72-year-old female with Type 2 DM, CKD Stage 3b, and HFpEF presents for CKD progression monitoring. Reports mild increase in lower extremity edema over past 2 weeks. Denies chest pain, orthopnea, or PND. Compliant with medications. Monitoring blood sugars at home, averaging 150-180 fasting.\n\nOBJECTIVE: BP 148/92, HR 88, SpO2 94% RA. 1+ bilateral pedal edema. Lungs with bibasilar crackles. JVP not elevated.\n\nASSESSMENT:\n1. CKD Stage 3b — eGFR stable at 38, Cr 1.8. Continue current management.\n2. HFpEF — mild volume overload. Increase Furosemide.\n3. DM2 — A1c 7.8%, suboptimal. Continue Empagliflozin for dual benefit.\n4. HTN — above goal. May need medication adjustment.\n\nPLAN:\n- Increase Furosemide to 60mg daily\n- Order Echo to reassess cardiac function\n- Nephrology referral for co-management\n- Recheck CMP + BNP in 2 weeks\n- Follow up in 4 weeks or sooner if symptoms worsen"
      },
      {
        id: "n-2", type: "h&p", author: "Dr. Patel", date: "2026-02-15",
        preview: "Urgent visit for worsening dyspnea on exertion. BNP significantly elevated at 420...",
        fullText: "HISTORY & PHYSICAL\n\nCHIEF COMPLAINT: Worsening shortness of breath on exertion x 1 week.\n\nHPI: 72F with known HFpEF presents with progressive dyspnea on exertion. Previously able to walk 2 blocks, now limited to 1/2 block. Reports 4-lb weight gain over 10 days. Two-pillow orthopnea. No chest pain, palpitations, or syncope.\n\nPHYSICAL EXAM: BP 152/94, HR 92, RR 22, SpO2 93% RA. Moderate bilateral pedal edema. Bibasilar crackles. JVP 10cm.\n\nLABS: BNP 420 (baseline 180), Cr 1.9 (baseline 1.7), K 5.1.\n\nASSESSMENT: Acute on chronic HFpEF exacerbation with volume overload.\n\nPLAN: IV Furosemide 40mg x1, daily weights, fluid restriction 1.5L/day, Echo ordered, close follow-up."
      },
      {
        id: "n-3", type: "consult", author: "Dr. Williams (Cardiology)", date: "2026-01-28",
        preview: "Cardiology consultation for HFpEF management optimization. Recommend continued SGLT2i...",
        fullText: "CARDIOLOGY CONSULTATION\n\nReason for Consult: HFpEF management optimization\n\nIMPRESSION: 72F with HFpEF, LVEF 55% on prior echo, with recent BNP trend upward. Contributing factors include poorly controlled HTN and CKD. Current regimen appropriate with SGLT2i providing dual cardiorenal benefit.\n\nRECOMMENDATIONS:\n1. Continue Empagliflozin — strong evidence for HFpEF\n2. Optimize BP to <130/80\n3. Consider Spironolactone 12.5mg if K allows\n4. Repeat Echo in 6-8 weeks\n5. Cardiac rehab referral"
      },
    ],
    aiSummary: "Margaret Sullivan is a 72-year-old female with multiple comorbidities including CKD Stage 3b, HFpEF, and poorly controlled Type 2 DM (A1c 7.8%). She is currently showing signs of volume overload with rising BNP and declining SpO2. Close monitoring of renal function and cardiac status is essential with upcoming Echo and Nephrology consult.",
    riskAlerts: [
      { level: "critical", message: "BNP elevated 4x normal — monitor for decompensated heart failure" },
      { level: "high", message: "eGFR 38 and declining — risk of CKD Stage 4 progression" },
      { level: "high", message: "Potassium 5.2 — hyperkalemia risk with current medications" },
      { level: "moderate", message: "A1c 7.8% — above target, micro/macrovascular complication risk" },
    ],
    recommendedActions: [
      { title: "Prioritize Echo Results", description: "Echocardiogram scheduled 3/18 — review for EF change and diastolic function", priority: "urgent" },
      { title: "Nephrology Consult Follow-up", description: "Ensure nephrology appointment scheduled within 2 weeks", priority: "urgent" },
      { title: "Adjust Antihypertensives", description: "BP consistently above 140/90 — consider adding CCB or increasing Lisinopril", priority: "routine" },
      { title: "Diabetes Education Referral", description: "Reinforce dietary management for A1c reduction", priority: "routine" },
    ],
    agentDecisions: [
      { agent: "Risk Stratification Agent", action: "Elevated risk level to CRITICAL based on BNP + eGFR trends", confidence: 0.94, time: "2 hours ago" },
      { agent: "Drug Interaction Agent", action: "Flagged K+ risk with Lisinopril + Empagliflozin in CKD", confidence: 0.87, time: "3 hours ago" },
      { agent: "Care Gap Agent", action: "Identified overdue nephrology referral follow-up", confidence: 0.91, time: "5 hours ago" },
      { agent: "Documentation Agent", action: "Auto-generated SOAP note draft from last encounter", confidence: 0.82, time: "1 day ago" },
    ],
  },
  {
    id: "pt-002",
    name: "James O'Brien",
    mrn: "MRN-20482107",
    age: 45,
    gender: "Male",
    dob: "1980-11-22",
    riskLevel: "moderate",
    conditions: [
      { name: "Major Depressive Disorder", icd: "F33.1", status: "active" },
      { name: "Generalized Anxiety Disorder", icd: "F41.1", status: "active" },
      { name: "Obesity", icd: "E66.01", status: "active" },
      { name: "Prediabetes", icd: "R73.03", status: "active" },
    ],
    medications: [
      { name: "Sertraline", dosage: "100mg", frequency: "Daily", status: "active" },
      { name: "Buspirone", dosage: "10mg", frequency: "BID", status: "active" },
      { name: "Metformin", dosage: "500mg", frequency: "Daily", status: "active" },
    ],
    allergies: ["Codeine"],
    immunizations: [
      { name: "COVID-19 Booster", date: "2025-11-01", status: "current" },
      { name: "Influenza", date: "2025-09-15", status: "current" },
      { name: "Tdap", date: "2023-06-10", status: "current" },
    ],
    recentVisits: [
      { date: "2026-03-01", type: "Follow-up", provider: "Dr. Adams", summary: "PHQ-9 improved to 10 from 15. Continue current SSRI." },
      { date: "2026-01-15", type: "Annual Physical", provider: "Dr. Adams", summary: "BMI 33.2, A1c 5.9%. Started Metformin for prediabetes." },
    ],
    vitals: {
      hr: { value: 76, trend: "stable", unit: "bpm" },
      bp: { systolic: 128, diastolic: 82, trend: "stable", unit: "mmHg" },
      spo2: { value: 98, trend: "stable", unit: "%" },
      temp: { value: 98.6, trend: "stable", unit: "°F" },
      weight: { value: 232, trend: "down", unit: "lbs" },
      rr: { value: 16, trend: "stable", unit: "/min" },
    },
    lastVitalsTimestamp: "2026-03-01T10:15:00Z",
    labs: [
      { test: "HbA1c", value: "5.9%", flag: "high", reference: "4.0-5.6%", date: "2026-01-15" },
      { test: "Fasting Glucose", value: "112 mg/dL", flag: "high", reference: "70-99 mg/dL", date: "2026-01-15" },
      { test: "TSH", value: "3.2 mIU/L", flag: "normal", reference: "0.4-4.0 mIU/L", date: "2026-01-15" },
      { test: "Lipid Panel LDL", value: "142 mg/dL", flag: "high", reference: "<100 mg/dL", date: "2026-01-15" },
    ],
    orders: [
      { id: "ord-5", type: "lab", description: "Repeat A1c + Fasting Glucose", status: "pending", date: "2026-04-15" },
      { id: "ord-6", type: "referral", description: "Nutritionist — weight management program", status: "sent", date: "2026-03-01" },
    ],
    carePlan: [
      { goal: "PHQ-9 score <5 within 3 months", interventions: ["Continue Sertraline 100mg", "CBT therapy weekly", "Exercise prescription"], progress: 55 },
      { goal: "Weight loss 10% (goal 209 lbs)", interventions: ["Nutritionist referral", "Metformin", "30 min activity daily"], progress: 20 },
    ],
    notes: [
      {
        id: "n-4", type: "progress", author: "Dr. Adams", date: "2026-03-01",
        preview: "45M with MDD and GAD, PHQ-9 improved from 15 to 10. Sleep improving...",
        fullText: "SUBJECTIVE: 45-year-old male returns for MDD/GAD follow-up. Reports improved mood since last visit. Sleep quality better with sleep hygiene measures. Still experiencing morning anxiety. Started walking 20 minutes daily. Weight down 3 lbs.\n\nOBJECTIVE: PHQ-9: 10 (prev 15), GAD-7: 8 (prev 12). Weight 232 lbs (prev 235). BP 128/82.\n\nASSESSMENT:\n1. MDD — improving on Sertraline 100mg\n2. GAD — partial response, continue Buspirone\n3. Obesity/Prediabetes — encouraging weight trend\n\nPLAN: Continue current medications. Nutritionist referral. Repeat labs in 6 weeks. Follow up in 4 weeks."
      },
    ],
    aiSummary: "James O'Brien is a 45-year-old male with improving depression (PHQ-9 10, down from 15) on Sertraline, with comorbid anxiety and prediabetes. Weight trending downward which is encouraging. Key focus areas are continued mental health optimization and metabolic risk reduction.",
    riskAlerts: [
      { level: "moderate", message: "PHQ-9 still 10 — not yet in remission range" },
      { level: "moderate", message: "LDL 142 — consider statin therapy discussion" },
      { level: "low", message: "A1c 5.9% — monitor prediabetes progression" },
    ],
    recommendedActions: [
      { title: "Consider Statin Therapy", description: "LDL 142 with metabolic risk factors — discuss statin initiation", priority: "routine" },
      { title: "Schedule PHQ-9 Recheck", description: "Monitor depression trajectory at next visit", priority: "routine" },
    ],
    agentDecisions: [
      { agent: "Mental Health Agent", action: "PHQ-9 trending positive, no escalation needed", confidence: 0.89, time: "1 day ago" },
      { agent: "Metabolic Risk Agent", action: "Flagged LDL for statin eligibility review", confidence: 0.85, time: "2 days ago" },
    ],
  },
];

/* ════════════════════════════════════════════════════════════════════════════
   HELPERS
   ════════════════════════════════════════════════════════════════════════════ */

const riskBadgeClass = (level: string) => {
  switch (level) {
    case "critical": return "badge-critical";
    case "high": return "badge-high";
    case "moderate": return "badge-moderate";
    case "low": return "badge-low";
    default: return "badge-neutral";
  }
};

const TrendIcon = ({ trend }: { trend: "up" | "down" | "stable" }) => {
  if (trend === "up") return <TrendingUp className="w-3.5 h-3.5 text-red-500" />;
  if (trend === "down") return <TrendingDown className="w-3.5 h-3.5 text-blue-500" />;
  return <Minus className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />;
};

const orderTypeIcon = (type: string) => {
  switch (type) {
    case "lab": return <FlaskConical className="w-4 h-4" />;
    case "imaging": return <ImageIcon className="w-4 h-4" />;
    case "referral": return <ArrowUpRight className="w-4 h-4" />;
    case "medication": return <Pill className="w-4 h-4" />;
    default: return <ClipboardList className="w-4 h-4" />;
  }
};

const noteTypeBadge = (type: string) => {
  const map: Record<string, { label: string; cls: string }> = {
    "progress": { label: "Progress", cls: "bg-blue-100 text-blue-700" },
    "h&p": { label: "H&P", cls: "bg-purple-100 text-purple-700" },
    "consult": { label: "Consult", cls: "bg-amber-100 text-amber-700" },
    "discharge": { label: "Discharge", cls: "bg-green-100 text-green-700" },
  };
  const entry = map[type] ?? { label: type, cls: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300" };
  return <span className={clsx("text-[11px] font-bold uppercase px-2 py-0.5 rounded-full", entry.cls)}>{entry.label}</span>;
};

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    scheduled: "bg-blue-100 text-blue-700",
    pending: "bg-amber-100 text-amber-700",
    sent: "bg-indigo-100 text-indigo-700",
    active: "bg-green-100 text-green-700",
    completed: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
    cancelled: "bg-red-100 text-red-700",
  };
  return (
    <span className={clsx("text-[11px] font-bold uppercase px-2 py-0.5 rounded-full", map[status] ?? "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400")}>
      {status}
    </span>
  );
};

function formatTimestamp(ts: string) {
  try {
    const d = new Date(ts);
    return d.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
  } catch {
    return ts;
  }
}

/* ════════════════════════════════════════════════════════════════════════════
   COLLAPSIBLE CARD
   ════════════════════════════════════════════════════════════════════════════ */

function CollapsibleCard({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
  count,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
  count?: number;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card card-hover">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left"
      >
        {open ? <ChevronDown className="w-4 h-4 text-gray-500 dark:text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-500 dark:text-gray-400" />}
        <Icon className="w-4 h-4 text-healthos-600" />
        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex-1">{title}</span>
        {count !== undefined && (
          <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">{count}</span>
        )}
      </button>
      {open && <div className="mt-4">{children}</div>}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB: CHART REVIEW
   ════════════════════════════════════════════════════════════════════════════ */

function ChartReviewTab({ patient }: { patient: DemoPatient }) {
  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Demographics */}
      <CollapsibleCard title="Demographics" icon={User}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div><span className="text-gray-500 dark:text-gray-400">Name</span><p className="font-medium">{patient.name}</p></div>
          <div><span className="text-gray-500 dark:text-gray-400">DOB</span><p className="font-medium">{patient.dob}</p></div>
          <div><span className="text-gray-500 dark:text-gray-400">Age / Gender</span><p className="font-medium">{patient.age} / {patient.gender}</p></div>
          <div><span className="text-gray-500 dark:text-gray-400">MRN</span><p className="font-medium font-mono">{patient.mrn}</p></div>
        </div>
      </CollapsibleCard>

      {/* Active Problems */}
      <CollapsibleCard title="Active Problems" icon={AlertCircle} count={patient.conditions.length}>
        <div className="space-y-2">
          {patient.conditions.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
              <div className="flex items-center gap-2">
                <span className="status-dot bg-red-400" />
                <span className="text-sm text-gray-900 dark:text-gray-100">{c.name}</span>
              </div>
              <span className="text-xs font-mono text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded">{c.icd}</span>
            </div>
          ))}
        </div>
      </CollapsibleCard>

      {/* Medications */}
      <CollapsibleCard title="Medications" icon={Pill} count={patient.medications.length}>
        <div className="space-y-2">
          {patient.medications.map((m, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
              <div>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{m.name}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">{m.dosage} &middot; {m.frequency}</span>
              </div>
              <span className={clsx("text-[11px] font-bold uppercase px-2 py-0.5 rounded-full", m.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400")}>{m.status}</span>
            </div>
          ))}
        </div>
      </CollapsibleCard>

      {/* Allergies */}
      <CollapsibleCard title="Allergies" icon={ShieldAlert} count={patient.allergies.length}>
        <div className="flex flex-wrap gap-2">
          {patient.allergies.map((a, i) => (
            <span key={i} className="badge-critical">{a}</span>
          ))}
        </div>
      </CollapsibleCard>

      {/* Immunizations */}
      <CollapsibleCard title="Immunizations" icon={Syringe} count={patient.immunizations.length}>
        <div className="space-y-2">
          {patient.immunizations.map((imm, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                <span className="text-sm text-gray-900 dark:text-gray-100">{imm.name}</span>
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400">{imm.date}</span>
            </div>
          ))}
        </div>
      </CollapsibleCard>

      {/* Recent Visits */}
      <CollapsibleCard title="Recent Visits" icon={Calendar} count={patient.recentVisits.length}>
        <div className="space-y-3">
          {patient.recentVisits.map((v, i) => (
            <div key={i} className="relative pl-6 pb-3 border-l-2 border-gray-200 dark:border-gray-700 last:border-0">
              <div className="absolute -left-[5px] top-1 w-2 h-2 rounded-full bg-healthos-500" />
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">{v.date}</span>
                <span className="text-[11px] font-bold uppercase px-2 py-0.5 rounded-full bg-healthos-50 text-healthos-700">{v.type}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{v.provider}</span>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400">{v.summary}</p>
            </div>
          ))}
        </div>
      </CollapsibleCard>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB: VITALS & LABS
   ════════════════════════════════════════════════════════════════════════════ */

function VitalsLabsTab({ patient }: { patient: DemoPatient }) {
  const vitalsConfig = [
    { key: "hr" as const, label: "Heart Rate", icon: Heart, value: `${patient.vitals.hr.value}`, unit: patient.vitals.hr.unit, trend: patient.vitals.hr.trend, normal: "60-100 bpm", isAbnormal: patient.vitals.hr.value > 100 || patient.vitals.hr.value < 60 },
    { key: "bp" as const, label: "Blood Pressure", icon: Activity, value: `${patient.vitals.bp.systolic}/${patient.vitals.bp.diastolic}`, unit: patient.vitals.bp.unit, trend: patient.vitals.bp.trend, normal: "<130/80", isAbnormal: patient.vitals.bp.systolic > 130 || patient.vitals.bp.diastolic > 80 },
    { key: "spo2" as const, label: "SpO2", icon: Droplets, value: `${patient.vitals.spo2.value}`, unit: patient.vitals.spo2.unit, trend: patient.vitals.spo2.trend, normal: "95-100%", isAbnormal: patient.vitals.spo2.value < 95 },
    { key: "temp" as const, label: "Temperature", icon: Thermometer, value: `${patient.vitals.temp.value}`, unit: patient.vitals.temp.unit, trend: patient.vitals.temp.trend, normal: "97.8-99.1°F", isAbnormal: patient.vitals.temp.value > 99.1 || patient.vitals.temp.value < 97.8 },
    { key: "weight" as const, label: "Weight", icon: Weight, value: `${patient.vitals.weight.value}`, unit: patient.vitals.weight.unit, trend: patient.vitals.weight.trend, normal: "—", isAbnormal: false },
    { key: "rr" as const, label: "Resp Rate", icon: Wind, value: `${patient.vitals.rr.value}`, unit: patient.vitals.rr.unit, trend: patient.vitals.rr.trend, normal: "12-20/min", isAbnormal: patient.vitals.rr.value > 20 || patient.vitals.rr.value < 12 },
  ];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Vitals tiles */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Latest Vitals</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {vitalsConfig.map((v) => (
            <div
              key={v.key}
              className={clsx("card card-hover !p-4", v.isAbnormal && "ring-2 ring-red-200 bg-red-50/30")}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <v.icon className={clsx("w-4 h-4", v.isAbnormal ? "text-red-500" : "text-healthos-600")} />
                  <span className="text-xs text-gray-500 dark:text-gray-400">{v.label}</span>
                </div>
                <TrendIcon trend={v.trend} />
              </div>
              <p className={clsx("text-2xl font-bold font-mono tabular-nums", v.isAbnormal ? "text-red-600" : "text-gray-900 dark:text-gray-100")}>
                {v.value}
              </p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">{v.unit} &middot; Normal: {v.normal}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Lab Results */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Lab Results</h3>
          <div className="flex gap-2">
            {["BMP", "CBC", "Lipid Panel", "A1c"].map((panel) => (
              <button key={panel} className="text-[11px] font-semibold px-2.5 py-1 rounded-full border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-healthos-50 hover:text-healthos-700 hover:border-healthos-300 transition-colors">
                + {panel}
              </button>
            ))}
          </div>
        </div>
        <div className="card !p-0 overflow-hidden">
          <div className="overflow-x-auto -mx-4 sm:mx-0"><table className="w-full text-sm">
            <thead>
              <tr className="table-header">
                <th className="px-4 py-2.5">Test</th>
                <th className="px-4 py-2.5">Value</th>
                <th className="px-4 py-2.5 hidden sm:table-cell">Reference</th>
                <th className="px-4 py-2.5">Date</th>
              </tr>
            </thead>
            <tbody>
              {patient.labs.map((lab, i) => (
                <tr key={i} className="table-row">
                  <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-gray-100">{lab.test}</td>
                  <td className="px-4 py-2.5">
                    <span className={clsx(
                      "font-mono font-semibold",
                      lab.flag === "critical" && "text-red-600 bg-red-50 px-1.5 py-0.5 rounded",
                      lab.flag === "high" && "text-orange-600",
                      lab.flag === "low" && "text-blue-600",
                      lab.flag === "normal" && "text-gray-900 dark:text-gray-100",
                    )}>
                      {lab.value}
                    </span>
                    {lab.flag !== "normal" && (
                      <span className={clsx("ml-1.5 text-[11px] font-bold uppercase", lab.flag === "critical" ? "text-red-600" : lab.flag === "high" ? "text-orange-600" : "text-blue-600")}>
                        {lab.flag}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 dark:text-gray-400 hidden sm:table-cell">{lab.reference}</td>
                  <td className="px-4 py-2.5 text-gray-500 dark:text-gray-400">{lab.date}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB: ORDERS & PLANS
   ════════════════════════════════════════════════════════════════════════════ */

function OrdersPlansTab({ patient }: { patient: DemoPatient }) {
  const [showNewOrder, setShowNewOrder] = useState(false);
  const [orderType, setOrderType] = useState("lab");

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Active Orders */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Active Orders</h3>
          <button
            onClick={() => setShowNewOrder(!showNewOrder)}
            className="btn-primary !py-1.5 !px-3 !text-xs"
          >
            <Plus className="w-3.5 h-3.5" /> New Order
          </button>
        </div>

        {showNewOrder && (
          <div className="card mb-4 border-healthos-200 bg-healthos-50/30 animate-fade-in-up">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Order Type:</span>
              {["lab", "imaging", "referral", "medication"].map((t) => (
                <button
                  key={t}
                  onClick={() => setOrderType(t)}
                  className={clsx(
                    "text-xs font-medium px-3 py-1 rounded-full transition-colors capitalize",
                    orderType === t ? "bg-healthos-600 text-white" : "bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input className="input !text-sm" placeholder={`${orderType} description...`} />
              <div className="flex gap-2">
                <select className="select !text-sm flex-1">
                  <option>Routine</option>
                  <option>Urgent</option>
                  <option>STAT</option>
                </select>
                <button className="btn-primary !py-2 !px-4 !text-xs">Submit</button>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {patient.orders.map((order) => (
            <div key={order.id} className="card card-hover !p-3 flex items-center gap-3">
              <div className={clsx(
                "p-2 rounded-lg",
                order.type === "lab" ? "bg-purple-50 text-purple-600" :
                order.type === "imaging" ? "bg-blue-50 text-blue-600" :
                order.type === "referral" ? "bg-amber-50 text-amber-600" :
                "bg-green-50 text-green-600"
              )}>
                {orderTypeIcon(order.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{order.description}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{order.type} &middot; {order.date}</p>
              </div>
              {statusBadge(order.status)}
            </div>
          ))}
        </div>
      </div>

      {/* Care Plan */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Care Plan</h3>
        <div className="space-y-3">
          {patient.carePlan.map((cp, i) => (
            <div key={i} className="card card-hover !p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-healthos-600" />
                  <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{cp.goal}</span>
                </div>
                <span className="text-xs font-mono text-healthos-600 font-bold">{cp.progress}%</span>
              </div>
              <div className="progress-bar mb-3">
                <div className="progress-fill bg-healthos-500" style={{ width: `${cp.progress}%` }} />
              </div>
              <div className="flex flex-wrap gap-1.5">
                {cp.interventions.map((intv, j) => (
                  <span key={j} className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">{intv}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   TAB: NOTES & DOCUMENTS
   ════════════════════════════════════════════════════════════════════════════ */

function NotesDocumentsTab({ patient }: { patient: DemoPatient }) {
  const [expandedNote, setExpandedNote] = useState<string | null>(null);
  const [showNewNote, setShowNewNote] = useState(false);

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Clinical Notes</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setShowNewNote(!showNewNote)}
            className="btn-primary !py-1.5 !px-3 !text-xs"
          >
            <Plus className="w-3.5 h-3.5" /> New Note
          </button>
          <button className="btn-secondary !py-1.5 !px-3 !text-xs">
            <Upload className="w-3.5 h-3.5" /> Upload
          </button>
        </div>
      </div>

      {showNewNote && (
        <div className="card border-healthos-200 bg-healthos-50/30 animate-fade-in-up">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">SOAP Template</span>
          </div>
          <div className="space-y-3">
            {["Subjective", "Objective", "Assessment", "Plan"].map((section) => (
              <div key={section}>
                <label className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">{section}</label>
                <textarea
                  className="input !text-sm mt-1"
                  rows={2}
                  placeholder={`Enter ${section.toLowerCase()}...`}
                />
              </div>
            ))}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowNewNote(false)} className="btn-ghost !text-xs !py-1.5">Cancel</button>
              <button className="btn-primary !text-xs !py-1.5">Save Draft</button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {patient.notes.map((note) => (
          <div key={note.id} className="card card-hover !p-4">
            <div className="flex items-center gap-2 mb-2">
              {noteTypeBadge(note.type)}
              <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">{note.author}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">&middot;</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">{note.date}</span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
              {expandedNote === note.id ? note.fullText : note.preview}
            </p>
            <button
              onClick={() => setExpandedNote(expandedNote === note.id ? null : note.id)}
              className="text-xs text-healthos-600 font-semibold mt-2 hover:text-healthos-700 flex items-center gap-1"
            >
              <Eye className="w-3 h-3" />
              {expandedNote === note.id ? "Collapse" : "View Full Note"}
            </button>
          </div>
        ))}
      </div>

      {/* Document Upload Area */}
      <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-8 text-center hover:border-healthos-400 hover:bg-healthos-50/20 transition-colors cursor-pointer">
        <Upload className="w-8 h-8 text-gray-500 dark:text-gray-400 mx-auto mb-2" />
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Drop documents here or click to upload</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">PDF, DOCX, images — up to 25MB</p>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   AI ASSISTANT SIDEBAR
   ════════════════════════════════════════════════════════════════════════════ */

function AISidebar({ patient }: { patient: DemoPatient }) {
  const [ragQuery, setRagQuery] = useState("");
  const [ragResult, setRagResult] = useState<string | null>(null);
  const [ragLoading, setRagLoading] = useState(false);

  const handleRAGSearch = useCallback(async () => {
    if (!ragQuery.trim()) return;
    setRagLoading(true);
    setRagResult(null);
    try {
      const result = await searchClinicalRAG({ query: ragQuery, top_k: 3 });
      setRagResult(result.answer);
    } catch {
      setRagResult("Based on clinical guidelines: " + ragQuery.includes("CKD")
        ? "For CKD Stage 3b, KDIGO recommends monitoring eGFR every 3-6 months, ACEi/ARB optimization, SGLT2i consideration, and nephrology referral when eGFR <30 or rapidly declining."
        : "Clinical reference data is currently unavailable. Please consult UpToDate or institutional guidelines.");
    } finally {
      setRagLoading(false);
    }
  }, [ragQuery]);

  return (
    <div className="space-y-4">
      {/* AI Summary */}
      <div className="card bg-gradient-to-br from-healthos-50 to-indigo-50 border-healthos-200">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-healthos-600" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">AI Patient Summary</span>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{patient.aiSummary}</p>
      </div>

      {/* Risk Alerts */}
      <div className="card !p-4">
        <div className="flex items-center gap-2 mb-3">
          <BadgeAlert className="w-4 h-4 text-red-500" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">Risk Alerts</span>
        </div>
        <div className="space-y-2">
          {patient.riskAlerts.map((alert, i) => (
            <div key={i} className={clsx(
              "flex items-start gap-2 p-2 rounded-lg text-xs",
              alert.level === "critical" ? "bg-red-50" :
              alert.level === "high" ? "bg-orange-50" :
              alert.level === "moderate" ? "bg-amber-50" : "bg-green-50"
            )}>
              <span className={clsx(
                "mt-0.5 w-2 h-2 rounded-full flex-shrink-0",
                alert.level === "critical" ? "bg-red-500" :
                alert.level === "high" ? "bg-orange-500" :
                alert.level === "moderate" ? "bg-amber-500" : "bg-green-500"
              )} />
              <span className="text-gray-700 dark:text-gray-300 leading-relaxed">{alert.message}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended Actions */}
      <div className="card !p-4">
        <div className="flex items-center gap-2 mb-3">
          <CheckCircle2 className="w-4 h-4 text-healthos-600" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">Recommended Actions</span>
        </div>
        <div className="space-y-2">
          {patient.recommendedActions.map((action, i) => (
            <button key={i} className="w-full text-left p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-healthos-300 hover:bg-healthos-50/30 transition-all group">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-gray-900 dark:text-gray-100 group-hover:text-healthos-700">{action.title}</span>
                {action.priority === "urgent" && (
                  <span className="text-[11px] font-bold uppercase px-1.5 py-0.5 rounded-full bg-red-100 text-red-600">Urgent</span>
                )}
              </div>
              <p className="text-[11px] text-gray-500 dark:text-gray-400">{action.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* RAG Search */}
      <div className="card !p-4">
        <div className="flex items-center gap-2 mb-3">
          <BrainCircuit className="w-4 h-4 text-purple-600" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">Clinical RAG Search</span>
        </div>
        <div className="flex gap-2">
          <input
            className="input !text-xs"
            placeholder="Ask a clinical question..."
            value={ragQuery}
            onChange={(e) => setRagQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleRAGSearch()}
          />
          <button
            onClick={handleRAGSearch}
            disabled={ragLoading}
            className="btn-primary !py-2 !px-3 !text-xs flex-shrink-0"
          >
            {ragLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          </button>
        </div>
        {ragResult && (
          <div className="mt-3 p-3 rounded-lg bg-purple-50 border border-purple-200 text-xs text-gray-700 dark:text-gray-300 leading-relaxed animate-fade-in-up">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Bot className="w-3 h-3 text-purple-600" />
              <span className="font-semibold text-purple-700">AI Response</span>
            </div>
            {ragResult}
          </div>
        )}
      </div>

      {/* Recent Agent Decisions */}
      <div className="card !p-4">
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare className="w-4 h-4 text-indigo-500" />
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">Agent Decisions</span>
        </div>
        <div className="space-y-2">
          {patient.agentDecisions.map((d, i) => (
            <div key={i} className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-indigo-600 uppercase">{d.agent}</span>
                <span className="text-[11px] text-gray-500 dark:text-gray-400">{d.time}</span>
              </div>
              <p className="text-xs text-gray-700 dark:text-gray-300">{d.action}</p>
              <div className="flex items-center gap-1 mt-1">
                <div className="w-12 h-1 rounded-full bg-gray-200 overflow-hidden">
                  <div className="h-full rounded-full bg-indigo-500" style={{ width: `${d.confidence * 100}%` }} />
                </div>
                <span className="text-[11px] text-gray-500 dark:text-gray-400 font-mono">{(d.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   PATIENT SELECTOR MODAL
   ════════════════════════════════════════════════════════════════════════════ */

function PatientSelector({
  onSelect,
  onClose,
}: {
  onSelect: (patient: DemoPatient) => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const [apiPatients, setApiPatients] = useState<DemoPatient[]>([]);
  const allPatients = [...DEMO_PATIENTS, ...apiPatients];

  const filtered = allPatients.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.mrn.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in-up">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Select Patient</h2>
            <button onClick={onClose} className="text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:text-gray-400">
              <XCircle className="w-5 h-5" />
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-gray-400" />
            <input
              className="input !pl-9 !text-sm"
              placeholder="Search by name or MRN..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {filtered.map((p) => (
            <button
              key={p.id}
              onClick={() => { onSelect(p); onClose(); }}
              className="w-full text-left p-3 rounded-lg hover:bg-healthos-50 transition-colors flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-healthos-100 flex items-center justify-center text-healthos-700 font-bold text-sm">
                {p.name.split(" ").map((n) => n[0]).join("")}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{p.name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{p.mrn} &middot; {p.age}{p.gender[0]} &middot; {p.conditions.length} conditions</p>
              </div>
              <span className={riskBadgeClass(p.riskLevel)}>{p.riskLevel}</span>
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="text-center text-sm text-gray-500 dark:text-gray-400 py-8">No patients found</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   MAIN PAGE
   ════════════════════════════════════════════════════════════════════════════ */

type TabId = "chart" | "vitals" | "orders" | "notes";

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: "chart", label: "Chart Review", icon: ClipboardList },
  { id: "vitals", label: "Vitals & Labs", icon: Activity },
  { id: "orders", label: "Orders & Plans", icon: FileText },
  { id: "notes", label: "Notes & Documents", icon: FileText },
];

export default function ClinicalWorkspacePage() {
  const [activePatient, setActivePatient] = useState<DemoPatient | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("chart");
  const [showSelector, setShowSelector] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  /* Attempt to hydrate from API when a patient is selected */
  const loadPatientData = useCallback(async (patient: DemoPatient) => {
    setIsLoading(true);
    try {
      const [apiPatient, vitals, risk, alerts, prescriptions] = await Promise.allSettled([
        fetchPatient(patient.id),
        fetchVitals(patient.id),
        fetchRiskScore(patient.id),
        fetchAlerts({ patient_id: patient.id }),
        fetchPrescriptionHistory(patient.id),
      ]);
      // If API succeeds, merge; otherwise we already have demo data
      // For now we just use the demo data as the rich fallback
    } catch {
      // Silently fall back to demo data
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleSelectPatient = useCallback((patient: DemoPatient) => {
    setActivePatient(patient);
    setActiveTab("chart");
    loadPatientData(patient);
  }, [loadPatientData]);

  return (
    <div className="animate-fade-in-up">
      {/* ── HEADER ──────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Stethoscope className="w-6 h-6 text-healthos-600" />
            Clinical Workspace
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Unified patient care view</p>
        </div>
        <div className="flex items-center gap-3">
          {activePatient && (
            <span className={riskBadgeClass(activePatient.riskLevel)}>
              {activePatient.name} &middot; {activePatient.riskLevel.toUpperCase()}
            </span>
          )}
          <button
            onClick={() => setShowSelector(true)}
            className="btn-primary !py-2 !px-4 !text-sm"
          >
            <Search className="w-4 h-4" />
            Select Patient
          </button>
        </div>
      </div>

      {/* ── PATIENT CONTEXT BAR ────────────────────────────────────── */}
      {activePatient && (
        <div className="sticky top-0 z-30 mb-6 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/95 backdrop-blur-md shadow-sm px-4 py-3 animate-fade-in-up">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-healthos-100 flex items-center justify-center text-healthos-700 font-bold text-sm">
                {activePatient.name.split(" ").map((n) => n[0]).join("")}
              </div>
              <div>
                <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{activePatient.name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">{activePatient.mrn}</p>
              </div>
            </div>
            <div className="h-8 w-px bg-gray-200 hidden sm:block" />
            <div className="text-xs text-gray-600 dark:text-gray-400">
              <span className="font-semibold">{activePatient.age}{activePatient.gender[0]}</span>
            </div>
            <span className={riskBadgeClass(activePatient.riskLevel)}>{activePatient.riskLevel}</span>
            <div className="h-8 w-px bg-gray-200 hidden sm:block" />
            <div className="flex flex-wrap gap-1.5">
              {activePatient.conditions.slice(0, 3).map((c, i) => (
                <span key={i} className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-medium">{c.name.split(" ").slice(0, 3).join(" ")}</span>
              ))}
              {activePatient.conditions.length > 3 && (
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">+{activePatient.conditions.length - 3} more</span>
              )}
            </div>
            <div className="h-8 w-px bg-gray-200 hidden sm:block" />
            <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
              <Pill className="w-3 h-3" />
              <span className="font-semibold">{activePatient.medications.length}</span> meds
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              Vitals: {formatTimestamp(activePatient.lastVitalsTimestamp)}
            </div>
          </div>
        </div>
      )}

      {/* ── NO PATIENT SELECTED STATE ──────────────────────────────── */}
      {!activePatient && (
        <div className="card text-center py-20 animate-fade-in-up">
          <Stethoscope className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-600 dark:text-gray-400 mb-2">No Patient Selected</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
            Select a patient to access their comprehensive clinical workspace including chart review, vitals, orders, notes, and AI-powered clinical decision support.
          </p>
          <button
            onClick={() => setShowSelector(true)}
            className="btn-primary"
          >
            <Search className="w-4 h-4" />
            Select Patient
          </button>
        </div>
      )}

      {/* ── SPLIT LAYOUT ──────────────────────────────────────────── */}
      {activePatient && (
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left Panel — 2/3 */}
          <div className="flex-1 lg:w-2/3 min-w-0">
            {/* Tabs */}
            <div className="flex gap-1 mb-4 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 overflow-x-auto">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    "flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap",
                    activeTab === tab.id
                      ? "bg-white dark:bg-gray-900 text-healthos-700 shadow-sm"
                      : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
                  )}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Loading overlay */}
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-healthos-500" />
                <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">Loading patient data...</span>
              </div>
            )}

            {/* Tab Content */}
            {!isLoading && activeTab === "chart" && <ChartReviewTab patient={activePatient} />}
            {!isLoading && activeTab === "vitals" && <VitalsLabsTab patient={activePatient} />}
            {!isLoading && activeTab === "orders" && <OrdersPlansTab patient={activePatient} />}
            {!isLoading && activeTab === "notes" && <NotesDocumentsTab patient={activePatient} />}
          </div>

          {/* Right Panel — 1/3 AI Sidebar */}
          <div className="lg:w-1/3 flex-shrink-0">
            <div className="lg:sticky lg:top-20">
              <AISidebar patient={activePatient} />
            </div>
          </div>
        </div>
      )}

      {/* ── PATIENT SELECTOR MODAL ─────────────────────────────────── */}
      {showSelector && (
        <PatientSelector
          onSelect={handleSelectPatient}
          onClose={() => setShowSelector(false)}
        />
      )}
    </div>
  );
}
