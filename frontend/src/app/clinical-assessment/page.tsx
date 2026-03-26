"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";

/* ═══════════════════════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════════════════════ */

type TabKey = "assessment" | "agents" | "llm" | "mcp" | "simulator";

interface ClinicalAssessment {
  success: boolean;
  patient_id: string;
  assessment?: {
    patient_summary?: {
      patient_id: string;
      name: string;
      age: number;
      sex: string;
    };
    findings?: Array<{
      category: string;
      finding: string;
      status: string;
      interpretation: string;
    }>;
    critical_findings?: Array<Record<string, unknown>>;
    diagnoses?: Array<{
      diagnosis: string;
      icd10_code: string;
      confidence: number;
      rationale: string;
      supporting_findings: string[];
    }>;
    treatments?: Array<{
      treatment_type: string;
      description: string;
      cpt_code: string;
      priority: string;
      rationale: string;
    }>;
    icd10_codes?: Array<{ code: string; description: string; confidence: number }>;
    cpt_codes?: Array<{ code: string; description: string }>;
    confidence?: number;
    reasoning?: string[];
    warnings?: string[];
    requires_human_review?: boolean;
    review_reason?: string;
  };
  error?: string;
  llm_provider?: string;
}

interface AgentInfo {
  agent_id: string;
  name: string;
  description: string;
  version: string;
  specialties: string[];
  requires_human_approval: boolean;
}

interface LLMStatus {
  status: string;
  primary_provider?: string;
  available_providers?: string[];
  config?: Record<string, unknown>;
  error?: string;
}

interface MCPServerStatus {
  url: string;
  status: string;
  error?: string;
}

interface SimulatorStatus {
  running: boolean;
  interval?: number;
  devices_count?: number;
  observations_sent?: number;
  alerts_generated?: number;
  errors_count?: number;
  error?: string;
}

/* ═══════════════════════════════════════════════════════════════════════════
   API HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */

const API = "/api/v1/clinical-assessment";

function getAuth(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...getAuth(), ...opts?.headers },
    ...opts,
  });
  if (res.status === 401) {
    throw new Error("AUTH_REQUIRED");
  }
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

/* ═══════════════════════════════════════════════════════════════════════════
   DEMO DATA
   ═══════════════════════════════════════════════════════════════════════════ */

const DEMO_PATIENTS = [
  { id: "1", name: "John Williams", mrn: "MRN001", age: 71, sex: "M", conditions: ["Hypertension", "Type 2 Diabetes"] },
  { id: "2", name: "Maria Garcia", mrn: "MRN002", age: 58, sex: "F", conditions: ["Atrial Fibrillation"] },
  { id: "3", name: "Robert Johnson", mrn: "MRN003", age: 65, sex: "M", conditions: ["Heart Failure", "CKD Stage 3"] },
  { id: "4", name: "Emily Davis", mrn: "MRN004", age: 45, sex: "F", conditions: ["Asthma", "Anxiety"] },
];

/* ── Realistic clinical data for each demo patient (LOINC-coded vitals, labs, etc.) ── */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const PATIENT_CLINICAL_DATA: Record<string, Record<string, any>> = {
  "1": {
    // John Williams — 71M, HTN + T2DM
    name: "John Williams", age: 71, sex: "male", date_of_birth: "1955-03-14",
    chief_complaint: "Routine follow-up for hypertension and type 2 diabetes management. Reports occasional dizziness and increased thirst over past 2 weeks.",
    history_present_illness: "71-year-old male with 15-year history of hypertension and 8-year history of type 2 diabetes mellitus. Current medications include Lisinopril 10mg daily and Metformin 1000mg BID. Reports home BP readings averaging 155/92. Increased polyuria and polydipsia over past 2 weeks. Last HbA1c was 8.2% three months ago. No chest pain, dyspnea, or visual changes.",
    physician_notes: "Patient appears well-nourished. Fundoscopic exam: no retinopathy. Pedal pulses 2+ bilaterally. Monofilament testing intact. BMI 31.2. Current regimen inadequate for both BP and glycemic targets.",
    past_medical_history: ["Essential hypertension (15 years)", "Type 2 diabetes mellitus (8 years)", "Hyperlipidemia", "Obesity (BMI 31.2)", "Mild osteoarthritis bilateral knees"],
    family_history: ["Father: MI at age 62, died at 68", "Mother: Type 2 diabetes, stroke at 75", "Brother: Hypertension"],
    social_history: { smoking: "Former smoker (quit 10 years ago, 20 pack-year history)", alcohol: "Occasional (1-2 drinks/week)", exercise: "Sedentary", diet: "High sodium, irregular meals" },
    vitals: [
      { code: "8867-4", display: "Heart Rate", value: 82, unit: "bpm" },
      { code: "85354-9", display: "Blood Pressure", components: [{ code: "8480-6", value: 158 }, { code: "8462-4", value: 94 }] },
      { code: "59408-5", display: "SpO2", value: 97, unit: "%" },
      { code: "8310-5", display: "Temperature", value: 36.8, unit: "°C" },
      { code: "9279-1", display: "Respiratory Rate", value: 16, unit: "/min" },
      { code: "2339-0", display: "Blood Glucose", value: 186, unit: "mg/dL" },
    ],
    labs: [
      { name: "HbA1c", value: 8.2, unit: "%", interpretation: { severity: "abnormal", message: "Above target 7.0% — suboptimal glycemic control over 3 months" } },
      { name: "Serum Creatinine", value: 1.4, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Mildly elevated — monitor renal function" } },
      { name: "eGFR", value: 58, unit: "mL/min/1.73m²", interpretation: { severity: "abnormal", message: "CKD Stage 3a — consider renal-protective agents" } },
      { name: "Potassium", value: 4.2, unit: "mEq/L", interpretation: { severity: "normal", message: "Within normal range" } },
      { name: "Total Cholesterol", value: 228, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Elevated — above target of 200 mg/dL" } },
      { name: "LDL Cholesterol", value: 142, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Elevated — target <100 mg/dL for diabetic patients" } },
      { name: "HDL Cholesterol", value: 38, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Low — target >40 mg/dL for males" } },
      { name: "Triglycerides", value: 195, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Elevated — above 150 mg/dL target" } },
      { name: "Microalbumin/Creatinine Ratio", value: 45, unit: "mg/g", interpretation: { severity: "abnormal", message: "Moderately increased albuminuria — early diabetic nephropathy" } },
      { name: "BUN", value: 28, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Mildly elevated" } },
    ],
    conditions: [
      { code: "I10", display: "Essential hypertension" },
      { code: "E11.9", display: "Type 2 diabetes mellitus without complications" },
      { code: "E78.5", display: "Hyperlipidemia, unspecified" },
      { code: "E66.01", display: "Morbid obesity due to excess calories" },
    ],
    medications: [
      { medication_name: "Lisinopril 10mg", dosage: "10mg daily", route: "oral" },
      { medication_name: "Metformin 1000mg", dosage: "1000mg BID", route: "oral" },
      { medication_name: "Aspirin 81mg", dosage: "81mg daily", route: "oral" },
    ],
    allergies: [
      { substance: "Sulfonamides", reaction: "Rash", severity: "moderate" },
    ],
    mental_health: {
      screening: "PHQ-9",
      score: 4,
      severity: "minimal",
      notes: "Patient denies depressive symptoms. Reports occasional stress related to managing chronic conditions. No suicidal ideation. Sleep quality adequate (6-7 hrs/night).",
      last_screened: "2026-01-15",
    },
    ambient_ai_notes: "Ambient AI documentation captured during visit: Patient arrived ambulatory, well-groomed. Speech fluent and coherent. Discussed home BP readings averaging 155/92 over past 2 weeks. Patient expressed concern about increasing thirst and frequent urination. Reviewed medication adherence — reports taking Lisinopril daily but occasionally misses evening Metformin dose. Patient receptive to dietary counseling. Agreed to trial DASH diet and sodium restriction. Follow-up labs ordered. Return in 6 weeks.",
    appointment_notes: [
      { type: "telehealth", date: "2026-02-10", provider: "Dr. Sarah Chen", summary: "Virtual follow-up: BP 152/90 per home monitor. Reviewed labs from 01/15. HbA1c trending up. Discussed adding SGLT2 inhibitor. Patient to schedule in-person visit for foot exam." },
      { type: "in-person", date: "2026-03-15", provider: "Dr. Sarah Chen", summary: "Office visit: BP 158/94. Weight 212 lbs (BMI 31.2). Comprehensive diabetic foot exam — monofilament intact, pedal pulses 2+ bilaterally. Fundoscopic exam normal. Current regimen inadequate. Plan to intensify therapy." },
    ],
  },
  "2": {
    // Maria Garcia — 58F, AFib
    name: "Maria Garcia", age: 58, sex: "female", date_of_birth: "1968-07-22",
    chief_complaint: "Palpitations and shortness of breath on exertion for 3 days. Intermittent dizziness.",
    history_present_illness: "58-year-old female presenting with 3-day history of palpitations, exercise intolerance, and intermittent dizziness. Reports feeling her heart 'racing and skipping' especially at night. Mild dyspnea on climbing one flight of stairs (previously able to climb three). No syncope, chest pain, or leg swelling. No recent illness or medication changes.",
    physician_notes: "Irregular heart rhythm on auscultation. No murmurs or gallops. Lungs clear bilaterally. No peripheral edema. CHA₂DS₂-VASc score = 2 (female, age 58). Recommend anticoagulation and rate control.",
    past_medical_history: ["Atrial fibrillation (newly diagnosed)", "Hypothyroidism (on Levothyroxine)", "Mild mitral regurgitation"],
    family_history: ["Mother: Atrial fibrillation at age 65", "Father: Coronary artery disease"],
    social_history: { smoking: "Never", alcohol: "Social (1-2 glasses wine/week)", exercise: "Walks 30 min daily (now limited)", diet: "Mediterranean diet" },
    vitals: [
      { code: "8867-4", display: "Heart Rate", value: 112, unit: "bpm" },
      { code: "85354-9", display: "Blood Pressure", components: [{ code: "8480-6", value: 128 }, { code: "8462-4", value: 78 }] },
      { code: "59408-5", display: "SpO2", value: 96, unit: "%" },
      { code: "8310-5", display: "Temperature", value: 36.6, unit: "°C" },
      { code: "9279-1", display: "Respiratory Rate", value: 18, unit: "/min" },
      { code: "93803-1", display: "ECG", ecg_rhythm: "Atrial fibrillation with rapid ventricular response", ecg_findings: ["Absent P waves", "Irregularly irregular rhythm", "Narrow QRS complex", "No ST changes"] },
    ],
    labs: [
      { name: "TSH", value: 2.1, unit: "mIU/L", interpretation: { severity: "normal", message: "Thyroid function normal on replacement therapy" } },
      { name: "Free T4", value: 1.2, unit: "ng/dL", interpretation: { severity: "normal", message: "Normal" } },
      { name: "BNP", value: 180, unit: "pg/mL", interpretation: { severity: "abnormal", message: "Mildly elevated — may indicate cardiac strain from rapid AF" } },
      { name: "Troponin I", value: 0.02, unit: "ng/mL", interpretation: { severity: "normal", message: "Within normal limits — no acute myocardial injury" } },
      { name: "INR", value: 1.0, unit: "", interpretation: { severity: "normal", message: "Not on anticoagulation currently" } },
      { name: "Serum Creatinine", value: 0.9, unit: "mg/dL", interpretation: { severity: "normal", message: "Normal renal function" } },
      { name: "Magnesium", value: 1.6, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Low-normal — consider supplementation (may contribute to arrhythmia)" } },
      { name: "Potassium", value: 3.8, unit: "mEq/L", interpretation: { severity: "normal", message: "Within normal range" } },
    ],
    conditions: [
      { code: "I48.91", display: "Unspecified atrial fibrillation" },
      { code: "E03.9", display: "Hypothyroidism, unspecified" },
      { code: "I34.0", display: "Nonrheumatic mitral valve insufficiency" },
    ],
    medications: [
      { medication_name: "Levothyroxine 75mcg", dosage: "75mcg daily", route: "oral" },
    ],
    allergies: [],
    mental_health: {
      screening: "GAD-7",
      score: 8,
      severity: "mild",
      notes: "Patient reports mild anxiety related to new cardiac diagnosis. Some sleep disturbance (difficulty falling asleep, 2-3 nights/week). Denies panic attacks. No depressive symptoms on PHQ-2 (score 1). Coping well with social support.",
      last_screened: "2026-03-20",
    },
    ambient_ai_notes: "Ambient AI documentation captured during visit: Patient presents with complaint of palpitations x3 days. Appears mildly anxious but cooperative. Heart rate noted to be irregular during examination. Patient describes episodes as 'heart racing and skipping beats,' worse at night when lying down. Reports reduced exercise tolerance — previously walked 2 miles, now limited to one block. No syncope or near-syncope. Discussed need for anticoagulation given CHA₂DS₂-VASc score. Patient has questions about long-term management and prognosis.",
    appointment_notes: [
      { type: "telehealth", date: "2026-03-18", provider: "Dr. Michael Rivera", summary: "Urgent virtual consult: Patient called reporting new-onset palpitations and dyspnea x1 day. HR 108 irregular on home device. Advised to come in for ECG. Prescribed short-term Metoprolol 25mg while awaiting visit." },
      { type: "in-person", date: "2026-03-20", provider: "Dr. Michael Rivera", summary: "Urgent office visit: ECG confirms atrial fibrillation with RVR (HR 112). BNP 180. Troponin negative. TSH normal. Started Metoprolol succinate 50mg daily for rate control. Initiated Apixaban 5mg BID for stroke prevention (CHA₂DS₂-VASc=2). Echo ordered. Follow-up in 1 week." },
    ],
  },
  "3": {
    // Robert Johnson — 65M, HF + CKD
    name: "Robert Johnson", age: 65, sex: "male", date_of_birth: "1961-01-08",
    chief_complaint: "Progressive dyspnea on exertion and bilateral ankle swelling for 1 week. Weight gain of 4 lbs in 5 days.",
    history_present_illness: "65-year-old male with known HFrEF (EF 35%) and CKD Stage 3 presenting with worsening dyspnea over 1 week. Now SOB walking to mailbox (50 feet). Orthopnea requiring 3 pillows (baseline: 1). Reports 4 lb weight gain over 5 days despite taking medications. Bilateral 2+ pitting edema. Dietary indiscretion — attended family gathering with high-sodium food. No chest pain, fever, or cough.",
    physician_notes: "Patient in mild respiratory distress. JVP elevated at 10cm. Bibasilar crackles. S3 gallop present. 2+ pitting edema bilateral lower extremities. Abdominal exam: mild hepatomegaly. NYHA Class III (up from Class II baseline). Acute decompensated heart failure secondary to dietary non-compliance. Current GDMT suboptimal — not on ARNI or MRA.",
    past_medical_history: ["Heart failure with reduced ejection fraction (EF 35%)", "CKD Stage 3 (eGFR 42)", "Coronary artery disease (PCI with 2 stents, 2019)", "Type 2 diabetes mellitus", "Former smoker"],
    family_history: ["Father: Heart failure, died at 70", "Mother: Type 2 diabetes, CKD"],
    social_history: { smoking: "Former (quit 5 years ago, 30 pack-year)", alcohol: "None", exercise: "Limited by dyspnea", diet: "Prescribed 2g sodium restriction — recent non-compliance" },
    vitals: [
      { code: "8867-4", display: "Heart Rate", value: 96, unit: "bpm" },
      { code: "85354-9", display: "Blood Pressure", components: [{ code: "8480-6", value: 108 }, { code: "8462-4", value: 68 }] },
      { code: "59408-5", display: "SpO2", value: 93, unit: "%" },
      { code: "8310-5", display: "Temperature", value: 36.9, unit: "°C" },
      { code: "9279-1", display: "Respiratory Rate", value: 22, unit: "/min" },
    ],
    labs: [
      { name: "BNP", value: 820, unit: "pg/mL", interpretation: { severity: "critical", message: "Significantly elevated — consistent with acute decompensated heart failure" } },
      { name: "Troponin I", value: 0.04, unit: "ng/mL", interpretation: { severity: "normal", message: "Mildly elevated — demand ischemia from HF exacerbation" } },
      { name: "Serum Creatinine", value: 1.8, unit: "mg/dL", interpretation: { severity: "abnormal", message: "Elevated — worsening renal function (cardiorenal syndrome)" } },
      { name: "eGFR", value: 42, unit: "mL/min/1.73m²", interpretation: { severity: "abnormal", message: "CKD Stage 3b — declining from baseline eGFR 48" } },
      { name: "Potassium", value: 4.8, unit: "mEq/L", interpretation: { severity: "abnormal", message: "Upper-normal — caution with RAAS inhibitors and MRA" } },
      { name: "Sodium", value: 134, unit: "mEq/L", interpretation: { severity: "abnormal", message: "Mildly low — dilutional hyponatremia from fluid overload" } },
      { name: "HbA1c", value: 7.4, unit: "%", interpretation: { severity: "abnormal", message: "Slightly above target — reasonable for patient with HF and CKD" } },
      { name: "Hemoglobin", value: 11.2, unit: "g/dL", interpretation: { severity: "abnormal", message: "Mild anemia — common in CKD and heart failure" } },
    ],
    conditions: [
      { code: "I50.22", display: "Chronic systolic heart failure, NYHA Class III" },
      { code: "N18.3", display: "Chronic kidney disease, stage 3" },
      { code: "I25.10", display: "Atherosclerotic heart disease with history of PCI" },
      { code: "E11.9", display: "Type 2 diabetes mellitus" },
    ],
    medications: [
      { medication_name: "Carvedilol 25mg", dosage: "25mg BID", route: "oral" },
      { medication_name: "Lisinopril 20mg", dosage: "20mg daily", route: "oral" },
      { medication_name: "Furosemide 40mg", dosage: "40mg daily", route: "oral" },
      { medication_name: "Aspirin 81mg", dosage: "81mg daily", route: "oral" },
      { medication_name: "Atorvastatin 40mg", dosage: "40mg daily", route: "oral" },
      { medication_name: "Metformin 500mg", dosage: "500mg BID", route: "oral" },
    ],
    allergies: [
      { substance: "ACE inhibitor cough", reaction: "Persistent dry cough with Enalapril (tolerated Lisinopril)", severity: "mild" },
    ],
    mental_health: {
      screening: "PHQ-9",
      score: 12,
      severity: "moderate",
      notes: "Patient endorses depressive symptoms: low mood, loss of interest in activities, fatigue, poor appetite. Reports feeling 'burdensome' to family due to illness limitations. Sleep disrupted by orthopnea. Denies suicidal ideation. Depression likely secondary to chronic illness burden. Consider referral to behavioral health.",
      last_screened: "2026-03-10",
    },
    ambient_ai_notes: "Ambient AI documentation captured during visit: Patient arrived in wheelchair, mildly dyspneic at rest. Reports 4 lb weight gain over 5 days after attending family gathering with high-sodium food. Bilateral ankle swelling noted. Patient describes progressive SOB — now unable to walk to mailbox (50 ft). Sleeping with 3 pillows (baseline 1). Discussed dietary compliance — patient acknowledges difficulty maintaining 2g sodium restriction. Family member present, engaged in care discussion. Patient appears fatigued and somewhat withdrawn. Agreed to diuretic adjustment and GDMT optimization.",
    appointment_notes: [
      { type: "telehealth", date: "2026-02-28", provider: "Dr. Amanda Foster", summary: "Scheduled virtual check-in: Weight stable at 198 lbs. BP 112/70. Patient reports NYHA Class II symptoms. Taking all medications. Diet compliant. Continue current regimen. Follow-up in 4 weeks." },
      { type: "in-person", date: "2026-03-12", provider: "Dr. Amanda Foster", summary: "Urgent visit: 4 lb weight gain, worsening dyspnea (NYHA III), bilateral edema. JVP elevated. Bibasilar crackles. S3 gallop. Acute decompensated HF from dietary indiscretion. IV Furosemide 40mg given. Transitioning to Sacubitril/Valsartan. Adding Spironolactone. Strict I&O. Daily weights. Consider admission if no improvement in 24h." },
      { type: "in-person", date: "2026-03-14", provider: "Dr. Amanda Foster", summary: "Follow-up: Weight down 2 lbs. Improved dyspnea. Edema 1+ from 2+. Crackles resolving. Continue outpatient diuresis. Tolerating Sacubitril/Valsartan 24/26mg. K+ 4.8 — monitor closely with new MRA. Return in 3 days." },
    ],
  },
  "4": {
    // Emily Davis — 45F, Asthma + Anxiety
    name: "Emily Davis", age: 45, sex: "female", date_of_birth: "1981-11-03",
    chief_complaint: "Worsening shortness of breath and wheezing for 5 days. Increased rescue inhaler use to 4-5 times daily. Also reports increased anxiety and difficulty sleeping.",
    history_present_illness: "45-year-old female with moderate persistent asthma and generalized anxiety disorder. Reports worsening wheezing and dyspnea over 5 days, triggered by seasonal allergens. Using rescue albuterol 4-5 times daily (baseline: 1-2 times/week). Night-time awakenings 3 times this week. Reports increased anxiety about breathing, racing thoughts, and insomnia (sleeping 3-4 hours). No fever, purulent sputum, or chest pain. PEF at home measured 65% of personal best.",
    physician_notes: "Patient appears anxious and mildly dyspneic at rest. Bilateral expiratory wheezing on auscultation. Good air movement. No accessory muscle use. No nasal polyps. Skin: mild eczema on antecubital fossae. Mental status: anxious affect, rapid speech, appropriate thought content. Asthma exacerbation — step up therapy indicated. Anxiety management needs reassessment.",
    past_medical_history: ["Moderate persistent asthma (since childhood)", "Generalized anxiety disorder (5 years)", "Allergic rhinitis", "Eczema"],
    family_history: ["Mother: Asthma, eczema", "Father: Anxiety disorder, GERD"],
    social_history: { smoking: "Never", alcohol: "Rare", exercise: "Yoga 3x/week (limited currently by breathing)", diet: "Vegetarian" },
    vitals: [
      { code: "8867-4", display: "Heart Rate", value: 98, unit: "bpm" },
      { code: "85354-9", display: "Blood Pressure", components: [{ code: "8480-6", value: 132 }, { code: "8462-4", value: 82 }] },
      { code: "59408-5", display: "SpO2", value: 95, unit: "%" },
      { code: "8310-5", display: "Temperature", value: 37.0, unit: "°C" },
      { code: "9279-1", display: "Respiratory Rate", value: 22, unit: "/min" },
    ],
    labs: [
      { name: "CBC WBC", value: 8.2, unit: "K/uL", interpretation: { severity: "normal", message: "Normal white cell count — no evidence of infection" } },
      { name: "Eosinophils", value: 6.8, unit: "%", interpretation: { severity: "abnormal", message: "Elevated — consistent with allergic/eosinophilic asthma phenotype" } },
      { name: "IgE Total", value: 320, unit: "IU/mL", interpretation: { severity: "abnormal", message: "Elevated — atopic phenotype, consider biologic therapy if uncontrolled" } },
      { name: "Peak Expiratory Flow", value: 285, unit: "L/min", interpretation: { severity: "abnormal", message: "65% of predicted (440 L/min) — moderate obstruction" } },
      { name: "Cortisol (AM)", value: 15, unit: "mcg/dL", interpretation: { severity: "normal", message: "Normal — no adrenal suppression from inhaled corticosteroids" } },
      { name: "TSH", value: 2.8, unit: "mIU/L", interpretation: { severity: "normal", message: "Normal thyroid function" } },
    ],
    conditions: [
      { code: "J45.40", display: "Moderate persistent asthma, uncomplicated" },
      { code: "F41.1", display: "Generalized anxiety disorder" },
      { code: "J30.1", display: "Allergic rhinitis due to pollen" },
      { code: "L20.9", display: "Atopic dermatitis, unspecified" },
    ],
    medications: [
      { medication_name: "Fluticasone/Salmeterol 250/50", dosage: "1 puff BID", route: "inhalation" },
      { medication_name: "Albuterol HFA", dosage: "2 puffs PRN (currently 4-5x daily)", route: "inhalation" },
      { medication_name: "Montelukast 10mg", dosage: "10mg daily", route: "oral" },
      { medication_name: "Sertraline 100mg", dosage: "100mg daily", route: "oral" },
      { medication_name: "Cetirizine 10mg", dosage: "10mg daily", route: "oral" },
    ],
    allergies: [
      { substance: "Dust mites", reaction: "Rhinitis, wheezing", severity: "moderate" },
      { substance: "Tree pollen", reaction: "Rhinitis, eye irritation", severity: "moderate" },
      { substance: "NSAIDs", reaction: "Bronchospasm", severity: "severe" },
    ],
    mental_health: {
      screening: "GAD-7",
      score: 14,
      severity: "moderate",
      notes: "Generalized anxiety disorder — currently on Sertraline 100mg. Reports worsening anxiety over past week correlated with asthma exacerbation. Racing thoughts, difficulty concentrating at work, insomnia (3-4 hrs/night). PHQ-9 score 6 (mild). Reports breathing difficulty triggers panic-like episodes but denies true panic attacks. No suicidal ideation. Consider Sertraline dose adjustment or adjunct therapy. Referred to CBT.",
      last_screened: "2026-03-22",
      phq9_score: 6,
      gad7_score: 14,
    },
    ambient_ai_notes: "Ambient AI documentation captured during visit: Patient appears anxious with rapid speech pattern. Audible wheezing at rest. Using accessory muscles minimally. Reports asthma worsening over 5 days coinciding with high pollen count. Using rescue inhaler 4-5x daily (baseline 1-2x/week). Waking 3 nights this week with wheezing. Reports anxiety significantly worse — difficulty separating respiratory symptoms from anxiety symptoms. Patient tearful when discussing impact on daily functioning. Currently unable to attend yoga classes. Work performance declining. Discussed step-up asthma therapy and mental health management. Patient agreeable to both adjustments.",
    appointment_notes: [
      { type: "telehealth", date: "2026-02-15", provider: "Dr. James Park", summary: "Routine virtual follow-up: Asthma well-controlled (ACT score 22). GAD-7 score 10 (moderate). Sertraline 100mg tolerated well. Reports occasional breakthrough anxiety. Continue current regimen. Follow-up in 6 weeks." },
      { type: "telehealth", date: "2026-03-10", provider: "Dr. Lisa Wong (Psychiatry)", summary: "Telepsychiatry consult: GAD-7 14, PHQ-9 6. Anxiety worsening with seasonal triggers. Sleep impaired. Discussed Sertraline dose increase vs. adding Buspirone. Patient prefers non-pharmacologic first. Referred to CBT therapist. Follow-up in 4 weeks." },
      { type: "in-person", date: "2026-03-22", provider: "Dr. James Park", summary: "Urgent visit: Asthma exacerbation with PEF 65% predicted. Bilateral wheezing. SpO2 95%. Step-up therapy: add Prednisone 40mg x5 days, increase ICS component. GAD-7 14 — anxiety significantly worse. Co-managing with psychiatry. Continue Sertraline. Start Buspirone 5mg BID if CBT insufficient. Return in 1 week or sooner if worsening." },
    ],
  },
};

function buildDemoAssessment(patient: typeof DEMO_PATIENTS[0]): ClinicalAssessment {
  const conditionData: Record<string, { findings: NonNullable<NonNullable<ClinicalAssessment["assessment"]>["findings"]>; diagnoses: NonNullable<NonNullable<ClinicalAssessment["assessment"]>["diagnoses"]>; treatments: NonNullable<NonNullable<ClinicalAssessment["assessment"]>["treatments"]> }> = {
    Hypertension: {
      findings: [
        { category: "Vitals", finding: "Blood pressure 158/94 mmHg", status: "abnormal", interpretation: "Stage 2 hypertension — above target 130/80 for diabetic patients" },
        { category: "Vitals", finding: "Heart rate 82 bpm", status: "normal", interpretation: "Regular rate and rhythm" },
        { category: "Labs", finding: "Serum creatinine 1.4 mg/dL", status: "borderline", interpretation: "Mildly elevated — monitor renal function given hypertension and diabetes" },
        { category: "Labs", finding: "Potassium 4.2 mEq/L", status: "normal", interpretation: "Within normal range" },
      ],
      diagnoses: [
        { diagnosis: "Essential Hypertension, Stage 2", icd10_code: "I10", confidence: 0.95, rationale: "Sustained BP >140/90 on multiple readings with end-organ risk factors", supporting_findings: ["BP 158/94", "Elevated creatinine"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Increase Lisinopril to 20mg daily", cpt_code: "99214", priority: "high", rationale: "Current BP above target on 10mg; ACE inhibitor preferred given concurrent diabetes" },
        { treatment_type: "Lifestyle", description: "DASH diet counseling, sodium restriction <2g/day", cpt_code: "97802", priority: "medium", rationale: "Dietary modification is first-line adjunct for hypertension management" },
      ],
    },
    "Type 2 Diabetes": {
      findings: [
        { category: "Labs", finding: "HbA1c 8.2%", status: "abnormal", interpretation: "Above target of 7.0% — indicates suboptimal glycemic control over past 3 months" },
        { category: "Labs", finding: "Fasting glucose 186 mg/dL", status: "abnormal", interpretation: "Elevated fasting glucose consistent with uncontrolled diabetes" },
        { category: "Labs", finding: "eGFR 58 mL/min", status: "borderline", interpretation: "CKD Stage 3a — consider renal-protective diabetes agents" },
      ],
      diagnoses: [
        { diagnosis: "Type 2 Diabetes Mellitus without complications", icd10_code: "E11.9", confidence: 0.92, rationale: "Elevated HbA1c and fasting glucose with established diabetes history", supporting_findings: ["HbA1c 8.2%", "FG 186 mg/dL"] },
        { diagnosis: "Chronic Kidney Disease, Stage 3a", icd10_code: "N18.31", confidence: 0.88, rationale: "eGFR 58 mL/min with diabetic and hypertensive nephropathy risk", supporting_findings: ["eGFR 58", "Cr 1.4"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Add Empagliflozin 10mg daily", cpt_code: "99214", priority: "high", rationale: "SGLT2 inhibitor provides glycemic control plus renal and cardiovascular protection" },
        { treatment_type: "Monitoring", description: "Repeat HbA1c in 3 months, renal panel in 6 weeks", cpt_code: "83036", priority: "medium", rationale: "Track glycemic response and renal function with new medication" },
      ],
    },
    "Atrial Fibrillation": {
      findings: [
        { category: "ECG", finding: "Irregular rhythm, absent P waves", status: "abnormal", interpretation: "Consistent with atrial fibrillation" },
        { category: "Vitals", finding: "Heart rate 112 bpm (irregular)", status: "abnormal", interpretation: "Rapid ventricular response in atrial fibrillation" },
        { category: "Labs", finding: "TSH 0.8 mIU/L", status: "normal", interpretation: "Thyroid function normal — rules out thyrotoxicosis as AF trigger" },
      ],
      diagnoses: [
        { diagnosis: "Atrial Fibrillation, Unspecified", icd10_code: "I48.91", confidence: 0.96, rationale: "ECG findings with irregular narrow-complex tachycardia and absent P waves", supporting_findings: ["Irregular rhythm", "Absent P waves", "HR 112"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Initiate Metoprolol succinate 50mg daily for rate control", cpt_code: "99214", priority: "high", rationale: "Rate control strategy for AF with rapid ventricular response; target HR <110 at rest" },
        { treatment_type: "Anticoagulation", description: "Start Apixaban 5mg BID (CHA₂DS₂-VASc = 2)", cpt_code: "99214", priority: "high", rationale: "Stroke prevention indicated with CHA₂DS₂-VASc ≥2 in female patient" },
      ],
    },
    "Heart Failure": {
      findings: [
        { category: "Labs", finding: "BNP 820 pg/mL", status: "abnormal", interpretation: "Significantly elevated — consistent with heart failure exacerbation" },
        { category: "Imaging", finding: "Ejection fraction 35%", status: "abnormal", interpretation: "Reduced EF indicating systolic dysfunction (HFrEF)" },
        { category: "Vitals", finding: "SpO2 93% on room air", status: "borderline", interpretation: "Mild hypoxemia — may indicate pulmonary congestion" },
      ],
      diagnoses: [
        { diagnosis: "Heart Failure with Reduced Ejection Fraction", icd10_code: "I50.2", confidence: 0.94, rationale: "EF 35% with elevated BNP and clinical signs of congestion", supporting_findings: ["EF 35%", "BNP 820", "SpO2 93%"] },
      ],
      treatments: [
        { treatment_type: "Medication", description: "Optimize GDMT: Sacubitril/Valsartan 24/26mg BID", cpt_code: "99214", priority: "high", rationale: "ARNI therapy reduces mortality in HFrEF per ACC/AHA guidelines" },
        { treatment_type: "Medication", description: "Add Spironolactone 25mg daily", cpt_code: "99214", priority: "high", rationale: "MRA reduces mortality in NYHA II-IV HFrEF with EF ≤35%" },
      ],
    },
  };

  const allFindings: NonNullable<ClinicalAssessment["assessment"]>["findings"] = [];
  const allDiagnoses: NonNullable<ClinicalAssessment["assessment"]>["diagnoses"] = [];
  const allTreatments: NonNullable<ClinicalAssessment["assessment"]>["treatments"] = [];

  for (const cond of patient.conditions) {
    const data = conditionData[cond];
    if (data) {
      if (data.findings) allFindings.push(...data.findings);
      if (data.diagnoses) allDiagnoses.push(...data.diagnoses);
      if (data.treatments) allTreatments.push(...data.treatments);
    }
  }

  const reasoning = [
    `=== Step 1: Patient Intake ===`,
    `Agent [Supervisor] reviewing patient ${patient.name} (${patient.age}${patient.sex}, MRN: ${patient.mrn})`,
    `Known conditions: ${patient.conditions.join(", ")}`,
    `Routing to specialist agents for comprehensive assessment...`,
    ``,
    `=== Step 2: Clinical Findings ===`,
    `Agent [Diagnostician] analyzing vitals, labs, and imaging data`,
    `Found ${allFindings.length} relevant findings across ${patient.conditions.length} condition(s)`,
    ...allFindings.filter(f => f.status === "abnormal").map(f => `  ⚠ ${f.finding} — ${f.interpretation}`),
    ``,
    `=== Step 3: Differential Diagnosis ===`,
    `Agent [Diagnostician] generating differential diagnoses with ICD-10 codes`,
    ...allDiagnoses.map(d => `  → ${d.diagnosis} (${d.icd10_code}) — confidence ${(d.confidence * 100).toFixed(0)}%`),
    ``,
    `=== Step 4: Treatment Planning ===`,
    `Agent [Treatment Planner] formulating evidence-based treatment plan`,
    ...allTreatments.map(t => `  → [${t.priority.toUpperCase()}] ${t.description}`),
    ``,
    `=== Step 5: Safety Check ===`,
    `Agent [Safety Checker] verifying drug interactions and contraindications`,
    `QC Result: PASS — No critical drug interactions detected`,
    `QC Result: PASS — Allergy screening clear`,
    `QC Result: ${allFindings.some(f => f.status === "abnormal") ? "WARN" : "PASS"} — ${allFindings.filter(f => f.status === "abnormal").length} abnormal finding(s) flagged for review`,
    ``,
    `=== Step 6: Final Review ===`,
    `Agent [Supervisor] compiling final assessment`,
    `Human review: RECOMMENDED — Complex multi-condition patient`,
    `Total agents consulted: 5 | Confidence: ${(allDiagnoses.reduce((s, d) => s + d.confidence, 0) / Math.max(allDiagnoses.length, 1) * 100).toFixed(0)}%`,
  ];

  return {
    success: true,
    patient_id: patient.id,
    llm_provider: "demo-mode",
    assessment: {
      patient_summary: { patient_id: patient.id, name: patient.name, age: patient.age, sex: patient.sex },
      findings: allFindings,
      critical_findings: allFindings.filter(f => f.status === "abnormal").map(f => ({ finding: f.finding, interpretation: f.interpretation })),
      diagnoses: allDiagnoses,
      treatments: allTreatments,
      icd10_codes: allDiagnoses.map(d => ({ code: d.icd10_code, description: d.diagnosis, confidence: d.confidence })),
      cpt_codes: allTreatments.map(t => ({ code: t.cpt_code, description: t.description })),
      confidence: allDiagnoses.reduce((s, d) => s + d.confidence, 0) / Math.max(allDiagnoses.length, 1),
      reasoning,
      warnings: allFindings.filter(f => f.status === "abnormal").map(f => f.finding),
      requires_human_review: true,
      review_reason: "Multi-condition patient with abnormal findings requires clinician verification",
    },
  };
}

const DEMO_AGENTS: AgentInfo[] = [
  { agent_id: "supervisor", name: "Clinical Supervisor", description: "Orchestrates multi-agent clinical pipeline", version: "2.0.0", specialties: ["triage", "routing"], requires_human_approval: true },
  { agent_id: "diagnostician", name: "Diagnostician", description: "Differential diagnosis with ICD-10 coding", version: "2.0.0", specialties: ["diagnosis", "ICD-10"], requires_human_approval: true },
  { agent_id: "treatment", name: "Treatment Planner", description: "Evidence-based treatment plans with CPT codes", version: "2.0.0", specialties: ["treatment", "CPT"], requires_human_approval: true },
  { agent_id: "safety", name: "Safety Checker", description: "Drug interactions, allergies, contraindications", version: "2.0.0", specialties: ["safety", "pharmacology"], requires_human_approval: false },
  { agent_id: "coding", name: "Medical Coder", description: "ICD-10 and CPT code validation", version: "2.0.0", specialties: ["coding", "billing"], requires_human_approval: false },
  { agent_id: "cardiology", name: "Cardiology Specialist", description: "Cardiovascular assessment, Framingham risk, GDMT", version: "2.0.0", specialties: ["cardiology", "echocardiography"], requires_human_approval: true },
];

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */

const TABS: { key: TabKey; label: string }[] = [
  { key: "assessment", label: "Clinical Assessment" },
  { key: "agents", label: "Specialist Agents" },
  { key: "llm", label: "LLM Configuration" },
  { key: "mcp", label: "MCP Servers" },
  { key: "simulator", label: "IoT Simulator" },
];

export default function ClinicalAssessmentPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<TabKey>("assessment");
  const [selectedPatient, setSelectedPatient] = useState(DEMO_PATIENTS[0]);
  const [assessment, setAssessment] = useState<ClinicalAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Agent state
  const [agents, setAgents] = useState<AgentInfo[]>(DEMO_AGENTS);

  // LLM state
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);

  // MCP state
  const [mcpServers, setMcpServers] = useState<Record<string, MCPServerStatus>>({});

  // Simulator state
  const [simStatus, setSimStatus] = useState<SimulatorStatus | null>(null);

  const runAssessment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<ClinicalAssessment>("/assess", {
        method: "POST",
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          include_diagnoses: true,
          include_treatments: true,
          include_codes: true,
          patient_data: PATIENT_CLINICAL_DATA[selectedPatient.id] || undefined,
        }),
      });
      setAssessment(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Assessment failed";
      if (msg === "AUTH_REQUIRED") {
        // Fall back to demo assessment when not authenticated
        await new Promise((r) => setTimeout(r, 1500)); // simulate processing
        setAssessment(buildDemoAssessment(selectedPatient));
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedPatient]);

  const loadAgents = useCallback(async () => {
    try {
      const data = await apiFetch<{ agents: AgentInfo[] }>("/agents");
      if (data.agents?.length) setAgents(data.agents);
    } catch {
      /* use demo data */
    }
  }, []);

  const loadLLMStatus = useCallback(async () => {
    try {
      const data = await apiFetch<LLMStatus>("/llm/status");
      setLlmStatus(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        setLlmStatus({
          status: "demo",
          primary_provider: "claude-sonnet-4-6 (demo)",
          available_providers: ["claude-sonnet-4-6", "gpt-4o", "gemini-2.0-flash"],
          config: { temperature: 0.2, max_tokens: 4096, top_p: 0.9 },
        });
      } else {
        setLlmStatus({ status: "unavailable", error: "Orchestrator not reachable" });
      }
    }
  }, []);

  const loadMCPStatus = useCallback(async () => {
    try {
      const data = await apiFetch<{ mcp_servers: Record<string, MCPServerStatus> }>("/mcp/status");
      setMcpServers(data.mcp_servers || {});
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        setMcpServers({
          "fhir-server": { url: "http://localhost:8090", status: "demo" },
          "audit-server": { url: "http://localhost:8091", status: "demo" },
          "terminology-server": { url: "http://localhost:8092", status: "demo" },
        });
      }
    }
  }, []);

  const loadSimStatus = useCallback(async () => {
    try {
      const data = await apiFetch<SimulatorStatus>("/simulator/status");
      setSimStatus(data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        setSimStatus({ running: false, devices_count: 6, observations_sent: 0, alerts_generated: 0, errors_count: 0 });
      } else {
        setSimStatus({ running: false, error: "Simulator not reachable" });
      }
    }
  }, []);

  const switchProvider = useCallback(async (provider: string) => {
    try {
      await apiFetch("/llm/switch?provider=" + encodeURIComponent(provider), { method: "POST" });
      await loadLLMStatus();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg === "AUTH_REQUIRED") {
        // In demo mode, simulate switching
        setLlmStatus((prev) => prev ? { ...prev, primary_provider: provider } : prev);
      }
    }
  }, [loadLLMStatus]);

  useEffect(() => {
    if (tab === "agents") loadAgents();
    if (tab === "llm") loadLLMStatus();
    if (tab === "mcp") loadMCPStatus();
    if (tab === "simulator") loadSimStatus();
  }, [tab, loadAgents, loadLLMStatus, loadMCPStatus, loadSimStatus]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Clinical Decision Support
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-500">
          AI-powered multi-agent clinical assessment with specialist agents, LLM orchestration, and FHIR integration
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-4 sm:gap-6 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`whitespace-nowrap border-b-2 pb-3 pt-1 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "border-healthos-500 text-healthos-600 dark:text-healthos-400"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {tab === "assessment" && (
        <AssessmentTab
          patients={DEMO_PATIENTS}
          selectedPatient={selectedPatient}
          onSelectPatient={setSelectedPatient}
          assessment={assessment}
          loading={loading}
          error={error}
          onRunAssessment={runAssessment}
          physicianName={user?.full_name || "Reviewing Physician"}
          physicianEmail={user?.email}
        />
      )}
      {tab === "agents" && <AgentsTab agents={agents} />}
      {tab === "llm" && <LLMTab status={llmStatus} onRefresh={loadLLMStatus} onSwitch={switchProvider} />}
      {tab === "mcp" && <MCPTab servers={mcpServers} onRefresh={loadMCPStatus} />}
      {tab === "simulator" && <SimulatorTab status={simStatus} onRefresh={loadSimStatus} />}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   ASSESSMENT TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function AssessmentTab({
  patients,
  selectedPatient,
  onSelectPatient,
  assessment,
  loading,
  error,
  onRunAssessment,
  physicianName,
  physicianEmail,
}: {
  patients: typeof DEMO_PATIENTS;
  selectedPatient: (typeof DEMO_PATIENTS)[0];
  onSelectPatient: (p: (typeof DEMO_PATIENTS)[0]) => void;
  assessment: ClinicalAssessment | null;
  loading: boolean;
  error: string | null;
  onRunAssessment: () => void;
  physicianName: string;
  physicianEmail?: string;
}) {
  // HITL Review State
  const [reviewDecisions, setReviewDecisions] = useState<Record<string, "approve" | "reject" | "modify">>({});
  const [clinicalNotes, setClinicalNotes] = useState("");
  const [attestChecked, setAttestChecked] = useState(false);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [reviewStartedAt] = useState(new Date().toISOString());
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [workflowResult, setWorkflowResult] = useState<Record<string, any> | null>(null);

  // Reset review state when assessment changes
  useEffect(() => {
    setReviewDecisions({});
    setClinicalNotes("");
    setAttestChecked(false);
    setReviewSubmitted(false);
    setWorkflowResult(null);
  }, [assessment]);

  const allDiagnoses = assessment?.assessment?.diagnoses ?? [];
  const allTreatments = assessment?.assessment?.treatments ?? [];
  const totalItems = allDiagnoses.length + allTreatments.length;
  const reviewedCount = Object.keys(reviewDecisions).length;
  const allReviewed = totalItems > 0 && reviewedCount >= totalItems;
  const canSubmit = allReviewed && attestChecked && clinicalNotes.trim().length > 0;

  const toggleDecision = (key: string, decision: "approve" | "reject" | "modify") => {
    setReviewDecisions((prev) => {
      const next = { ...prev };
      if (next[key] === decision) delete next[key];
      else next[key] = decision;
      return next;
    });
  };

  // Compute approved/rejected indices from decisions
  const getReviewIndices = () => {
    const approvedDx: number[] = [];
    const rejectedDx: number[] = [];
    const approvedTx: number[] = [];
    const rejectedTx: number[] = [];
    Object.entries(reviewDecisions).forEach(([key, decision]) => {
      const [type, idxStr] = key.split("-");
      const idx = parseInt(idxStr);
      if (type === "dx") {
        if (decision === "approve") approvedDx.push(idx);
        else rejectedDx.push(idx);
      } else if (type === "tx") {
        if (decision === "approve") approvedTx.push(idx);
        else rejectedTx.push(idx);
      }
    });
    return { approvedDx, rejectedDx, approvedTx, rejectedTx };
  };

  const handleSubmitReview = async () => {
    setSubmitting(true);
    const { approvedDx, rejectedDx, approvedTx, rejectedTx } = getReviewIndices();
    const allApproved = rejectedDx.length === 0 && rejectedTx.length === 0;
    const decision = allApproved ? "approved" : "approved_modified";

    try {
      // Call the real backend endpoint
      const result = await fetch("/api/v1/clinical/reviews/submit/", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuth() },
        body: JSON.stringify({
          assessment_id: assessment?.assessment?.review_reason || assessment?.patient_id || "assessment",
          patient_id: assessment?.patient_id || "1",
          physician_name: physicianName,
          physician_specialty: "Internal Medicine",
          decision,
          approved_diagnoses: approvedDx,
          rejected_diagnoses: rejectedDx,
          approved_treatments: approvedTx,
          rejected_treatments: rejectedTx,
          physician_notes: clinicalNotes,
          clinical_rationale: clinicalNotes,
          attest: attestChecked,
          review_started_at: reviewStartedAt,
          diagnoses: allDiagnoses,
          treatments: allTreatments,
          icd10_codes: assessment?.assessment?.icd10_codes || [],
          cpt_codes: assessment?.assessment?.cpt_codes || [],
        }),
      });
      if (result.ok) {
        const data = await result.json();
        setWorkflowResult(data);
      }
    } catch {
      // Demo fallback — simulate the workflow result
      setWorkflowResult({
        id: `review-${Date.now()}`,
        decision,
        physician_name: physicianName,
        attested: attestChecked,
        signature_datetime: new Date().toISOString(),
        review_completed_at: new Date().toISOString(),
        time_spent_seconds: Math.floor((Date.now() - new Date(reviewStartedAt).getTime()) / 1000),
        workflow_status: "completed",
        treatment_plan_created: decision !== "rejected",
        patient_notified: decision !== "rejected",
        pharmacy_ordered: approvedTx.some((i) => {
          const t = allTreatments[i];
          return t && ["medication", "anticoagulation"].includes(t.treatment_type?.toLowerCase());
        }),
        orders_created: approvedTx.length,
        approved_diagnoses: approvedDx,
        rejected_diagnoses: rejectedDx,
        approved_treatments: approvedTx,
        rejected_treatments: rejectedTx,
      });
    }
    setReviewSubmitted(true);
    setSubmitting(false);
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Patient Picker */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
        <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">Select Patient</h3>
        <div className="space-y-2">
          {patients.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectPatient(p)}
              className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition-all ${
                selectedPatient.id === p.id
                  ? "border-healthos-500 bg-healthos-50 dark:bg-healthos-950/30"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-500"
              }`}
            >
              <div className="font-medium text-gray-900 dark:text-gray-100">{p.name}</div>
              <div className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {p.mrn} &middot; {p.age}y {p.sex} &middot; {p.conditions.join(", ")}
              </div>
            </button>
          ))}
        </div>

        <button
          onClick={onRunAssessment}
          disabled={loading}
          className="mt-4 w-full rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-healthos-700 disabled:opacity-50"
        >
          {loading ? "Running Assessment..." : "Run AI Clinical Assessment"}
        </button>
      </div>

      {/* Results */}
      <div className="lg:col-span-2 space-y-4">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 sm:p-12 dark:bg-gray-800">
            <div className="text-center">
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
              <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Running multi-agent clinical assessment...</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Supervisor &rarr; Diagnostician &rarr; Treatment &rarr; Safety &rarr; Coding</p>
            </div>
          </div>
        )}

        {assessment?.assessment && !loading && (
          <>
            {/* Status Banner */}
            <div className={`rounded-lg border-2 overflow-hidden ${
              assessment.assessment.requires_human_review
                ? "border-amber-400 dark:border-amber-600"
                : "border-emerald-400 dark:border-emerald-600"
            }`}>
              <div className={`px-5 py-4 flex items-center justify-between ${
                assessment.assessment.requires_human_review
                  ? "bg-amber-50 dark:bg-amber-900/20"
                  : "bg-emerald-50 dark:bg-emerald-900/20"
              }`}>
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-lg font-bold ${
                    assessment.assessment.requires_human_review ? "bg-amber-500" : "bg-emerald-500"
                  }`}>
                    {assessment.assessment.requires_human_review ? "!" : "\u2713"}
                  </div>
                  <div>
                    <p className={`font-bold text-sm ${
                      assessment.assessment.requires_human_review
                        ? "text-amber-800 dark:text-amber-400"
                        : "text-emerald-800 dark:text-emerald-400"
                    }`}>
                      {assessment.assessment.requires_human_review ? "REQUIRES PHYSICIAN REVIEW" : "ASSESSMENT COMPLETE"}
                    </p>
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                      AI Confidence: <strong>{((assessment.assessment.confidence ?? 0) * 100).toFixed(0)}%</strong>
                      {assessment.llm_provider && <> &middot; Engine: {assessment.llm_provider}</>}
                    </p>
                  </div>
                </div>
                {assessment.assessment.requires_human_review && (
                  <span className="px-4 py-2 rounded-md bg-red-600 text-white text-xs font-bold shadow-sm">REVIEW REQUIRED</span>
                )}
              </div>
              {(assessment.assessment.warnings?.length ?? 0) > 0 && (
                <div className="px-5 py-3 space-y-1.5 border-t border-gray-200/50 dark:border-gray-700/50">
                  {assessment.assessment.warnings!.map((w, i) => (
                    <div key={i} className="px-3 py-2 rounded bg-red-100 dark:bg-red-900/20 text-xs text-red-700 dark:text-red-400">
                      <strong>WARNING:</strong> {w}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Patient Clinical Context */}
            {(() => {
              const pd = PATIENT_CLINICAL_DATA[assessment.patient_id];
              if (!pd) return null;
              return (
                <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-50 dark:bg-slate-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                    <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                    </svg>
                    <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Patient Clinical Context</span>
                  </div>
                  <div className="p-4 space-y-4 text-[12px]">
                    {/* Demographics + Chief Complaint */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="font-bold text-gray-900 dark:text-gray-100 text-sm">{pd.name}</p>
                        <p className="text-gray-500 mt-0.5">{pd.age}y {pd.sex} &middot; DOB: {pd.date_of_birth}</p>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">Chief Complaint</p>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{pd.chief_complaint}</p>
                      </div>
                    </div>

                    {/* HPI */}
                    {pd.history_present_illness && (
                      <div>
                        <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">History of Present Illness</p>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{pd.history_present_illness}</p>
                      </div>
                    )}

                    {/* Physician Notes */}
                    {pd.physician_notes && (
                      <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20 p-3">
                        <div className="flex items-center gap-1.5 mb-1">
                          <svg className="h-3.5 w-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                          </svg>
                          <span className="font-bold text-blue-700 dark:text-blue-400 text-[10px] uppercase tracking-wide">Physician Notes</span>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{pd.physician_notes}</p>
                      </div>
                    )}

                    {/* Ambient AI Notes */}
                    {pd.ambient_ai_notes && (
                      <div className="rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50/50 dark:bg-violet-950/20 p-3">
                        <div className="flex items-center gap-1.5 mb-1">
                          <svg className="h-3.5 w-3.5 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                          </svg>
                          <span className="font-bold text-violet-700 dark:text-violet-400 text-[10px] uppercase tracking-wide">Ambient AI Clinical Documentation</span>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{pd.ambient_ai_notes}</p>
                      </div>
                    )}

                    {/* Appointment Notes (Telehealth & In-Person) */}
                    {pd.appointment_notes?.length > 0 && (
                      <div>
                        <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-2">Appointment History</p>
                        <div className="space-y-2">
                          {pd.appointment_notes.map((appt: { type: string; date: string; provider: string; summary: string }, i: number) => (
                            <div key={i} className={`rounded-lg border p-3 ${
                              appt.type === "telehealth"
                                ? "border-cyan-200 dark:border-cyan-800 bg-cyan-50/30 dark:bg-cyan-950/10"
                                : "border-emerald-200 dark:border-emerald-800 bg-emerald-50/30 dark:bg-emerald-950/10"
                            }`}>
                              <div className="flex items-center gap-2 mb-1">
                                {appt.type === "telehealth" ? (
                                  <svg className="h-3.5 w-3.5 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
                                  </svg>
                                ) : (
                                  <svg className="h-3.5 w-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
                                  </svg>
                                )}
                                <span className={`text-[9px] font-bold uppercase tracking-wide ${
                                  appt.type === "telehealth" ? "text-cyan-600 dark:text-cyan-400" : "text-emerald-600 dark:text-emerald-400"
                                }`}>{appt.type === "telehealth" ? "Telehealth Visit" : "In-Person Visit"}</span>
                                <span className="text-[10px] text-gray-500">{appt.date}</span>
                                <span className="text-[10px] font-medium text-gray-700 dark:text-gray-300 ml-auto">{appt.provider}</span>
                              </div>
                              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{appt.summary}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Medications + Allergies row */}
                    <div className="grid grid-cols-2 gap-4">
                      {pd.medications?.length > 0 && (
                        <div>
                          <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">Current Medications</p>
                          <div className="flex flex-wrap gap-1">
                            {pd.medications.map((m: { medication_name: string }, i: number) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 text-[10px]">{m.medication_name}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {pd.allergies?.length > 0 && (
                        <div>
                          <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">Allergies</p>
                          <div className="flex flex-wrap gap-1">
                            {pd.allergies.map((a: { substance: string; severity: string }, i: number) => (
                              <span key={i} className={`px-1.5 py-0.5 rounded text-[10px] ${a.severity === "severe" ? "bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400" : "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400"}`}>
                                {a.substance} ({a.severity})
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Active Conditions */}
                    {pd.conditions?.length > 0 && (
                      <div>
                        <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">Active Conditions</p>
                        <div className="flex flex-wrap gap-1">
                          {pd.conditions.map((c: { code: string; display: string }, i: number) => (
                            <span key={i} className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-[10px]">
                              <strong className="text-blue-700 dark:text-blue-400">{c.code}</strong> {c.display}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Past Medical History + Family History + Social History */}
                    <div className="grid grid-cols-3 gap-4">
                      {pd.past_medical_history?.length > 0 && (
                        <div>
                          <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">Past Medical History</p>
                          <ul className="space-y-0.5">
                            {pd.past_medical_history.map((h: string, i: number) => (
                              <li key={i} className="text-gray-700 dark:text-gray-300 text-[11px] leading-relaxed flex items-start gap-1">
                                <span className="text-gray-400 mt-0.5 shrink-0">-</span> {h}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {pd.family_history?.length > 0 && (
                        <div>
                          <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">Family History</p>
                          <ul className="space-y-0.5">
                            {pd.family_history.map((h: string, i: number) => (
                              <li key={i} className="text-gray-700 dark:text-gray-300 text-[11px] leading-relaxed flex items-start gap-1">
                                <span className="text-gray-400 mt-0.5 shrink-0">-</span> {h}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {pd.social_history && (
                        <div>
                          <p className="font-semibold text-gray-600 dark:text-gray-400 text-[10px] uppercase tracking-wide mb-1">Social History</p>
                          <ul className="space-y-0.5">
                            {Object.entries(pd.social_history).map(([key, val]: [string, unknown]) => (
                              <li key={key} className="text-[11px] leading-relaxed">
                                <span className="font-medium text-gray-600 dark:text-gray-400 capitalize">{key}:</span>{" "}
                                <span className="text-gray-700 dark:text-gray-300">{String(val)}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Mental Health Screening */}
                    {pd.mental_health && (
                      <div className={`rounded-lg border p-3 ${
                        pd.mental_health.severity === "moderate" || pd.mental_health.severity === "moderately severe"
                          ? "border-amber-300 dark:border-amber-700 bg-amber-50/50 dark:bg-amber-950/20"
                          : pd.mental_health.severity === "severe"
                          ? "border-red-300 dark:border-red-700 bg-red-50/50 dark:bg-red-950/20"
                          : "border-purple-200 dark:border-purple-800 bg-purple-50/30 dark:bg-purple-950/10"
                      }`}>
                        <div className="flex items-center gap-2 mb-2">
                          <svg className="h-3.5 w-3.5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.182 15.182a4.5 4.5 0 01-6.364 0M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm-.375 0h.008v.015h-.008V9.75zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75zm-.375 0h.008v.015h-.008V9.75z" />
                          </svg>
                          <span className="font-bold text-purple-700 dark:text-purple-400 text-[10px] uppercase tracking-wide">Mental Health Screening</span>
                          <span className={`ml-auto px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                            pd.mental_health.severity === "minimal" || pd.mental_health.severity === "none"
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                              : pd.mental_health.severity === "mild"
                              ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                              : pd.mental_health.severity === "moderate"
                              ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                              : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                          }`}>
                            {pd.mental_health.severity}
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-3 mb-2">
                          <div className="text-center p-2 rounded bg-white/60 dark:bg-gray-900/40">
                            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{pd.mental_health.score}</p>
                            <p className="text-[9px] font-semibold uppercase text-gray-500">{pd.mental_health.screening} Score</p>
                          </div>
                          {pd.mental_health.phq9_score != null && (
                            <div className="text-center p-2 rounded bg-white/60 dark:bg-gray-900/40">
                              <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{pd.mental_health.phq9_score}</p>
                              <p className="text-[9px] font-semibold uppercase text-gray-500">PHQ-9</p>
                            </div>
                          )}
                          {pd.mental_health.gad7_score != null && (
                            <div className="text-center p-2 rounded bg-white/60 dark:bg-gray-900/40">
                              <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{pd.mental_health.gad7_score}</p>
                              <p className="text-[9px] font-semibold uppercase text-gray-500">GAD-7</p>
                            </div>
                          )}
                          <div className="text-center p-2 rounded bg-white/60 dark:bg-gray-900/40">
                            <p className="text-[11px] font-semibold text-gray-700 dark:text-gray-300">{pd.mental_health.last_screened}</p>
                            <p className="text-[9px] font-semibold uppercase text-gray-500">Last Screened</p>
                          </div>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{pd.mental_health.notes}</p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Findings Summary */}
            {(assessment.assessment.findings?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                  <svg className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                  <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Clinical Findings ({assessment.assessment.findings!.length})</span>
                </div>
                <div className="p-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {assessment.assessment.findings!.map((f, i) => {
                      const statusColors: Record<string, string> = {
                        abnormal: "border-l-red-500 bg-red-50/50 dark:bg-red-950/20",
                        borderline: "border-l-amber-500 bg-amber-50/50 dark:bg-amber-950/20",
                        critical: "border-l-red-600 bg-red-100/50 dark:bg-red-950/30",
                        normal: "border-l-emerald-500 bg-emerald-50/30 dark:bg-emerald-950/10",
                      };
                      const cls = statusColors[f.status] || statusColors.normal;
                      return (
                        <div key={i} className={`rounded-md border-l-[3px] px-3 py-2 ${cls}`}>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold uppercase tracking-wide text-gray-400">{f.category}</span>
                            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                              f.status === "abnormal" || f.status === "critical" ? "bg-red-200 text-red-700 dark:bg-red-900/40 dark:text-red-400" :
                              f.status === "borderline" ? "bg-amber-200 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400" :
                              "bg-emerald-200 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
                            }`}>{f.status}</span>
                          </div>
                          <p className="text-[12px] font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{f.finding}</p>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">{f.interpretation}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Diagnoses */}
            {(assessment.assessment.diagnoses?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                  <svg className="h-4 w-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5" />
                  </svg>
                  <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">AI-Generated Diagnoses ({assessment.assessment.diagnoses!.length})</span>
                </div>
                <div className="p-4 space-y-3">
                  {assessment.assessment.diagnoses!.map((d, i) => {
                    const confColor = d.confidence >= 0.8 ? "text-emerald-600" : d.confidence >= 0.5 ? "text-amber-600" : "text-red-600";
                    return (
                      <div key={i} className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
                        <div className="flex items-center gap-3 px-4 py-3 bg-gray-50/50 dark:bg-gray-800/30">
                          <span className="w-7 h-7 rounded-full bg-blue-800 text-white text-[11px] font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{d.diagnosis}</p>
                            <div className="flex gap-4 mt-1 text-[11px] text-gray-500">
                              <span>ICD-10: <strong className="text-blue-700 dark:text-blue-400">{d.icd10_code}</strong></span>
                              <span>Confidence: <strong className={confColor}>{(d.confidence * 100).toFixed(0)}%</strong></span>
                            </div>
                          </div>
                        </div>
                        <div className="px-4 py-2.5 border-t border-gray-100 dark:border-gray-800 text-xs text-gray-600 dark:text-gray-400">{d.rationale}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Treatments */}
            {(assessment.assessment.treatments?.length ?? 0) > 0 && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                  <svg className="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                  </svg>
                  <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Treatment Recommendations ({assessment.assessment.treatments!.length})</span>
                </div>
                <div className="p-4 space-y-3">
                  {assessment.assessment.treatments!.map((t, i) => {
                    const pCfg: Record<string, string> = { immediate: "bg-red-600", urgent: "bg-amber-600", routine: "bg-blue-600", elective: "bg-purple-600" };
                    const pBg = pCfg[t.priority] || pCfg.routine;
                    return (
                      <div key={i} className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
                        <div className="flex items-start gap-3 px-4 py-3">
                          <span className="w-7 h-7 rounded-full bg-emerald-700 text-white text-[11px] font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              <span className={`${pBg} text-white px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide`}>{t.priority}</span>
                              <span className="text-[10px] text-gray-500 capitalize font-medium">{t.treatment_type}</span>
                              {t.cpt_code && <span className="ml-auto px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-semibold">CPT: {t.cpt_code}</span>}
                            </div>
                            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{t.description}</p>
                            <p className="text-[11px] text-gray-500 mt-1">{t.rationale}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Billing Codes */}
            {((assessment.assessment.icd10_codes?.length ?? 0) > 0 || (assessment.assessment.cpt_codes?.length ?? 0) > 0) && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                  <svg className="h-4 w-4 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                  </svg>
                  <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Clinical Billing Codes</span>
                </div>
                <div className="p-4 grid grid-cols-2 gap-5">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-400 mb-2">ICD-10 Codes</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(assessment.assessment.icd10_codes ?? []).map((c, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 text-[10px] font-semibold border border-blue-200 dark:border-blue-700">
                          {c.code} <span className="text-gray-500 font-normal">{((c as Record<string, unknown>).confidence as number) ? `(${(((c as Record<string, unknown>).confidence as number) * 100).toFixed(0)}%)` : ""}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-2">CPT Codes</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(assessment.assessment.cpt_codes ?? []).map((c, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-400 text-[10px] font-semibold border border-emerald-200 dark:border-emerald-700">
                          {c.code}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ═══ HITL PHYSICIAN REVIEW PANEL ═══ */}
            {assessment.assessment.requires_human_review && !reviewSubmitted && (
              <div className="rounded-xl border-2 border-amber-400 dark:border-amber-600 overflow-hidden shadow-sm">
                <div className="px-5 py-4 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/20 border-b border-amber-200 dark:border-amber-700">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-amber-500 flex items-center justify-center shadow-sm">
                      <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-amber-900 dark:text-amber-300">Physician Review Required (HITL)</h3>
                      <p className="text-[11px] text-amber-700 dark:text-amber-400 mt-0.5">
                        Review each diagnosis and treatment recommendation. Approve, reject, or modify each item.
                        {assessment.assessment.review_reason && <> &middot; {assessment.assessment.review_reason}</>}
                      </p>
                    </div>
                  </div>
                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-[10px] font-semibold text-amber-700 dark:text-amber-400 mb-1">
                      <span>Review Progress</span>
                      <span>{reviewedCount} / {totalItems} items reviewed</span>
                    </div>
                    <div className="h-2 rounded-full bg-amber-200 dark:bg-amber-900/50 overflow-hidden">
                      <div className="h-full rounded-full bg-amber-500 transition-all duration-300" style={{ width: `${totalItems > 0 ? (reviewedCount / totalItems) * 100 : 0}%` }} />
                    </div>
                  </div>
                </div>

                <div className="p-5 space-y-4 bg-white dark:bg-gray-900">
                  {/* Diagnosis Review */}
                  {allDiagnoses.length > 0 && (
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-400 mb-2">Review Diagnoses</p>
                      <div className="space-y-2">
                        {allDiagnoses.map((d, i) => {
                          const key = `dx-${i}`;
                          const decision = reviewDecisions[key];
                          return (
                            <div key={key} className={`rounded-lg border px-4 py-3 transition-all ${
                              decision === "approve" ? "border-emerald-300 bg-emerald-50/50 dark:border-emerald-700 dark:bg-emerald-950/20" :
                              decision === "reject" ? "border-red-300 bg-red-50/50 dark:border-red-700 dark:bg-red-950/20" :
                              decision === "modify" ? "border-amber-300 bg-amber-50/50 dark:border-amber-700 dark:bg-amber-950/20" :
                              "border-gray-200 dark:border-gray-700"
                            }`}>
                              <div className="flex items-center justify-between">
                                <div className="flex-1 mr-4">
                                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{d.diagnosis}</p>
                                  <p className="text-[11px] text-gray-500 mt-0.5">
                                    ICD-10: <strong className="text-blue-700 dark:text-blue-400">{d.icd10_code}</strong>
                                    &nbsp;&middot;&nbsp;Confidence: <strong>{(d.confidence * 100).toFixed(0)}%</strong>
                                  </p>
                                </div>
                                <div className="flex gap-1.5 shrink-0">
                                  {(["approve", "reject", "modify"] as const).map((act) => {
                                    const cfg: Record<string, { label: string; active: string; idle: string }> = {
                                      approve: { label: "Approve", active: "bg-emerald-600 text-white", idle: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30" },
                                      reject: { label: "Reject", active: "bg-red-600 text-white", idle: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-red-100 dark:hover:bg-red-900/30" },
                                      modify: { label: "Modify", active: "bg-amber-600 text-white", idle: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-amber-100 dark:hover:bg-amber-900/30" },
                                    };
                                    const c = cfg[act];
                                    return (
                                      <button
                                        key={act}
                                        onClick={() => toggleDecision(key, act)}
                                        className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wide transition-all ${decision === act ? c.active : c.idle}`}
                                      >
                                        {c.label}
                                      </button>
                                    );
                                  })}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Treatment Review */}
                  {allTreatments.length > 0 && (
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-2">Review Treatment Recommendations</p>
                      <div className="space-y-2">
                        {allTreatments.map((t, i) => {
                          const key = `tx-${i}`;
                          const decision = reviewDecisions[key];
                          const pCfg: Record<string, string> = { immediate: "bg-red-600", urgent: "bg-amber-600", high: "bg-red-600", routine: "bg-blue-600", medium: "bg-amber-600", elective: "bg-purple-600" };
                          const pBg = pCfg[t.priority] || pCfg.routine;
                          return (
                            <div key={key} className={`rounded-lg border px-4 py-3 transition-all ${
                              decision === "approve" ? "border-emerald-300 bg-emerald-50/50 dark:border-emerald-700 dark:bg-emerald-950/20" :
                              decision === "reject" ? "border-red-300 bg-red-50/50 dark:border-red-700 dark:bg-red-950/20" :
                              decision === "modify" ? "border-amber-300 bg-amber-50/50 dark:border-amber-700 dark:bg-amber-950/20" :
                              "border-gray-200 dark:border-gray-700"
                            }`}>
                              <div className="flex items-center justify-between">
                                <div className="flex-1 mr-4">
                                  <div className="flex items-center gap-2 mb-0.5">
                                    <span className={`${pBg} text-white px-1.5 py-0.5 rounded text-[8px] font-bold uppercase`}>{t.priority}</span>
                                    <span className="text-[10px] text-gray-500 capitalize">{t.treatment_type}</span>
                                  </div>
                                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{t.description}</p>
                                </div>
                                <div className="flex gap-1.5 shrink-0">
                                  {(["approve", "reject", "modify"] as const).map((act) => {
                                    const cfg: Record<string, { label: string; active: string; idle: string }> = {
                                      approve: { label: "Approve", active: "bg-emerald-600 text-white", idle: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30" },
                                      reject: { label: "Reject", active: "bg-red-600 text-white", idle: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-red-100 dark:hover:bg-red-900/30" },
                                      modify: { label: "Modify", active: "bg-amber-600 text-white", idle: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-amber-100 dark:hover:bg-amber-900/30" },
                                    };
                                    const c = cfg[act];
                                    return (
                                      <button
                                        key={act}
                                        onClick={() => toggleDecision(key, act)}
                                        className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wide transition-all ${decision === act ? c.active : c.idle}`}
                                      >
                                        {c.label}
                                      </button>
                                    );
                                  })}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Clinical Notes */}
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-gray-600 dark:text-gray-400 mb-1.5">
                      Physician Clinical Notes <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={clinicalNotes}
                      onChange={(e) => setClinicalNotes(e.target.value)}
                      rows={3}
                      placeholder="Add clinical rationale for your review decisions, modifications, or additional orders..."
                      className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none transition-all"
                    />
                  </div>

                  {/* Attestation */}
                  <label className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 cursor-pointer hover:border-healthos-400 transition-all">
                    <input
                      type="checkbox"
                      checked={attestChecked}
                      onChange={(e) => setAttestChecked(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-gray-300 text-healthos-600 focus:ring-healthos-500"
                    />
                    <span className="text-[12px] text-gray-700 dark:text-gray-300 leading-relaxed">
                      I, the reviewing physician, attest that I have independently reviewed all AI-generated diagnoses and treatment recommendations.
                      I accept clinical responsibility for the approved items and any modifications made. This review constitutes my professional medical judgment.
                    </span>
                  </label>

                  {/* Submit */}
                  <div className="flex items-center justify-between pt-2">
                    <div className="text-[11px] text-gray-500">
                      {!allReviewed && <span className="text-amber-600 dark:text-amber-400">Review all items to submit</span>}
                      {allReviewed && !attestChecked && <span className="text-amber-600 dark:text-amber-400">Attestation required</span>}
                      {allReviewed && attestChecked && !clinicalNotes.trim() && <span className="text-amber-600 dark:text-amber-400">Clinical notes required</span>}
                      {canSubmit && <span className="text-emerald-600 dark:text-emerald-400">Ready to submit</span>}
                    </div>
                    <button
                      onClick={handleSubmitReview}
                      disabled={!canSubmit || submitting}
                      className="px-6 py-2.5 rounded-lg bg-healthos-600 text-white text-sm font-bold shadow-sm hover:bg-healthos-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                    >
                      {submitting ? "Submitting..." : "Submit Physician Review"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ═══ POST-REVIEW: WORKFLOW STATUS TRACKER ═══ */}
            {reviewSubmitted && (
              <div className="rounded-xl border-2 border-emerald-400 dark:border-emerald-600 overflow-hidden shadow-sm">
                {/* Header */}
                <div className="px-5 py-4 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/20 border-b border-emerald-200 dark:border-emerald-700">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center shadow-sm">
                      <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-emerald-900 dark:text-emerald-300">Physician Review Submitted &mdash; Workflow Active</h3>
                      <p className="text-[11px] text-emerald-700 dark:text-emerald-400 mt-0.5">
                        Review recorded at {new Date().toLocaleString()} &middot; Signed electronically
                        {workflowResult?.workflow_status && <> &middot; Status: <strong>{workflowResult.workflow_status}</strong></>}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-5 bg-white dark:bg-gray-900 space-y-4">
                  {/* Decision Summary Grid */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/20">
                      <p className="text-xl font-bold text-emerald-600">{Object.values(reviewDecisions).filter(d => d === "approve").length}</p>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">Approved</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-red-50 dark:bg-red-950/20">
                      <p className="text-xl font-bold text-red-600">{Object.values(reviewDecisions).filter(d => d === "reject").length}</p>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-red-700 dark:text-red-400">Rejected</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20">
                      <p className="text-xl font-bold text-amber-600">{Object.values(reviewDecisions).filter(d => d === "modify").length}</p>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">Modified</p>
                    </div>
                  </div>

                  {/* ── Post-Approval Workflow Pipeline ── */}
                  <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                      <svg className="h-4 w-4 text-healthos-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                      </svg>
                      <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Post-Approval Workflow</span>
                    </div>
                    <div className="p-4 space-y-3">
                      {[
                        {
                          label: "Treatment Plan Created",
                          detail: "DoctorTreatmentPlan created from approved items, visible in Patient Portal",
                          done: workflowResult?.treatment_plan_created ?? true,
                          icon: "M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75",
                        },
                        {
                          label: "Patient Notified",
                          detail: "Patient notified via portal, SMS, and email per preferences",
                          done: workflowResult?.patient_notified ?? true,
                          icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0",
                        },
                        {
                          label: "Pharmacy Orders Submitted",
                          detail: workflowResult?.pharmacy_ordered
                            ? "E-prescriptions created and transmitted to pharmacy"
                            : "No medication orders in this assessment",
                          done: workflowResult?.pharmacy_ordered ?? false,
                          icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5",
                          skipped: !workflowResult?.pharmacy_ordered && Object.values(reviewDecisions).some(d => d === "approve"),
                        },
                        {
                          label: "EHR Orders Created",
                          detail: `${workflowResult?.orders_created ?? 0} order(s) submitted to EHR system`,
                          done: (workflowResult?.orders_created ?? 0) > 0,
                          icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z",
                        },
                        {
                          label: "Care Team Notified",
                          detail: "PCP, care manager, and nursing staff notified of plan changes",
                          done: workflowResult?.workflow_status === "completed",
                          icon: "M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z",
                        },
                        {
                          label: "Insurance Pre-Authorization",
                          detail: "Pre-auth requirements checked for procedures and medications",
                          done: workflowResult?.workflow_status === "completed",
                          icon: "M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z",
                        },
                        {
                          label: "Clinical Document Generated",
                          detail: "Assessment summary available for download (PDF/HTML)",
                          done: workflowResult?.workflow_status === "completed",
                          icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z",
                        },
                      ].map((step, i) => (
                        <div key={i} className="flex items-start gap-3">
                          <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                            step.done ? "bg-emerald-500" : step.skipped ? "bg-gray-300 dark:bg-gray-600" : "bg-amber-400"
                          }`}>
                            {step.done ? (
                              <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                              </svg>
                            ) : step.skipped ? (
                              <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
                              </svg>
                            ) : (
                              <svg className="h-3.5 w-3.5 text-white animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                              </svg>
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className={`text-[13px] font-semibold ${step.done ? "text-emerald-700 dark:text-emerald-400" : step.skipped ? "text-gray-400" : "text-amber-700 dark:text-amber-400"}`}>
                                {step.label}
                              </p>
                              <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                                step.done ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                                : step.skipped ? "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500"
                                : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                              }`}>
                                {step.done ? "Complete" : step.skipped ? "N/A" : "Processing"}
                              </span>
                            </div>
                            <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">{step.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Electronic Signature Block */}
                  <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800/50">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                      </svg>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-600 dark:text-gray-400">Electronic Signature</span>
                    </div>
                    <p className="text-[12px] text-gray-700 dark:text-gray-300 leading-relaxed">
                      Reviewed and electronically signed by <strong>{physicianName}</strong>.
                      All AI-generated recommendations have been independently evaluated.
                      Clinical responsibility accepted for approved items per institutional HITL protocol.
                    </p>
                    <p className="text-[11px] text-gray-500 mt-2">
                      Physician: <strong>{physicianName}</strong>{physicianEmail && <>&nbsp;&middot;&nbsp;{physicianEmail}</>}
                      &nbsp;&middot;&nbsp;Patient: <strong>{assessment.assessment?.patient_summary?.name ?? `ID ${assessment.patient_id}`}</strong>
                      &nbsp;&middot;&nbsp;Date: <strong>{new Date().toLocaleDateString()}</strong>
                      &nbsp;&middot;&nbsp;Time: <strong>{new Date().toLocaleTimeString()}</strong>
                      {workflowResult?.time_spent_seconds != null && (
                        <>&nbsp;&middot;&nbsp;Review time: <strong>{Math.floor(workflowResult.time_spent_seconds / 60)}m {workflowResult.time_spent_seconds % 60}s</strong></>
                      )}
                    </p>
                  </div>

                  {/* Clinical Notes Echo */}
                  {clinicalNotes.trim() && (
                    <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Physician Notes</p>
                      <p className="text-[12px] text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{clinicalNotes}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Reasoning Chain */}
            {(assessment.assessment.reasoning?.length ?? 0) > 0 && (
              <ReasoningChain steps={assessment.assessment.reasoning!} />
            )}
          </>
        )}

        {!assessment && !loading && !error && (
          <div className="flex items-center justify-center rounded-xl border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 p-6 sm:p-16">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <h3 className="mt-3 text-sm font-medium text-gray-900 dark:text-gray-200">No Assessment Yet</h3>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Select a patient and click &ldquo;Run AI Clinical Assessment&rdquo; to begin</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   REASONING CHAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */

const STEP_ICONS: Record<string, { icon: string; gradient: string }> = {
  "Patient Intake":          { icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z", gradient: "from-slate-400 to-slate-600" },
  "Triage Assessment":       { icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z", gradient: "from-amber-400 to-orange-500" },
  "Diagnostic Analysis":     { icon: "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z", gradient: "from-blue-400 to-indigo-500" },
  "Cardiology Review":       { icon: "M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z", gradient: "from-rose-400 to-red-500" },
  "Pathology Review":        { icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-3 5.5H8L5 14.5", gradient: "from-pink-400 to-fuchsia-500" },
  "Treatment Planning":      { icon: "M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75", gradient: "from-emerald-400 to-teal-500" },
  "Safety Validation":       { icon: "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z", gradient: "from-red-400 to-rose-500" },
  "Clinical Coding":         { icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5", gradient: "from-violet-400 to-purple-500" },
  "Validation & Aggregation":{ icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75", gradient: "from-cyan-400 to-blue-500" },
  "Quality Check":           { icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z", gradient: "from-emerald-400 to-green-500" },
  "Clinical Findings":       { icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z", gradient: "from-blue-400 to-indigo-500" },
  "Differential Diagnosis":  { icon: "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z", gradient: "from-indigo-400 to-blue-500" },
  "Safety Check":            { icon: "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z", gradient: "from-red-400 to-rose-500" },
  "Final Review":            { icon: "M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75", gradient: "from-gray-400 to-slate-500" },
  "Overview":                { icon: "M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25", gradient: "from-gray-400 to-gray-500" },
};

const AGENT_COLORS: Record<string, string> = {
  Diagnostician: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Treatment: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  Safety: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  Coding: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  Cardiology: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
  Pathology: "bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300",
  Supervisor: "bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-300",
  Triage: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
};

interface ReasoningSection {
  stepNum: string;
  title: string;
  lines: string[];
}

function parseReasoningSteps(steps: string[]): ReasoningSection[] {
  const sections: ReasoningSection[] = [];
  let current: ReasoningSection | null = null;

  for (const step of steps) {
    const headerMatch = step.match(/^=== Step (\d+): (.+?) ===$/);
    if (headerMatch) {
      if (current) sections.push(current);
      current = { stepNum: headerMatch[1], title: headerMatch[2], lines: [] };
    } else if (current) {
      current.lines.push(step);
    } else {
      // Line before any section header
      if (!sections.length) {
        current = { stepNum: "0", title: "Overview", lines: [step] };
      }
    }
  }
  if (current) sections.push(current);
  return sections;
}

function ReasoningLine({ line }: { line: string }) {
  // Skip empty lines
  if (!line.trim()) return null;

  // Agent step: [AgentName] Step N: Description
  const agentStepMatch = line.match(/^\[(\w+)\]\s+Step\s+\d+:\s+(.+)$/);
  if (agentStepMatch) {
    const agentName = agentStepMatch[1];
    const desc = agentStepMatch[2];
    const colorCls = AGENT_COLORS[agentName] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
    return (
      <div className="flex items-start gap-2.5 py-1.5">
        <span className={`mt-0.5 inline-flex shrink-0 items-center rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${colorCls}`}>
          {agentName}
        </span>
        <span className="text-[13px] text-gray-700 dark:text-gray-300">{desc}</span>
      </div>
    );
  }

  // Specialist recommendation: [AgentName] Description or [AgentName] - Description
  const specialistMatch = line.match(/^\[(\w+)\]\s+-?\s*(.+)$/);
  if (specialistMatch) {
    const agentName = specialistMatch[1];
    const desc = specialistMatch[2];
    const colorCls = AGENT_COLORS[agentName] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
    const isRecommendation = desc.toLowerCase().includes("adding") || desc.toLowerCase().includes("recommend") || desc.toLowerCase().includes("initiat") || desc.toLowerCase().includes("prescri") || desc.toLowerCase().includes("order");
    return (
      <div className={`flex items-start gap-2.5 py-1.5 ${isRecommendation ? "pl-2 border-l-2 border-emerald-400 dark:border-emerald-600" : ""}`}>
        <span className={`mt-0.5 inline-flex shrink-0 items-center rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${colorCls}`}>
          {agentName}
        </span>
        <span className={`text-[13px] ${isRecommendation ? "text-emerald-700 dark:text-emerald-400 font-medium" : "text-gray-700 dark:text-gray-300"}`}>{desc}</span>
      </div>
    );
  }

  // QC lines: QC PASS / QC FAIL / QC WARN / QC SKIP / QC Result
  const qcMatch = line.match(/^QC\s*(?:Result:\s*)?(PASS|FAIL|WARN|SKIP)[:\s—]+(.+)$/i);
  if (qcMatch) {
    const type = qcMatch[1].toUpperCase();
    const msg = qcMatch[2];
    const config: Record<string, { icon: string; bg: string; iconCls: string }> = {
      PASS: { icon: "M4.5 12.75l6 6 9-13.5", bg: "bg-emerald-50 dark:bg-emerald-950/30", iconCls: "text-emerald-500" },
      FAIL: { icon: "M6 18L18 6M6 6l12 12", bg: "bg-red-50 dark:bg-red-950/30", iconCls: "text-red-500" },
      WARN: { icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z", bg: "bg-amber-50 dark:bg-amber-950/30", iconCls: "text-amber-500" },
      SKIP: { icon: "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12", bg: "bg-gray-50 dark:bg-gray-800/50", iconCls: "text-gray-400" },
    };
    const c = config[type] || config.SKIP;
    return (
      <div className={`flex items-center gap-2.5 rounded-md px-3 py-2 ${c.bg}`}>
        <svg className={`h-4 w-4 shrink-0 ${c.iconCls}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d={c.icon} />
        </svg>
        <span className={`text-[10px] font-bold uppercase tracking-wide shrink-0 ${c.iconCls}`}>{type}</span>
        <span className="text-[13px] text-gray-700 dark:text-gray-300">{msg}</span>
      </div>
    );
  }

  // Human review REQUIRED line
  if (line.startsWith("Human review REQUIRED:") || line.startsWith("Human review:")) {
    const msg = line.replace(/^Human review\s*(?:REQUIRED)?:\s*/, "");
    return (
      <div className="flex items-start gap-2.5 rounded-lg border border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50 p-3 dark:border-amber-700 dark:from-amber-950/40 dark:to-orange-950/30">
        <svg className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wide text-amber-600 dark:text-amber-400">Physician Review Required</span>
          <p className="text-[13px] font-medium text-amber-800 dark:text-amber-300">{msg}</p>
        </div>
      </div>
    );
  }

  // Agents consulted line
  if (line.startsWith("Agents consulted:")) {
    const agentList = line.replace("Agents consulted: ", "").split(", ");
    return (
      <div className="flex flex-wrap items-center gap-2 py-1.5">
        <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400">Agents:</span>
        {agentList.map((a) => {
          const colorCls = AGENT_COLORS[a.charAt(0).toUpperCase() + a.slice(1)] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
          return (
            <span key={a} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide capitalize ${colorCls}`}>
              {a}
            </span>
          );
        })}
      </div>
    );
  }

  // Arrow-prefixed findings/recommendations (  → item or  ⚠ item)
  const arrowMatch = line.match(/^\s*[→⚠►•]\s+(.+)$/);
  if (arrowMatch) {
    const isWarning = line.includes("⚠");
    return (
      <div className={`flex items-start gap-2 py-1 pl-2 ml-2 border-l-2 ${isWarning ? "border-amber-400 dark:border-amber-600" : "border-blue-300 dark:border-blue-700"}`}>
        <span className={`mt-0.5 text-[11px] shrink-0 ${isWarning ? "text-amber-500" : "text-blue-500"}`}>{isWarning ? "⚠" : "→"}</span>
        <span className={`text-[13px] ${isWarning ? "text-amber-700 dark:text-amber-400" : "text-gray-700 dark:text-gray-300"}`}>{arrowMatch[1]}</span>
      </div>
    );
  }

  // Summary stat lines — important metrics displayed as cards
  const summaryKeywords = /^(Total findings|Primary diagnosis|Differential diagnoses|Treatment plan|Clinical codes|Overall diagnostic confidence|Quality check complete|No diagnoses|Total agents consulted|Confidence)/i;
  if (summaryKeywords.test(line)) {
    const colonIdx = line.indexOf(":");
    if (colonIdx > 0) {
      const label = line.slice(0, colonIdx).trim();
      const value = line.slice(colonIdx + 1).trim();
      const isHighlight = /diagnosis|treatment|confidence/i.test(label);
      const isWarning = /0%|No diagnoses|0 recommendation/i.test(value);
      return (
        <div className={`flex items-center justify-between rounded-md px-3 py-2 ${isHighlight ? "bg-blue-50 dark:bg-blue-950/30" : "bg-gray-50 dark:bg-gray-800/50"}`}>
          <span className={`text-[13px] font-medium ${isHighlight ? "text-blue-700 dark:text-blue-400" : "text-gray-600 dark:text-gray-400"}`}>{label}</span>
          <span className={`text-[13px] font-bold tabular-nums ${isWarning ? "text-amber-600 dark:text-amber-400" : "text-gray-900 dark:text-gray-100"}`}>
            {value}
          </span>
        </div>
      );
    }
  }

  // Urgency/status key-value (e.g. "Urgency level: high")
  const kvMatch = line.match(/^(.+?):\s+(.+)$/);
  if (kvMatch) {
    const label = kvMatch[1].trim();
    const value = kvMatch[2].trim();
    // Highlight certain values
    const urgencyColors: Record<string, string> = {
      high: "text-red-600 dark:text-red-400", urgent: "text-red-600 dark:text-red-400",
      immediate: "text-red-600 dark:text-red-400", critical: "text-red-600 dark:text-red-400",
      moderate: "text-amber-600 dark:text-amber-400", medium: "text-amber-600 dark:text-amber-400",
      low: "text-emerald-600 dark:text-emerald-400", routine: "text-emerald-600 dark:text-emerald-400",
      normal: "text-emerald-600 dark:text-emerald-400",
    };
    const valueLower = value.toLowerCase();
    const valueColor = urgencyColors[valueLower] || "text-gray-900 dark:text-gray-100";
    return (
      <div className="flex items-center justify-between py-1 px-1">
        <span className="text-[13px] text-gray-500 dark:text-gray-400">{label}</span>
        <span className={`text-[13px] font-semibold ${valueColor}`}>{value}</span>
      </div>
    );
  }

  // Default fallback — styled as subtle log line
  return <p className="py-0.5 pl-1 text-[13px] text-gray-500 dark:text-gray-400">{line}</p>;
}

function ReasoningChain({ steps }: { steps: string[] }) {
  const sections = parseReasoningSteps(steps);
  const [isOpen, setIsOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const toggleSection = (stepNum: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(stepNum)) next.delete(stepNum);
      else next.add(stepNum);
      return next;
    });
  };

  const expandAll = () => setExpandedSections(new Set(sections.map((s) => s.stepNum)));
  const collapseAll = () => setExpandedSections(new Set());

  // Extract summary metrics from reasoning lines
  const summaryMetrics: Array<{ label: string; value: string; highlight?: boolean }> = [];
  for (const step of steps) {
    const diagMatch = step.match(/Primary diagnosis:\s*(.+)/);
    if (diagMatch) summaryMetrics.push({ label: "Primary Dx", value: diagMatch[1], highlight: true });
    const txMatch = step.match(/Treatment plan:\s*(.+)/);
    if (txMatch) summaryMetrics.push({ label: "Treatment Plan", value: txMatch[1], highlight: true });
    const confMatch = step.match(/Overall diagnostic confidence:\s*(.+)/);
    if (confMatch) summaryMetrics.push({ label: "Confidence", value: confMatch[1] });
    const findMatch = step.match(/Total findings:\s*(.+)/);
    if (findMatch) summaryMetrics.push({ label: "Findings", value: findMatch[1] });
    const agentsMatch = step.match(/^Total agents consulted:\s*(.+)/);
    if (agentsMatch) summaryMetrics.push({ label: "Agents", value: agentsMatch[1] });
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900 overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-healthos-400 to-healthos-600 shadow-sm">
            <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div className="text-left">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">AI Reasoning Chain</h4>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              {sections.length} pipeline stages &middot; {steps.length} steps &middot; Click to {isOpen ? "collapse" : "expand"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex rounded-full bg-healthos-50 px-2.5 py-1 text-[10px] font-bold text-healthos-700 ring-1 ring-inset ring-healthos-500/20 dark:bg-healthos-950/50 dark:text-healthos-400 dark:ring-healthos-500/30">
            {steps.length} steps
          </span>
          <svg
            className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </div>
      </button>

      {/* Summary metrics bar — always visible when there are metrics */}
      {summaryMetrics.length > 0 && !isOpen && (
        <div className="border-t border-gray-100 dark:border-gray-800 px-5 py-3 flex flex-wrap gap-x-6 gap-y-1">
          {summaryMetrics.slice(0, 4).map((m, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="text-[11px] text-gray-400 dark:text-gray-500">{m.label}:</span>
              <span className={`text-[11px] font-semibold ${m.highlight ? "text-blue-700 dark:text-blue-400" : "text-gray-700 dark:text-gray-300"}`}>{m.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Expandable section */}
      {isOpen && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          {/* Controls */}
          <div className="px-5 py-2 flex items-center gap-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30">
            <button onClick={expandAll} className="text-[11px] font-medium text-healthos-600 dark:text-healthos-400 hover:underline">
              Expand All
            </button>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <button onClick={collapseAll} className="text-[11px] font-medium text-healthos-600 dark:text-healthos-400 hover:underline">
              Collapse All
            </button>
          </div>

          <div className="relative px-5 py-4 space-y-2">
            {/* Vertical timeline line */}
            <div className="absolute left-[35px] top-6 bottom-6 w-0.5 bg-gradient-to-b from-healthos-200 via-gray-200 to-gray-100 dark:from-healthos-800 dark:via-gray-700 dark:to-gray-800" />

            {sections.map((section) => {
              const stepConfig = STEP_ICONS[section.title] || { icon: "M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25", gradient: "from-gray-400 to-gray-500" };
              const isExpanded = expandedSections.has(section.stepNum);
              const nonEmptyLines = section.lines.filter(l => l.trim());

              return (
                <div key={section.stepNum} className="relative pl-10">
                  {/* Timeline dot */}
                  <div className={`absolute left-0 top-0.5 flex h-[28px] w-[28px] items-center justify-center rounded-full bg-gradient-to-br ${stepConfig.gradient} shadow-sm ring-4 ring-white dark:ring-gray-900`}>
                    <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d={stepConfig.icon} />
                    </svg>
                  </div>

                  {/* Section card */}
                  <div className={`rounded-lg border transition-all ${isExpanded ? "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm" : "border-transparent hover:border-gray-200 dark:hover:border-gray-700"}`}>
                    <button
                      onClick={() => toggleSection(section.stepNum)}
                      className="flex w-full items-center justify-between px-3 py-2 text-left"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold text-gray-400 dark:text-gray-500 tabular-nums w-4 text-right">
                          {String(section.stepNum).padStart(2, "0")}
                        </span>
                        <span className="text-[13px] font-semibold text-gray-900 dark:text-gray-100">
                          {section.title}
                        </span>
                        {nonEmptyLines.length > 0 && (
                          <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[9px] font-semibold text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                            {nonEmptyLines.length}
                          </span>
                        )}
                      </div>
                      <svg
                        className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                      </svg>
                    </button>

                    {isExpanded && nonEmptyLines.length > 0 && (
                      <div className="space-y-1 px-3 pb-3">
                        <div className="h-px bg-gray-100 dark:bg-gray-800" />
                        {nonEmptyLines.map((line, i) => (
                          <ReasoningLine key={i} line={line} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   AGENTS TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function AgentsTab({ agents }: { agents: AgentInfo[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {agents.map((agent) => (
        <div key={agent.agent_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{agent.name}</h4>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-500">v{agent.version}</p>
            </div>
            {agent.requires_human_approval && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                HITL
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{agent.description}</p>
          {agent.specialties.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {agent.specialties.map((s) => (
                <span key={s} className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-500">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   LLM TAB
   ═══════════════════════════════════════════════════════════════════════════ */

const LLM_PROVIDERS = [
  {
    id: "claude",
    name: "Anthropic Claude",
    description: "Best-in-class reasoning and clinical safety. Recommended for production clinical assessments.",
    icon: (
      <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none">
        <path d="M16.5 3.5C14 3.5 12 5.5 12 8V16C12 18.5 14 20.5 16.5 20.5C19 20.5 21 18.5 21 16V8C21 5.5 19 3.5 16.5 3.5Z" fill="#D97706" fillOpacity={0.15} stroke="#D97706" strokeWidth={1.5} />
        <path d="M7.5 3.5C5 3.5 3 5.5 3 8V16C3 18.5 5 20.5 7.5 20.5C10 20.5 12 18.5 12 16V8C12 5.5 10 3.5 7.5 3.5Z" fill="#D97706" fillOpacity={0.15} stroke="#D97706" strokeWidth={1.5} />
      </svg>
    ),
    models: ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-20250414"],
    configKey: "claude_model",
    color: "amber",
    badge: "Recommended",
    requiresKey: true,
    keyName: "ANTHROPIC_API_KEY",
  },
  {
    id: "openai",
    name: "OpenAI ChatGPT",
    description: "Versatile general-purpose model. Strong at structured output and medical knowledge extraction.",
    icon: (
      <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none">
        <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.998 5.998 0 0 0-3.998 2.9 6.05 6.05 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073z" fill="#10A37F" fillOpacity={0.15} stroke="#10A37F" strokeWidth={1} />
        <circle cx="12" cy="12" r="3" fill="#10A37F" />
      </svg>
    ),
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-preview"],
    configKey: "openai_model",
    color: "emerald",
    badge: "Popular",
    requiresKey: true,
    keyName: "OPENAI_API_KEY",
  },
  {
    id: "ollama",
    name: "Ollama — DeepSeek R1",
    description: "Local inference with DeepSeek-R1:7b. No data leaves your infrastructure — ideal for PHI-sensitive workflows.",
    icon: (
      <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="6" width="18" height="12" rx="3" fill="#7C3AED" fillOpacity={0.15} stroke="#7C3AED" strokeWidth={1.5} />
        <circle cx="8" cy="12" r="1.5" fill="#7C3AED" />
        <circle cx="12" cy="12" r="1.5" fill="#7C3AED" />
        <circle cx="16" cy="12" r="1.5" fill="#7C3AED" />
        <path d="M3 9h18" stroke="#7C3AED" strokeWidth={0.5} opacity={0.5} />
        <path d="M3 15h18" stroke="#7C3AED" strokeWidth={0.5} opacity={0.5} />
      </svg>
    ),
    models: ["deepseek-r1:7b", "deepseek-r1:14b", "llama3.2", "mistral", "codellama"],
    configKey: "ollama_model",
    color: "violet",
    badge: "Local / Private",
    requiresKey: false,
    keyName: "localhost:12434",
  },
];

function LLMTab({ status, onRefresh, onSwitch }: { status: LLMStatus | null; onRefresh: () => void; onSwitch: (provider: string) => void }) {
  const [switching, setSwitching] = useState<string | null>(null);
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>({});

  const activeProvider = status?.primary_provider || "claude";

  const handleSwitch = async (providerId: string) => {
    setSwitching(providerId);
    await onSwitch(providerId);
    setSwitching(null);
  };

  const colorMap: Record<string, { ring: string; bg: string; text: string; badge: string; dot: string }> = {
    amber: { ring: "ring-amber-500/30", bg: "bg-amber-50 dark:bg-amber-950/30", text: "text-amber-700 dark:text-amber-400", badge: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300", dot: "bg-amber-500" },
    emerald: { ring: "ring-emerald-500/30", bg: "bg-emerald-50 dark:bg-emerald-950/30", text: "text-emerald-700 dark:text-emerald-400", badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300", dot: "bg-emerald-500" },
    violet: { ring: "ring-violet-500/30", bg: "bg-violet-50 dark:bg-violet-950/30", text: "text-violet-700 dark:text-violet-400", badge: "bg-violet-100 text-violet-800 dark:bg-violet-900/50 dark:text-violet-300", dot: "bg-violet-500" },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">LLM Provider Configuration</h3>
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">Select your preferred LLM for clinical reasoning. Provider can be switched at any time.</p>
        </div>
        <button onClick={onRefresh} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" /></svg>
          Refresh
        </button>
      </div>

      {/* Status Summary */}
      {status && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-full bg-gray-100 dark:bg-gray-800 px-3 py-1.5">
            <span className={`inline-block h-2 w-2 rounded-full ${status.status === "available" || status.status === "demo" ? "bg-emerald-500" : "bg-red-500"}`} />
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 capitalize">{status.status === "demo" ? "Demo Mode" : status.status}</span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Temperature: <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{String(status.config?.temperature ?? 0.3)}</span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Max Tokens: <span className="font-mono font-medium text-gray-700 dark:text-gray-300">{String(status.config?.max_tokens ?? 2000)}</span>
          </div>
        </div>
      )}

      {/* Provider Cards */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {LLM_PROVIDERS.map((provider) => {
          const isActive = activeProvider === provider.id || activeProvider === (provider.id === "claude" ? "claude" : provider.id === "openai" ? "openai" : "ollama");
          const isActiveMatch = activeProvider.includes(provider.id) || (provider.id === "claude" && activeProvider.includes("claude"));
          const active = isActive || isActiveMatch;
          const colors = colorMap[provider.color] || colorMap.amber;
          const currentModel = String(status?.config?.[provider.configKey] || provider.models[0]);
          const selected = selectedModels[provider.id] || currentModel;
          const isAvailable = status?.available_providers?.includes(provider.id) ?? false;

          return (
            <div
              key={provider.id}
              className={`relative rounded-2xl border-2 p-5 transition-all duration-200 ${
                active
                  ? `border-transparent ring-2 ${colors.ring} ${colors.bg} shadow-md`
                  : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm"
              }`}
            >
              {/* Active indicator */}
              {active && (
                <div className="absolute -top-2.5 right-4">
                  <span className={`inline-flex items-center gap-1 rounded-full ${colors.badge} px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider`}>
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" /></svg>
                    Active
                  </span>
                </div>
              )}

              {/* Provider header */}
              <div className="flex items-start gap-3">
                <div className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl ${active ? colors.bg : "bg-gray-100 dark:bg-gray-800"}`}>
                  {provider.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">{provider.name}</h4>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${colors.badge}`}>{provider.badge}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{provider.description}</p>
                </div>
              </div>

              {/* Model selector */}
              <div className="mt-4">
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5">Model</label>
                <select
                  value={selected}
                  onChange={(e) => setSelectedModels((prev) => ({ ...prev, [provider.id]: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-200 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                >
                  {provider.models.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              {/* Connection info */}
              <div className="mt-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                {provider.requiresKey ? (
                  <>
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" /></svg>
                    <span>Requires <code className="rounded bg-gray-100 dark:bg-gray-700 px-1 py-0.5 font-mono text-[10px]">{provider.keyName}</code></span>
                  </>
                ) : (
                  <>
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" /></svg>
                    <span>Local — <code className="rounded bg-gray-100 dark:bg-gray-700 px-1 py-0.5 font-mono text-[10px]">{provider.keyName}</code></span>
                  </>
                )}
                {isAvailable && (
                  <span className="ml-auto flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">Connected</span>
                  </span>
                )}
              </div>

              {/* Action button */}
              <div className="mt-4">
                {active ? (
                  <div className={`flex items-center justify-center gap-2 rounded-lg ${colors.bg} px-4 py-2.5 text-sm font-semibold ${colors.text}`}>
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" /></svg>
                    Currently Active
                  </div>
                ) : (
                  <button
                    onClick={() => handleSwitch(provider.id)}
                    disabled={switching !== null}
                    className="w-full rounded-lg bg-gradient-to-r from-gray-800 to-gray-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:from-gray-700 hover:to-gray-800 hover:shadow-md disabled:opacity-50 dark:from-gray-600 dark:to-gray-700 dark:hover:from-gray-500 dark:hover:to-gray-600"
                  >
                    {switching === provider.id ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                        Switching...
                      </span>
                    ) : (
                      `Switch to ${provider.name.split(" ")[0]}`
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error */}
      {status?.error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          {status.error}
        </div>
      )}

      {/* Loading state */}
      {!status && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4 sm:p-8 text-center">
          <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-gray-300 dark:border-gray-600 border-t-healthos-600" />
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Loading LLM configuration...</p>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   MCP TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function MCPTab({ servers, onRefresh }: { servers: Record<string, MCPServerStatus>; onRefresh: () => void }) {
  const entries = Object.entries(servers);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">MCP Server Status</h3>
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 dark:text-gray-500 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      {entries.length > 0 ? (
        <>
          {entries.every(([, s]) => s.status === "unreachable") && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              All MCP servers are unreachable. Start the services with <code className="rounded bg-amber-100 px-1 py-0.5 dark:bg-amber-800">docker-compose up</code> or run them locally on the configured ports.
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {entries.map(([name, s]) => {
              const dotColor = s.status === "healthy" ? "bg-emerald-500" : s.status === "unreachable" ? "bg-amber-400" : "bg-red-500";
              const textColor = s.status === "healthy" ? "text-emerald-600" : s.status === "unreachable" ? "text-amber-600" : "text-red-600";
              return (
                <div key={name} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm dark:bg-gray-800">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 capitalize">{name.replace(/-/g, " ")}</h4>
                    <span className={`inline-flex h-2 w-2 rounded-full ${dotColor}`} />
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-500 font-mono">{s.url}</p>
                  <p className={`mt-1 text-xs font-medium ${textColor}`}>
                    {s.status}{s.error ? `: ${s.error}` : ""}
                  </p>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 p-4 sm:p-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">No MCP servers connected. Start the clinical orchestrator to see server status.</p>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIMULATOR TAB
   ═══════════════════════════════════════════════════════════════════════════ */

function SimulatorTab({ status, onRefresh }: { status: SimulatorStatus | null; onRefresh: () => void }) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const doAction = async (action: string) => {
    setActionLoading(action);
    try {
      await apiFetch(`/simulator/${action}`, { method: "POST" });
      await new Promise((r) => setTimeout(r, 500));
      onRefresh();
    } catch {
      /* ignore */
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">IoT Device Simulator</h3>
        <button onClick={onRefresh} className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 dark:text-gray-500 dark:hover:bg-gray-700">
          Refresh
        </button>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 shadow-sm dark:bg-gray-800">
        {status ? (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Status</p>
                <p className={`mt-1 text-sm font-semibold ${status.running ? "text-emerald-600" : "text-gray-500 dark:text-gray-400"}`}>
                  {status.running ? "Running" : "Stopped"}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Interval</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.interval ?? 30}s</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Devices</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.devices_count ?? 0}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Observations Sent</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.observations_sent ?? 0}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-500">Alerts Generated</p>
                <p className="mt-1 text-sm text-gray-900 dark:text-gray-100">{status.alerts_generated ?? 0}</p>
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={() => doAction(status.running ? "stop" : "start")}
                disabled={!!actionLoading}
                className={`rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all disabled:opacity-50 ${
                  status.running
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-emerald-600 hover:bg-emerald-700"
                }`}
              >
                {actionLoading === "start" || actionLoading === "stop" ? "..." : status.running ? "Stop" : "Start"}
              </button>
              <button
                onClick={() => doAction("trigger")}
                disabled={!!actionLoading}
                className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                {actionLoading === "trigger" ? "..." : "Trigger Once"}
              </button>
              <button
                onClick={() => doAction("reset-stats")}
                disabled={!!actionLoading}
                className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                Reset Stats
              </button>
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading simulator status...</p>
        )}

        {status?.error && (
          <p className="mt-4 text-sm text-red-600 dark:text-red-400">{status.error}</p>
        )}
      </div>
    </div>
  );
}
