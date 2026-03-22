"use client";

import React, { useState, useEffect, useMemo } from "react";
import { fetchPatients } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type EventType = "encounter" | "lab" | "medication" | "procedure" | "alert" | "note";

interface TimelineEvent {
  id: string;
  date: string;
  time: string;
  type: EventType;
  title: string;
  description: string;
  provider: string;
  details?: string;
}

interface Patient {
  id: string;
  name: string;
}

/* ------------------------------------------------------------------ */
/*  Color / badge config per event type                                */
/* ------------------------------------------------------------------ */

const EVENT_CONFIG: Record<
  EventType,
  { label: string; color: string; bg: string; border: string; dot: string; badge: string }
> = {
  encounter: {
    label: "Encounter",
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-900/30",
    border: "border-blue-300 dark:border-blue-700",
    dot: "bg-blue-500",
    badge: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
  },
  lab: {
    label: "Lab",
    color: "text-purple-600 dark:text-purple-400",
    bg: "bg-purple-50 dark:bg-purple-900/30",
    border: "border-purple-300 dark:border-purple-700",
    dot: "bg-purple-500",
    badge: "bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300",
  },
  medication: {
    label: "Medication",
    color: "text-green-600 dark:text-green-400",
    bg: "bg-green-50 dark:bg-green-900/30",
    border: "border-green-300 dark:border-green-700",
    dot: "bg-green-500",
    badge: "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300",
  },
  procedure: {
    label: "Procedure",
    color: "text-orange-600 dark:text-orange-400",
    bg: "bg-orange-50 dark:bg-orange-900/30",
    border: "border-orange-300 dark:border-orange-700",
    dot: "bg-orange-500",
    badge: "bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300",
  },
  alert: {
    label: "Alert",
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-50 dark:bg-red-900/30",
    border: "border-red-300 dark:border-red-700",
    dot: "bg-red-500",
    badge: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
  },
  note: {
    label: "Note",
    color: "text-gray-600 dark:text-gray-500",
    bg: "bg-gray-50 dark:bg-gray-800/50",
    border: "border-gray-300 dark:border-gray-700",
    dot: "bg-gray-500",
    badge: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300",
  },
};

/* ------------------------------------------------------------------ */
/*  Demo data — realistic 6-month patient journey                      */
/* ------------------------------------------------------------------ */

const DEMO_PATIENTS: Patient[] = [
  { id: "p-1001", name: "Maria Santos" },
  { id: "p-1002", name: "James Whitfield" },
  { id: "p-1003", name: "Aya Nakamura" },
];

const DEMO_TIMELINE: TimelineEvent[] = [
  // --- September 2025 ---
  {
    id: "evt-001",
    date: "2025-09-02",
    time: "09:15",
    type: "encounter",
    title: "Annual Wellness Visit",
    description: "Routine annual physical examination. Patient reports mild fatigue over past 3 weeks.",
    provider: "Dr. Angela Rivera",
    details:
      "Vitals: BP 138/88 mmHg, HR 78 bpm, Temp 98.4\u00b0F, BMI 27.3. General appearance normal. Heart sounds regular, no murmurs. Lungs clear bilaterally. Abdomen soft, non-tender. Elevated BP noted \u2014 recommend lifestyle modifications and follow-up in 4 weeks. Ordered comprehensive metabolic panel and CBC.",
  },
  {
    id: "evt-002",
    date: "2025-09-05",
    time: "07:30",
    type: "lab",
    title: "Comprehensive Metabolic Panel",
    description: "Fasting blood draw completed. Results: Glucose 118 mg/dL (H), HbA1c 6.2%, Creatinine 0.9 mg/dL.",
    provider: "Quest Diagnostics",
    details:
      "Sodium: 140, Potassium: 4.1, Chloride: 102, BUN: 15, Creatinine: 0.9, Glucose: 118 (H), Calcium: 9.5, Albumin: 4.3, AST: 22, ALT: 28. HbA1c: 6.2% \u2014 pre-diabetic range.",
  },
  {
    id: "evt-003",
    date: "2025-09-05",
    time: "07:30",
    type: "lab",
    title: "Complete Blood Count (CBC)",
    description: "All values within normal limits. WBC 6.8, Hgb 14.1, Platelets 245.",
    provider: "Quest Diagnostics",
    details:
      "WBC: 6.8, RBC: 4.72, Hemoglobin: 14.1, Hematocrit: 42.3%, MCV: 89.6, Platelets: 245. Differential: Neutrophils 58%, Lymphocytes 32%, Monocytes 7%, Eosinophils 2%, Basophils 1%.",
  },
  {
    id: "evt-004",
    date: "2025-09-08",
    time: "14:00",
    type: "note",
    title: "Lab Results Review \u2014 Clinical Note",
    description: "Reviewed labs with patient via patient portal message. Pre-diabetes counseling provided.",
    provider: "Dr. Angela Rivera",
    details:
      "Patient notified of elevated fasting glucose and HbA1c in pre-diabetic range. Discussed dietary changes including reduced refined carbohydrate intake, increased fiber, and regular physical activity (150 min/week moderate exercise). Referred to nutritionist. Will recheck HbA1c in 3 months.",
  },
  {
    id: "evt-005",
    date: "2025-09-12",
    time: "11:00",
    type: "note",
    title: "Referral: Nutrition Counseling",
    description: "Referral placed for medical nutrition therapy for pre-diabetes management.",
    provider: "Dr. Angela Rivera",
  },
  // --- October 2025 ---
  {
    id: "evt-006",
    date: "2025-10-01",
    time: "10:30",
    type: "encounter",
    title: "Blood Pressure Follow-Up",
    description: "4-week BP recheck. Readings: 142/90, 140/88, 136/86 (3 measurements). Hypertension Stage 1 confirmed.",
    provider: "Dr. Angela Rivera",
    details:
      "Patient reports attempting dietary changes but struggling with consistency. Weight unchanged at 183 lbs. Three seated BP readings averaged 139/88. Diagnosis: Essential Hypertension, Stage 1 (ICD-10 I10). Starting Lisinopril 10 mg daily. Discussed side effects including cough, dizziness. Follow-up in 4 weeks to assess response.",
  },
  {
    id: "evt-007",
    date: "2025-10-01",
    time: "10:45",
    type: "medication",
    title: "New Prescription: Lisinopril 10 mg",
    description: "Lisinopril 10 mg tablet, once daily in the morning. Qty: 30, Refills: 5.",
    provider: "Dr. Angela Rivera",
    details:
      "ACE inhibitor for Stage 1 hypertension. Patient educated on taking in the morning, avoiding potassium supplements, and reporting persistent dry cough. Renal function and potassium to be checked in 2 weeks.",
  },
  {
    id: "evt-008",
    date: "2025-10-08",
    time: "13:00",
    type: "encounter",
    title: "Nutrition Counseling \u2014 Initial Visit",
    description: "Medical nutrition therapy session. Developed personalized meal plan targeting blood sugar control.",
    provider: "Sarah Kim, RD, CDCES",
    details:
      "60-minute initial nutrition assessment. Current diet high in refined carbohydrates and sugary beverages. Created individualized meal plan: 1800 kcal/day, moderate carbohydrate (45% of calories), emphasis on whole grains, lean proteins, non-starchy vegetables. Set goals: eliminate sugary drinks, add 2 servings of vegetables daily, walk 30 min 5x/week. Follow-up in 4 weeks.",
  },
  {
    id: "evt-009",
    date: "2025-10-15",
    time: "07:45",
    type: "lab",
    title: "Basic Metabolic Panel \u2014 2-Week Med Check",
    description: "Renal function and electrolytes following Lisinopril initiation. Potassium 4.3, Creatinine 0.9 \u2014 stable.",
    provider: "Quest Diagnostics",
  },
  // --- November 2025 ---
  {
    id: "evt-010",
    date: "2025-11-03",
    time: "09:00",
    type: "encounter",
    title: "Hypertension Follow-Up",
    description: "BP improved to 130/82. Lisinopril well-tolerated. Continue current regimen.",
    provider: "Dr. Angela Rivera",
    details:
      "Patient reports no side effects from Lisinopril. Has been walking 20\u201330 minutes most days. BP today: 132/84, 128/80 (average 130/82). Weight down 2 lbs to 181 lbs. Good response to medication. Continue Lisinopril 10 mg daily. Encourage continued lifestyle modifications. Follow-up in 2 months or sooner if needed.",
  },
  {
    id: "evt-011",
    date: "2025-11-10",
    time: "13:30",
    type: "encounter",
    title: "Nutrition Counseling \u2014 Follow-Up",
    description: "Progress review: patient eliminated sugary beverages, added more vegetables. Lost 2 lbs.",
    provider: "Sarah Kim, RD, CDCES",
  },
  {
    id: "evt-012",
    date: "2025-11-18",
    time: "22:15",
    type: "encounter",
    title: "ER Visit \u2014 Acute Chest Pain",
    description: "Patient presented to ER with substernal chest tightness and shortness of breath after climbing stairs.",
    provider: "Dr. Mark Okonkwo (Emergency Medicine)",
    details:
      "52-year-old with HTN and pre-diabetes, 45 min substernal chest pressure radiating to left arm with dyspnea. ECG: NSR, no ST changes. Troponin I: <0.01 (normal). CXR: no acute findings. D-dimer negative. Serial troponins negative over 6 hours. Impression: atypical chest pain, likely musculoskeletal. Discharged with PCP follow-up and cardiology referral.",
  },
  {
    id: "evt-013",
    date: "2025-11-19",
    time: "08:00",
    type: "alert",
    title: "ER Discharge Notification",
    description: "Alert: Patient discharged from ER after chest pain evaluation. Troponins negative. Cardiology referral recommended.",
    provider: "System \u2014 Hospital ADT Feed",
  },
  {
    id: "evt-014",
    date: "2025-11-20",
    time: "09:30",
    type: "note",
    title: "Referral: Cardiology \u2014 Stress Test",
    description: "Urgent referral to cardiology for exercise stress echocardiogram following ER visit for chest pain.",
    provider: "Dr. Angela Rivera",
  },
  // --- December 2025 ---
  {
    id: "evt-015",
    date: "2025-12-02",
    time: "08:00",
    type: "procedure",
    title: "Exercise Stress Echocardiogram",
    description: "Treadmill stress echo performed. Achieved 10.1 METs, peak HR 158 bpm (94% predicted). No ischemic changes.",
    provider: "Dr. Priya Sharma (Cardiology)",
    details:
      "Bruce protocol. Baseline echo: normal LV, EF 60\u201365%, no wall motion abnormalities. Exercised 9 min 45 sec, 10.1 METs, peak HR 158 (94% predicted). No chest pain, no ST changes. Post-stress: no new wall motion abnormalities. Impression: Negative for inducible ischemia. Low risk for obstructive CAD.",
  },
  {
    id: "evt-016",
    date: "2025-12-02",
    time: "09:30",
    type: "note",
    title: "Cardiology Consultation Note",
    description: "Negative stress test. Low cardiac risk. Recommended continued BP and metabolic management.",
    provider: "Dr. Priya Sharma (Cardiology)",
  },
  {
    id: "evt-017",
    date: "2025-12-05",
    time: "07:30",
    type: "lab",
    title: "HbA1c Recheck (3-Month)",
    description: "HbA1c improved from 6.2% to 5.9%. Fasting glucose 102 mg/dL \u2014 moving in the right direction.",
    provider: "Quest Diagnostics",
    details:
      "HbA1c: 5.9% (previously 6.2%). Fasting glucose: 102 mg/dL (previously 118 mg/dL). Significant improvement with lifestyle modifications. Still in pre-diabetic range (5.7\u20136.4%) but trending favorably.",
  },
  {
    id: "evt-018",
    date: "2025-12-10",
    time: "10:00",
    type: "encounter",
    title: "Telehealth \u2014 Results Review",
    description: "Virtual visit to discuss stress echo results and improved HbA1c. Patient reassured about cardiac health.",
    provider: "Dr. Angela Rivera",
    details:
      "Reviewed negative stress echocardiogram \u2014 patient greatly relieved. Discussed continued importance of risk factor modification. HbA1c improved to 5.9% from 6.2% \u2014 excellent response to dietary changes and increased activity. Weight now 178 lbs (down 5 lbs from September). BP at home averaging 128/80. Continue Lisinopril 10 mg. Recheck labs in 3 months. Annual follow-up scheduled.",
  },
  {
    id: "evt-019",
    date: "2025-12-18",
    time: "15:00",
    type: "medication",
    title: "Rx Refill: Lisinopril 10 mg",
    description: "Pharmacy refill processed. 90-day supply dispensed via mail order.",
    provider: "CVS Pharmacy \u2014 Mail Order",
  },
  // --- January 2026 ---
  {
    id: "evt-020",
    date: "2026-01-07",
    time: "13:00",
    type: "encounter",
    title: "Nutrition Counseling \u2014 Quarterly Review",
    description: "Sustained progress. Patient cooking more at home, meal prepping on weekends. A1c trending down.",
    provider: "Sarah Kim, RD, CDCES",
  },
  {
    id: "evt-021",
    date: "2026-01-15",
    time: "14:00",
    type: "procedure",
    title: "Screening Colonoscopy",
    description: "Age-appropriate colorectal cancer screening. Two small polyps removed for biopsy.",
    provider: "Dr. Kevin Liu (Gastroenterology)",
    details:
      "Moderate sedation (Propofol). Scope to cecum without difficulty. Two sessile polyps: 4 mm sigmoid, 6 mm ascending colon. Cold snare polypectomy performed, sent for histopath. Normal mucosa otherwise. Prep quality excellent. Follow-up per pathology results.",
  },
  {
    id: "evt-022",
    date: "2026-01-22",
    time: "10:00",
    type: "lab",
    title: "Pathology \u2014 Colon Polyp Biopsy",
    description: "Sigmoid polyp: hyperplastic (benign). Ascending colon polyp: tubular adenoma, low grade dysplasia.",
    provider: "Dr. Lisa Chen (Pathology)",
    details:
      "Specimen A (sigmoid, 4 mm): Hyperplastic polyp. Benign. Specimen B (ascending colon, 6 mm): Tubular adenoma with low-grade dysplasia. Margins clear. Recommendation per GI guidelines: repeat colonoscopy in 3 years due to adenomatous polyp.",
  },
  {
    id: "evt-023",
    date: "2026-01-23",
    time: "09:00",
    type: "alert",
    title: "Pathology Result: Tubular Adenoma Found",
    description: "Action required: adenomatous polyp identified on screening colonoscopy. Shortened surveillance interval recommended.",
    provider: "System \u2014 Pathology Alert",
  },
  {
    id: "evt-024",
    date: "2026-01-25",
    time: "11:00",
    type: "note",
    title: "GI Follow-Up Note \u2014 Colonoscopy Results",
    description: "Dr. Liu communicated polyp results to patient. Next colonoscopy in 3 years (Jan 2029).",
    provider: "Dr. Kevin Liu (Gastroenterology)",
  },
  // --- February 2026 ---
  {
    id: "evt-025",
    date: "2026-02-10",
    time: "08:45",
    type: "encounter",
    title: "Office Visit \u2014 Knee Pain",
    description: "New complaint of right knee pain worsening over 3 weeks. Aggravated by stairs and prolonged walking.",
    provider: "Dr. Angela Rivera",
    details:
      "Right knee: mild effusion, no erythema or warmth. Full ROM with crepitus on flexion/extension. Negative McMurray, negative Lachman. Tender along medial joint line. Weight-bearing X-ray ordered. Working diagnosis: early osteoarthritis vs. meniscal injury. Prescribed Naproxen 500 mg BID with food for 2 weeks, ice, activity modification. MRI if no improvement.",
  },
  {
    id: "evt-026",
    date: "2026-02-10",
    time: "09:00",
    type: "medication",
    title: "New Prescription: Naproxen 500 mg",
    description: "Naproxen 500 mg tablet, twice daily with food for 14 days. For right knee pain.",
    provider: "Dr. Angela Rivera",
  },
  {
    id: "evt-027",
    date: "2026-02-10",
    time: "10:30",
    type: "procedure",
    title: "X-Ray \u2014 Right Knee (Weight-Bearing)",
    description: "Mild medial compartment joint space narrowing. Small osteophyte formation. No fracture.",
    provider: "Dr. Thomas Wright (Radiology)",
    details:
      "AP, lateral, and sunrise views of the right knee, weight-bearing. Findings: Mild narrowing of the medial tibiofemoral joint space. Small marginal osteophytes at the medial femoral condyle and tibial plateau. No fracture or dislocation. Patellofemoral compartment normal. Soft tissues unremarkable. Impression: Mild degenerative changes consistent with early osteoarthritis, Kellgren-Lawrence grade 2.",
  },
  // --- March 2026 ---
  {
    id: "evt-028",
    date: "2026-03-03",
    time: "07:30",
    type: "lab",
    title: "Comprehensive Metabolic Panel \u2014 6-Month Recheck",
    description: "Fasting glucose 98 mg/dL (normalized!). HbA1c 5.6% \u2014 now in normal range. Creatinine stable at 0.9.",
    provider: "Quest Diagnostics",
    details:
      "Fasting Glucose: 98 mg/dL (was 118 \u2192 102 \u2192 98, now normal!). HbA1c: 5.6% (was 6.2% \u2192 5.9% \u2192 5.6%, now normal range). All other values within normal limits. Significant improvement \u2014 patient has successfully reversed pre-diabetes through lifestyle modifications.",
  },
  {
    id: "evt-029",
    date: "2026-03-03",
    time: "07:30",
    type: "lab",
    title: "Lipid Panel",
    description: "Total cholesterol 195, LDL 118, HDL 52, Triglycerides 125. Borderline LDL.",
    provider: "Quest Diagnostics",
    details:
      "Total Cholesterol: 195 mg/dL, LDL: 118 mg/dL (borderline), HDL: 52 mg/dL, Triglycerides: 125 mg/dL, VLDL: 25 mg/dL. Non-HDL Cholesterol: 143 mg/dL. TC/HDL Ratio: 3.75. LDL slightly above optimal; continue lifestyle modifications, consider statin if 10-year ASCVD risk is elevated.",
  },
  {
    id: "evt-030",
    date: "2026-03-10",
    time: "10:00",
    type: "encounter",
    title: "6-Month Comprehensive Review",
    description: "Milestone visit: pre-diabetes reversed, BP well controlled, weight down 8 lbs. Outstanding progress.",
    provider: "Dr. Angela Rivera",
    details:
      "BP: 124/78 on Lisinopril 10 mg. Weight: 175 lbs (down 8 lbs). HbA1c normalized at 5.6% \u2014 no longer pre-diabetic. Knee pain improved, Naproxen PRN only. Plan: continue current meds and lifestyle, recheck labs in 6 months, annual wellness Sept 2026. Borderline LDL \u2014 consider statin if ASCVD risk elevated.",
  },
  {
    id: "evt-031",
    date: "2026-03-10",
    time: "10:30",
    type: "medication",
    title: "Medication Change: Naproxen \u2014 PRN Only",
    description: "Changed Naproxen from scheduled BID to as-needed (PRN) for right knee pain. Max 2 tablets/day.",
    provider: "Dr. Angela Rivera",
  },
  {
    id: "evt-032",
    date: "2026-03-12",
    time: "16:00",
    type: "alert",
    title: "Preventive Care Reminder: Flu Vaccine Due",
    description: "Patient has not received current season influenza vaccination. Recommended at next visit.",
    provider: "System \u2014 Preventive Care Module",
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function PatientTimelinePage() {
  const [patients, setPatients] = useState<Patient[]>(DEMO_PATIENTS);
  const [selectedPatientId, setSelectedPatientId] = useState<string>(DEMO_PATIENTS[0].id);
  const [events] = useState<TimelineEvent[]>(DEMO_TIMELINE);

  // Filters
  const [activeTypes, setActiveTypes] = useState<Set<EventType>>(
    new Set<EventType>(["encounter", "lab", "medication", "procedure", "alert", "note"])
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Expanded cards
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  /* Fetch patients from API, fall back to demo data */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchPatients();
        if (!cancelled && Array.isArray(data) && data.length > 0) {
          const mapped = data.map((p: any) => ({
            id: p.id ?? p.patient_id ?? p.uuid,
            name: p.name ?? `${p.first_name ?? ""} ${p.last_name ?? ""}`.trim(),
          }));
          setPatients(mapped);
          setSelectedPatientId(mapped[0].id);
        }
      } catch {
        /* keep demo data */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  /* Toggle helpers */
  const toggleType = (t: EventType) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  /* Filtered & sorted events */
  const filteredEvents = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return events
      .filter((e) => {
        if (!activeTypes.has(e.type)) return false;
        if (dateFrom && e.date < dateFrom) return false;
        if (dateTo && e.date > dateTo) return false;
        if (
          q &&
          !e.title.toLowerCase().includes(q) &&
          !e.description.toLowerCase().includes(q) &&
          !e.provider.toLowerCase().includes(q) &&
          !(e.details ?? "").toLowerCase().includes(q)
        )
          return false;
        return true;
      })
      .sort((a, b) => {
        const cmp = b.date.localeCompare(a.date);
        return cmp !== 0 ? cmp : b.time.localeCompare(a.time);
      });
  }, [events, activeTypes, searchQuery, dateFrom, dateTo]);

  /* Format helpers */
  const fmtDate = (d: string) => {
    const [y, m, day] = d.split("-");
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${months[Number(m) - 1]} ${Number(day)}, ${y}`;
  };

  const fmtTime = (t: string) => {
    const [h, min] = t.split(":").map(Number);
    const ampm = h >= 12 ? "PM" : "AM";
    const hr = h % 12 || 12;
    return `${hr}:${String(min).padStart(2, "0")} ${ampm}`;
  };

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors">
      {/* Header */}
      <header className="sticky top-0 z-30 backdrop-blur bg-white/80 dark:bg-gray-900/80 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-indigo-600 dark:bg-indigo-500 flex items-center justify-center">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold tracking-tight">Patient Timeline</h1>
          </div>

          {/* Patient selector */}
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            className="sm:ml-auto rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
          >
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Filters card */}
        <div className="card card-hover rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 space-y-4 animate-fade-in-up">
          {/* Search + date range */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 dark:text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z" />
              </svg>
              <input
                type="text"
                placeholder="Search timeline..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 pl-10 pr-3 py-2 text-sm placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
              />
            </div>
            <div className="flex gap-2 items-center text-sm">
              <label className="text-gray-500 dark:text-gray-500 whitespace-nowrap">From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
              />
              <label className="text-gray-500 dark:text-gray-500 whitespace-nowrap">To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
              />
            </div>
          </div>

          {/* Event type checkboxes */}
          <div className="flex flex-wrap gap-3">
            {(Object.keys(EVENT_CONFIG) as EventType[]).map((t) => {
              const cfg = EVENT_CONFIG[t];
              const active = activeTypes.has(t);
              return (
                <label
                  key={t}
                  className={`flex items-center gap-2 cursor-pointer select-none rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                    active
                      ? `${cfg.badge} ${cfg.border}`
                      : "bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 border-gray-200 dark:border-gray-700 opacity-60"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => toggleType(t)}
                    className="sr-only"
                  />
                  <span className={`h-2 w-2 rounded-full ${active ? cfg.dot : "bg-gray-400 dark:bg-gray-600"}`} />
                  {cfg.label}
                </label>
              );
            })}
          </div>

          {/* Results count */}
          <p className="text-xs text-gray-500 dark:text-gray-500">
            Showing {filteredEvents.length} of {events.length} events
          </p>
        </div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[19px] top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-800" />

          <div className="space-y-4">
            {filteredEvents.length === 0 && (
              <div className="card rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 sm:p-8 text-center text-gray-400 dark:text-gray-500 animate-fade-in-up">
                No events match your current filters.
              </div>
            )}

            {filteredEvents.map((evt, idx) => {
              const cfg = EVENT_CONFIG[evt.type];
              const expanded = expandedIds.has(evt.id);
              const showDateHeader =
                idx === 0 || filteredEvents[idx - 1].date !== evt.date;

              return (
                <React.Fragment key={evt.id}>
                  {/* Date separator */}
                  {showDateHeader && (
                    <div className="flex items-center gap-3 pl-10 pt-2 animate-fade-in-up">
                      <span className="text-xs font-semibold text-gray-500 dark:text-gray-500 uppercase tracking-wider">
                        {fmtDate(evt.date)}
                      </span>
                      <div className="flex-1 h-px bg-gray-200 dark:bg-gray-800" />
                    </div>
                  )}

                  {/* Timeline item */}
                  <div
                    className="relative flex gap-4 animate-fade-in-up"
                    style={{ animationDelay: `${Math.min(idx * 40, 400)}ms` }}
                  >
                    {/* Dot */}
                    <div className="relative z-10 mt-1.5 flex-shrink-0">
                      <div
                        className={`h-[10px] w-[10px] rounded-full ring-4 ring-white dark:ring-gray-950 ${cfg.dot}`}
                      />
                    </div>

                    {/* Card */}
                    <button
                      type="button"
                      onClick={() => evt.details && toggleExpanded(evt.id)}
                      className={`card card-hover flex-1 rounded-xl border text-left transition-all ${cfg.border} ${
                        expanded ? cfg.bg : "bg-white dark:bg-gray-900"
                      } p-4 ${evt.details ? "cursor-pointer" : "cursor-default"}`}
                    >
                      {/* Top row: time + badge + expand indicator */}
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <span className="text-xs text-gray-400 dark:text-gray-500 font-mono">
                          {fmtTime(evt.time)}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.badge}`}
                        >
                          <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                          {cfg.label}
                        </span>
                        {evt.details && (
                          <svg
                            className={`ml-auto h-4 w-4 text-gray-400 dark:text-gray-500 transition-transform ${
                              expanded ? "rotate-180" : ""
                            }`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                          </svg>
                        )}
                      </div>

                      {/* Title */}
                      <h3 className={`text-sm font-semibold ${cfg.color}`}>{evt.title}</h3>

                      {/* Description */}
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                        {evt.description}
                      </p>

                      {/* Provider */}
                      <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                        {evt.provider}
                      </p>

                      {/* Expanded details */}
                      {expanded && evt.details && (
                        <div
                          className={`mt-3 pt-3 border-t ${cfg.border} text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line`}
                        >
                          {evt.details}
                        </div>
                      )}
                    </button>
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Bottom summary */}
        <div className="card rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 animate-fade-in-up">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Timeline Summary
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {(Object.keys(EVENT_CONFIG) as EventType[]).map((t) => {
              const cfg = EVENT_CONFIG[t];
              const count = events.filter((e) => e.type === t).length;
              return (
                <div
                  key={t}
                  className={`rounded-lg p-3 text-center ${cfg.bg} border ${cfg.border}`}
                >
                  <p className={`text-2xl font-bold ${cfg.color}`}>{count}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">{cfg.label}s</p>
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
