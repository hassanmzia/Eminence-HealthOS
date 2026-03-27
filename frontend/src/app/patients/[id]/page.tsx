"use client";

import { useState, useEffect, useCallback, use } from "react";
import { fetchPatient, type PatientData } from "@/lib/api";
import {
  fetchDiagnoses,
  fetchPrescriptions,
  fetchAllergies,
  fetchMedicalHistory,
  fetchSocialHistory,
  fetchFamilyHistory,
  fetchLabTests,
  createDiagnosis,
  createPrescriptionRecord,
  createAllergy,
  createMedicalHistory,
  createSocialHistory,
  createFamilyHistory,
  fetchPatientQuestionnaires,
  reviewQuestionnaire,
  fetchPatientDevices,
  fetchDevices,
  assignDeviceToPatient,
  unassignDevice,
  type DiagnosisResponse,
  type PrescriptionResponse,
  type AllergyResponse,
  type MedicalHistoryResponse,
  type SocialHistoryResponse,
  type FamilyHistoryResponse,
  type LabTestResponse,
  type PatientQuestionnaireResponse,
  type DeviceInfoResponse,
  fetchDoctorTreatmentPlans,
  publishTreatmentPlan,
  type DoctorTreatmentPlanResponse,
} from "@/lib/platform-api";
import { PatientHeader } from "@/components/patients/PatientHeader";
import { VitalsTrendChart } from "@/components/patients/VitalsTrendChart";
import { RiskScoreGauge } from "@/components/patients/RiskScoreGauge";
import { PatientAlerts } from "@/components/patients/PatientAlerts";
import { AIAssessmentPanel } from "@/components/patients/AIAssessmentPanel";

/* ── Tiny inline icons ─────────────────────────────────────────────────────── */
const IconPlus = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
);
const IconX = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
);

/* ── Shared styles ─────────────────────────────────────────────────────────── */
const inputCls = "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500";
const selectCls = inputCls;
const labelCls = "block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1";
const btnPrimary = "inline-flex items-center gap-1.5 rounded-lg bg-healthos-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-healthos-500 transition disabled:opacity-50";
const btnSecondary = "inline-flex items-center gap-1 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition";

const STATUS_COLORS: Record<string, string> = {
  Active: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  Resolved: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  Chronic: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  Completed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  Discontinued: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${color}`}>{status}</span>;
}

function EmptyState({ message, onAdd }: { message: string; onAdd?: () => void }) {
  return (
    <div className="text-center py-8">
      <p className="text-sm text-gray-400 dark:text-gray-500">{message}</p>
      {onAdd && (
        <button onClick={onAdd} className={`${btnPrimary} mt-3`}><IconPlus /> Add Record</button>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Demographics
   ══════════════════════════════════════════════════════════════════════════════ */
function DemographicsTab({ patient }: { patient: PatientData }) {
  const d = patient.demographics as Record<string, unknown>;
  const fields = [
    { label: "Full Name", value: d?.name || d?.first_name ? `${d.first_name || ""} ${d.last_name || ""}`.trim() : "—" },
    { label: "Date of Birth", value: (d?.date_of_birth as string) || (d?.dob as string) || "—" },
    { label: "Gender", value: (d?.gender as string) || "—" },
    { label: "Sex", value: (d?.sex as string) || "—" },
    { label: "Race", value: (d?.race as string) || "—" },
    { label: "Ethnicity", value: (d?.ethnicity as string) || "—" },
    { label: "Preferred Language", value: (d?.preferred_language as string) || "—" },
    { label: "Blood Type", value: (d?.blood_type as string) || "—" },
    { label: "MRN", value: patient.mrn || "—" },
    { label: "Phone", value: (d?.phone as string) || "—" },
    { label: "Email", value: (d?.email as string) || "—" },
    { label: "Address", value: [d?.address_line1, d?.address_line2, d?.city, d?.state, d?.postal_code].filter(Boolean).join(", ") || "—" },
    { label: "Emergency Contact", value: (d?.emergency_contact_name as string) || "—" },
    { label: "Emergency Phone", value: (d?.emergency_contact_phone as string) || "—" },
    { label: "Insurance Provider", value: (d?.insurance_provider as string) || "—" },
    { label: "Insurance Member ID", value: (d?.insurance_member_id as string) || "—" },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {fields.map((f) => (
        <div key={f.label}>
          <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">{f.label}</p>
          <p className="text-sm text-gray-800 dark:text-gray-200 mt-0.5">{String(f.value)}</p>
        </div>
      ))}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Diagnoses
   ══════════════════════════════════════════════════════════════════════════════ */
function DiagnosesTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<DiagnosisResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ diagnosis_description: "", icd10_code: "", diagnosis_type: "Primary", status: "Active", notes: "" });

  const load = useCallback(async () => { try { setData(await fetchDiagnoses(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.diagnosis_description) return;
    setSaving(true);
    try { await createDiagnosis({ patient_id: patientId, ...form }); setShowAdd(false); setForm({ diagnosis_description: "", icd10_code: "", diagnosis_type: "Primary", status: "Active", notes: "" }); load(); } catch {}
    setSaving(false);
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowAdd(!showAdd)} className={showAdd ? btnSecondary : btnPrimary}>{showAdd ? <><IconX /> Cancel</> : <><IconPlus /> Add Diagnosis</>}</button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card !p-4 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div><label className={labelCls}>Description *</label><input className={inputCls} value={form.diagnosis_description} onChange={(e) => setForm({ ...form, diagnosis_description: e.target.value })} placeholder="e.g. Type 2 Diabetes Mellitus" /></div>
            <div><label className={labelCls}>ICD-10 Code</label><input className={inputCls} value={form.icd10_code} onChange={(e) => setForm({ ...form, icd10_code: e.target.value })} placeholder="e.g. E11.9" /></div>
            <div><label className={labelCls}>Type</label><select className={selectCls} value={form.diagnosis_type} onChange={(e) => setForm({ ...form, diagnosis_type: e.target.value })}><option>Primary</option><option>Secondary</option><option>Admitting</option><option>Discharge</option></select></div>
            <div><label className={labelCls}>Status</label><select className={selectCls} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option>Active</option><option>Resolved</option><option>Chronic</option></select></div>
          </div>
          <div><label className={labelCls}>Notes</label><textarea className={inputCls} rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
          <div className="flex justify-end"><button type="submit" disabled={saving} className={btnPrimary}>{saving ? "Saving..." : "Save Diagnosis"}</button></div>
        </form>
      )}

      {data.length === 0 ? <EmptyState message="No diagnoses recorded" onAdd={() => setShowAdd(true)} /> : (
        <div className="space-y-2">
          {data.map((d) => (
            <div key={d.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{d.diagnosis_description}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{[d.icd10_code, d.diagnosis_type, d.notes].filter(Boolean).join(" · ")}</p>
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Medications / Prescriptions
   ══════════════════════════════════════════════════════════════════════════════ */
function MedicationsTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<PrescriptionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ medication_name: "", dosage: "", frequency: "", route: "", start_date: "", instructions: "" });

  const load = useCallback(async () => { try { setData(await fetchPrescriptions(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.medication_name || !form.dosage || !form.frequency || !form.start_date) return;
    setSaving(true);
    try { await createPrescriptionRecord({ patient_id: patientId, ...form }); setShowAdd(false); setForm({ medication_name: "", dosage: "", frequency: "", route: "", start_date: "", instructions: "" }); load(); } catch {}
    setSaving(false);
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowAdd(!showAdd)} className={showAdd ? btnSecondary : btnPrimary}>{showAdd ? <><IconX /> Cancel</> : <><IconPlus /> Add Medication</>}</button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card !p-4 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Medication Name *</label><input className={inputCls} value={form.medication_name} onChange={(e) => setForm({ ...form, medication_name: e.target.value })} placeholder="e.g. Metformin" /></div>
            <div><label className={labelCls}>Dosage *</label><input className={inputCls} value={form.dosage} onChange={(e) => setForm({ ...form, dosage: e.target.value })} placeholder="e.g. 500mg" /></div>
            <div><label className={labelCls}>Frequency *</label><input className={inputCls} value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })} placeholder="e.g. Twice daily" /></div>
            <div><label className={labelCls}>Route</label><select className={selectCls} value={form.route} onChange={(e) => setForm({ ...form, route: e.target.value })}><option value="">Select...</option><option>Oral</option><option>IV</option><option>IM</option><option>Subcutaneous</option><option>Topical</option><option>Inhaled</option></select></div>
            <div><label className={labelCls}>Start Date *</label><input type="date" className={inputCls} value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
          </div>
          <div><label className={labelCls}>Instructions</label><textarea className={inputCls} rows={2} value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} placeholder="Take with food" /></div>
          <div className="flex justify-end"><button type="submit" disabled={saving} className={btnPrimary}>{saving ? "Saving..." : "Save Medication"}</button></div>
        </form>
      )}

      {data.length === 0 ? <EmptyState message="No medications prescribed" onAdd={() => setShowAdd(true)} /> : (
        <div className="space-y-2">
          {data.map((rx) => (
            <div key={rx.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{rx.medication_name} <span className="text-gray-500 font-normal">{rx.dosage}</span></p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{[rx.frequency, rx.route, rx.instructions].filter(Boolean).join(" · ")}</p>
              </div>
              <StatusBadge status={rx.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Allergies
   ══════════════════════════════════════════════════════════════════════════════ */
function AllergiesTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<AllergyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ allergen: "", allergy_type: "Medication", severity: "Moderate", reaction: "" });

  const load = useCallback(async () => { try { setData(await fetchAllergies(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.allergen) return;
    setSaving(true);
    try { await createAllergy({ patient_id: patientId, ...form }); setShowAdd(false); setForm({ allergen: "", allergy_type: "Medication", severity: "Moderate", reaction: "" }); load(); } catch {}
    setSaving(false);
  };

  const SEVERITY_COLORS: Record<string, string> = {
    Mild: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    Moderate: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    Severe: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    "Life-threatening": "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowAdd(!showAdd)} className={showAdd ? btnSecondary : btnPrimary}>{showAdd ? <><IconX /> Cancel</> : <><IconPlus /> Add Allergy</>}</button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card !p-4 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div><label className={labelCls}>Allergen *</label><input className={inputCls} value={form.allergen} onChange={(e) => setForm({ ...form, allergen: e.target.value })} placeholder="e.g. Penicillin" /></div>
            <div><label className={labelCls}>Type</label><select className={selectCls} value={form.allergy_type} onChange={(e) => setForm({ ...form, allergy_type: e.target.value })}><option>Medication</option><option>Food</option><option>Environmental</option><option>Other</option></select></div>
            <div><label className={labelCls}>Severity</label><select className={selectCls} value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}><option>Mild</option><option>Moderate</option><option>Severe</option><option>Life-threatening</option></select></div>
            <div><label className={labelCls}>Reaction</label><input className={inputCls} value={form.reaction} onChange={(e) => setForm({ ...form, reaction: e.target.value })} placeholder="e.g. Hives, anaphylaxis" /></div>
          </div>
          <div className="flex justify-end"><button type="submit" disabled={saving} className={btnPrimary}>{saving ? "Saving..." : "Save Allergy"}</button></div>
        </form>
      )}

      {data.length === 0 ? <EmptyState message="No allergies recorded" onAdd={() => setShowAdd(true)} /> : (
        <div className="space-y-2">
          {data.map((a) => (
            <div key={a.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{a.allergen} <span className="text-xs text-gray-400">({a.allergy_type})</span></p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{a.reaction || "No reaction noted"}</p>
              </div>
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${SEVERITY_COLORS[a.severity] || "bg-gray-100 text-gray-600"}`}>{a.severity}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Medical History
   ══════════════════════════════════════════════════════════════════════════════ */
function MedicalHistoryTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<MedicalHistoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ condition: "", diagnosis_date: "", status: "Active", treatment_notes: "" });

  const load = useCallback(async () => { try { setData(await fetchMedicalHistory(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.condition) return;
    setSaving(true);
    try { await createMedicalHistory({ patient_id: patientId, ...form }); setShowAdd(false); setForm({ condition: "", diagnosis_date: "", status: "Active", treatment_notes: "" }); load(); } catch {}
    setSaving(false);
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowAdd(!showAdd)} className={showAdd ? btnSecondary : btnPrimary}>{showAdd ? <><IconX /> Cancel</> : <><IconPlus /> Add Record</>}</button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card !p-4 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div><label className={labelCls}>Condition *</label><input className={inputCls} value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} placeholder="e.g. Hypertension" /></div>
            <div><label className={labelCls}>Diagnosis Date</label><input type="date" className={inputCls} value={form.diagnosis_date} onChange={(e) => setForm({ ...form, diagnosis_date: e.target.value })} /></div>
            <div><label className={labelCls}>Status</label><select className={selectCls} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option>Active</option><option>Resolved</option><option>Chronic</option></select></div>
          </div>
          <div><label className={labelCls}>Treatment Notes</label><textarea className={inputCls} rows={2} value={form.treatment_notes} onChange={(e) => setForm({ ...form, treatment_notes: e.target.value })} /></div>
          <div className="flex justify-end"><button type="submit" disabled={saving} className={btnPrimary}>{saving ? "Saving..." : "Save Record"}</button></div>
        </form>
      )}

      {data.length === 0 ? <EmptyState message="No medical history recorded" onAdd={() => setShowAdd(true)} /> : (
        <div className="space-y-2">
          {data.map((h) => (
            <div key={h.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{h.condition}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{[h.diagnosis_date && `Diagnosed: ${h.diagnosis_date}`, h.treatment_notes].filter(Boolean).join(" · ") || "—"}</p>
              </div>
              <StatusBadge status={h.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Family History
   ══════════════════════════════════════════════════════════════════════════════ */
function FamilyHistoryTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<FamilyHistoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ relationship: "Father", condition: "", age_at_diagnosis: "", is_alive: true, cause_of_death: "", notes: "" });

  const load = useCallback(async () => { try { setData(await fetchFamilyHistory(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.condition) return;
    setSaving(true);
    try {
      await createFamilyHistory({
        patient_id: patientId,
        relationship: form.relationship,
        condition: form.condition,
        age_at_diagnosis: form.age_at_diagnosis ? Number(form.age_at_diagnosis) : undefined,
        is_alive: form.is_alive,
        cause_of_death: form.cause_of_death || undefined,
        notes: form.notes || undefined,
      });
      setShowAdd(false);
      setForm({ relationship: "Father", condition: "", age_at_diagnosis: "", is_alive: true, cause_of_death: "", notes: "" });
      load();
    } catch {}
    setSaving(false);
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowAdd(!showAdd)} className={showAdd ? btnSecondary : btnPrimary}>{showAdd ? <><IconX /> Cancel</> : <><IconPlus /> Add Family Record</>}</button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card !p-4 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Relationship *</label><select className={selectCls} value={form.relationship} onChange={(e) => setForm({ ...form, relationship: e.target.value })}><option>Father</option><option>Mother</option><option>Brother</option><option>Sister</option><option>Paternal Grandfather</option><option>Paternal Grandmother</option><option>Maternal Grandfather</option><option>Maternal Grandmother</option><option>Son</option><option>Daughter</option><option>Uncle</option><option>Aunt</option></select></div>
            <div><label className={labelCls}>Condition *</label><input className={inputCls} value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} placeholder="e.g. Heart Disease, Diabetes" /></div>
            <div><label className={labelCls}>Age at Diagnosis</label><input type="number" className={inputCls} value={form.age_at_diagnosis} onChange={(e) => setForm({ ...form, age_at_diagnosis: e.target.value })} placeholder="e.g. 55" /></div>
            <div className="flex items-center gap-2 pt-5">
              <input type="checkbox" checked={form.is_alive} onChange={(e) => setForm({ ...form, is_alive: e.target.checked })} className="rounded border-gray-300 dark:border-gray-600 text-healthos-600" />
              <label className="text-sm text-gray-700 dark:text-gray-300">Still alive</label>
            </div>
            {!form.is_alive && (
              <div><label className={labelCls}>Cause of Death</label><input className={inputCls} value={form.cause_of_death} onChange={(e) => setForm({ ...form, cause_of_death: e.target.value })} /></div>
            )}
          </div>
          <div><label className={labelCls}>Notes</label><textarea className={inputCls} rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
          <div className="flex justify-end"><button type="submit" disabled={saving} className={btnPrimary}>{saving ? "Saving..." : "Save Record"}</button></div>
        </form>
      )}

      {data.length === 0 ? <EmptyState message="No family history recorded" onAdd={() => setShowAdd(true)} /> : (
        <div className="space-y-2">
          {data.map((f) => (
            <div key={f.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{f.relationship}: <span className="font-normal">{f.condition}</span></p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {[f.age_at_diagnosis != null && `Diagnosed at age ${f.age_at_diagnosis}`, f.is_alive ? "Alive" : `Deceased${f.cause_of_death ? ` — ${f.cause_of_death}` : ""}`].filter(Boolean).join(" · ")}
                </p>
              </div>
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${f.is_alive ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"}`}>
                {f.is_alive ? "Alive" : "Deceased"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Social History
   ══════════════════════════════════════════════════════════════════════════════ */
function SocialHistoryTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<SocialHistoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    smoking_status: "Never", alcohol_use: "Never", drug_use: "", occupation: "", marital_status: "Single",
    living_situation: "", exercise: "", diet: "", notes: "",
  });

  const load = useCallback(async () => { try { setData(await fetchSocialHistory(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try { await createSocialHistory({ patient_id: patientId, ...form }); setShowAdd(false); load(); } catch {}
    setSaving(false);
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowAdd(!showAdd)} className={showAdd ? btnSecondary : btnPrimary}>{showAdd ? <><IconX /> Cancel</> : <><IconPlus /> Add Social History</>}</button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="card !p-4 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div><label className={labelCls}>Smoking Status</label><select className={selectCls} value={form.smoking_status} onChange={(e) => setForm({ ...form, smoking_status: e.target.value })}><option>Never</option><option>Former</option><option>Current</option></select></div>
            <div><label className={labelCls}>Alcohol Use</label><select className={selectCls} value={form.alcohol_use} onChange={(e) => setForm({ ...form, alcohol_use: e.target.value })}><option>Never</option><option>Occasional</option><option>Regular</option><option>Heavy</option></select></div>
            <div><label className={labelCls}>Drug Use</label><input className={inputCls} value={form.drug_use} onChange={(e) => setForm({ ...form, drug_use: e.target.value })} placeholder="None" /></div>
            <div><label className={labelCls}>Occupation</label><input className={inputCls} value={form.occupation} onChange={(e) => setForm({ ...form, occupation: e.target.value })} /></div>
            <div><label className={labelCls}>Marital Status</label><select className={selectCls} value={form.marital_status} onChange={(e) => setForm({ ...form, marital_status: e.target.value })}><option>Single</option><option>Married</option><option>Divorced</option><option>Widowed</option><option>Separated</option></select></div>
            <div><label className={labelCls}>Living Situation</label><input className={inputCls} value={form.living_situation} onChange={(e) => setForm({ ...form, living_situation: e.target.value })} placeholder="e.g. Lives alone, with family" /></div>
            <div><label className={labelCls}>Exercise</label><input className={inputCls} value={form.exercise} onChange={(e) => setForm({ ...form, exercise: e.target.value })} placeholder="e.g. 3x/week, sedentary" /></div>
            <div><label className={labelCls}>Diet</label><input className={inputCls} value={form.diet} onChange={(e) => setForm({ ...form, diet: e.target.value })} placeholder="e.g. Balanced, low-sodium" /></div>
          </div>
          <div><label className={labelCls}>Notes</label><textarea className={inputCls} rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
          <div className="flex justify-end"><button type="submit" disabled={saving} className={btnPrimary}>{saving ? "Saving..." : "Save Social History"}</button></div>
        </form>
      )}

      {data.length === 0 ? <EmptyState message="No social history recorded" onAdd={() => setShowAdd(true)} /> : (
        <div className="space-y-2">
          {data.map((s) => (
            <div key={s.id} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {[
                  { label: "Smoking", value: s.smoking_status },
                  { label: "Alcohol", value: s.alcohol_use },
                  { label: "Occupation", value: s.occupation || "—" },
                  { label: "Marital Status", value: s.marital_status || "—" },
                ].map((f) => (
                  <div key={f.label}>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">{f.label}</p>
                    <p className="text-sm text-gray-800 dark:text-gray-200">{f.value}</p>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-gray-400 mt-2">Recorded {new Date(s.created_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Lab Results
   ══════════════════════════════════════════════════════════════════════════════ */
function LabResultsTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<LabTestResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => { try { setData(await fetchLabTests(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <div>
      {data.length === 0 ? <EmptyState message="No lab results available" /> : (
        <div className="space-y-2">
          {data.map((lab) => (
            <div key={lab.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <div>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{lab.test_name} {lab.test_code && <span className="text-xs text-gray-400">({lab.test_code})</span>}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {lab.result_value ? `${lab.result_value} ${lab.result_unit || ""}` : "Pending"}{lab.reference_range && ` · Ref: ${lab.reference_range}`}
                  {lab.interpretation && ` · ${lab.interpretation}`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {lab.abnormal_flag && <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">Abnormal</span>}
                <StatusBadge status={lab.status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: AI Recommendations
   ══════════════════════════════════════════════════════════════════════════════ */
const Q_TYPE_LABELS: Record<string, string> = {
  review_of_systems: "Review of Systems",
  history_presenting_illness: "History of Presenting Illness",
  pre_visit: "Pre-Visit Questionnaire",
};

function AIRecommendationsTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<PatientQuestionnaireResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => { try { setData(await fetchPatientQuestionnaires(patientId)); } catch {} setLoading(false); }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const handleReview = async (qId: string) => {
    setSaving(true);
    try { await reviewQuestionnaire(qId, reviewNotes); setReviewingId(null); setReviewNotes(""); load(); } catch {}
    setSaving(false);
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  if (data.length === 0) return <EmptyState message="No questionnaires submitted by patient" />;

  return (
    <div className="space-y-4">
      {data.map((q) => (
        <div key={q.id} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
            <div>
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                {Q_TYPE_LABELS[q.questionnaire_type] || q.questionnaire_type}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {q.submitted_at ? `Submitted ${new Date(q.submitted_at).toLocaleDateString()} at ${new Date(q.submitted_at).toLocaleTimeString()}` : q.created_at ? `Created ${new Date(q.created_at).toLocaleDateString()}` : ""}
              </p>
            </div>
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
              q.status === "reviewed" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
              q.status === "submitted" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
              "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
            }`}>{q.status}</span>
          </div>

          <div className="p-4 space-y-4">
            {/* AI Insights */}
            {q.ai_insights && Object.keys(q.ai_insights).length > 0 && (
              <div className="rounded-lg border border-healthos-200 dark:border-healthos-800 bg-healthos-50/50 dark:bg-healthos-900/20 p-3 space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-healthos-700 dark:text-healthos-400 flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                  AI-Extracted Insights
                </p>

                {q.ai_insights.chief_complaint && (
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Chief Complaint</p>
                    <p className="text-sm text-gray-800 dark:text-gray-200 mt-0.5">{q.ai_insights.chief_complaint}</p>
                  </div>
                )}

                {q.ai_insights.history_present_illness && (
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">History of Present Illness</p>
                    <p className="text-sm text-gray-800 dark:text-gray-200 mt-0.5 whitespace-pre-line">{q.ai_insights.history_present_illness}</p>
                  </div>
                )}

                {q.ai_insights.review_of_systems && Object.keys(q.ai_insights.review_of_systems).length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">Review of Systems (Positives)</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {Object.entries(q.ai_insights.review_of_systems).map(([system, symptoms]) => (
                        <div key={system} className="text-xs">
                          <span className="font-medium text-gray-700 dark:text-gray-300 capitalize">{system}:</span>{" "}
                          <span className="text-red-600 dark:text-red-400">{(symptoms as string[]).join(", ")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {q.ai_insights.patient_reported_symptoms && (q.ai_insights.patient_reported_symptoms as string[]).length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">Patient-Reported Symptoms</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(q.ai_insights.patient_reported_symptoms as string[]).map((s, i) => (
                        <span key={i} className="inline-flex items-center rounded-full px-2 py-0.5 text-xs bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">{s}</span>
                      ))}
                    </div>
                  </div>
                )}

                {q.ai_insights.social_history && Object.keys(q.ai_insights.social_history).length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">Social History</p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(q.ai_insights.social_history).map(([key, val]) => (
                        <div key={key} className="text-xs">
                          <span className="font-medium text-gray-700 dark:text-gray-300 capitalize">{key.replace(/_/g, " ")}:</span>{" "}
                          <span className="text-gray-600 dark:text-gray-400">{val as string}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Reviewer notes */}
            {q.reviewer_notes && (
              <div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 p-3">
                <p className="text-[11px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Reviewer Notes</p>
                <p className="text-sm text-gray-700 dark:text-gray-300 mt-0.5">{q.reviewer_notes}</p>
                {q.reviewed_at && <p className="text-[10px] text-gray-400 mt-1">Reviewed {new Date(q.reviewed_at).toLocaleDateString()}</p>}
              </div>
            )}

            {/* Mark as reviewed */}
            {q.status === "submitted" && (
              <div>
                {reviewingId === q.id ? (
                  <div className="space-y-2">
                    <textarea className={inputCls} rows={2} placeholder="Add clinical review notes..." value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} />
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => { setReviewingId(null); setReviewNotes(""); }} className={btnSecondary}>Cancel</button>
                      <button onClick={() => handleReview(q.id)} disabled={saving} className={btnPrimary}>{saving ? "Saving..." : "Mark Reviewed"}</button>
                    </div>
                  </div>
                ) : (
                  <button onClick={() => setReviewingId(q.id)} className={btnPrimary}>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                    Review Questionnaire
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: Devices
   ══════════════════════════════════════════════════════════════════════════════ */
function DevicesTab({ patientId }: { patientId: string }) {
  const [devices, setDevices] = useState<DeviceInfoResponse[]>([]);
  const [allDevices, setAllDevices] = useState<DeviceInfoResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAssign, setShowAssign] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [patientDevs, all] = await Promise.all([fetchPatientDevices(patientId), fetchDevices()]);
      setDevices(patientDevs);
      setAllDevices(all);
    } catch {}
    setLoading(false);
  }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const patientDeviceIds = new Set(devices.map((d) => d.id));
  const availableDevices = allDevices.filter((d) => !patientDeviceIds.has(d.id) && d.status === "Active");

  const handleAssign = async () => {
    if (!selectedDeviceId) return;
    setSaving(true);
    try { await assignDeviceToPatient({ patient_id: patientId, device_id: selectedDeviceId }); setShowAssign(false); setSelectedDeviceId(""); load(); } catch {}
    setSaving(false);
  };

  const handleUnassign = async (deviceId: string) => {
    if (!confirm("Unassign this device from the patient?")) return;
    try { await unassignDevice(deviceId); load(); } catch {}
  };

  if (loading) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  const DEVICE_TYPE_ICONS: Record<string, string> = { Watch: "W", Ring: "R", EarClip: "E", Adapter: "A", PulseGlucometer: "G" };
  const STATUS_CLR: Record<string, string> = {
    Active: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    Inactive: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
    Maintenance: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  };

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => setShowAssign(!showAssign)} className={showAssign ? btnSecondary : btnPrimary}>
          {showAssign ? <><IconX /> Cancel</> : <><IconPlus /> Assign Device</>}
        </button>
      </div>

      {showAssign && (
        <div className="card !p-4 mb-4 space-y-3">
          <label className={labelCls}>Select Device to Assign</label>
          {availableDevices.length === 0 ? (
            <p className="text-sm text-gray-500">No available devices. Register a device first.</p>
          ) : (
            <>
              <select className={selectCls} value={selectedDeviceId} onChange={(e) => setSelectedDeviceId(e.target.value)}>
                <option value="">Select a device...</option>
                {availableDevices.map((d) => (
                  <option key={d.id} value={d.id}>{d.device_name} — {d.device_type} ({d.device_unique_id})</option>
                ))}
              </select>
              <div className="flex justify-end">
                <button onClick={handleAssign} disabled={saving || !selectedDeviceId} className={btnPrimary}>
                  {saving ? "Assigning..." : "Assign to Patient"}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {devices.length === 0 ? <EmptyState message="No devices assigned to this patient" onAdd={() => setShowAssign(true)} /> : (
        <div className="space-y-2">
          {devices.map((d) => (
            <div key={d.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-healthos-100 dark:bg-healthos-900/30 text-sm font-bold text-healthos-700 dark:text-healthos-400">
                  {DEVICE_TYPE_ICONS[d.device_type] || d.device_type[0]}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{d.device_name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {d.device_type} · {d.device_unique_id}
                    {d.manufacturer && ` · ${d.manufacturer}`}
                    {d.model_number && ` ${d.model_number}`}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                    {d.battery_level != null && `Battery: ${d.battery_level}% · `}
                    {d.last_sync ? `Last sync: ${new Date(d.last_sync).toLocaleString()}` : "Never synced"}
                    {d.firmware_version && ` · FW: ${d.firmware_version}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_CLR[d.status] || STATUS_CLR.Inactive}`}>{d.status}</span>
                <button onClick={() => handleUnassign(d.id)} className="text-xs text-red-500 hover:text-red-700 dark:hover:text-red-400 transition" title="Unassign device">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TAB: AI Assessment (HITL Clinical Decision Support)
   ══════════════════════════════════════════════════════════════════════════════ */
function AIAssessmentTab({ patientId, patient }: { patientId: string; patient: PatientData }) {
  const [allergies, setAllergies] = useState<AllergyResponse[]>([]);
  const [meds, setMeds] = useState<PrescriptionResponse[]>([]);
  const [dx, setDx] = useState<DiagnosisResponse[]>([]);
  const [mh, setMh] = useState<MedicalHistoryResponse[]>([]);
  const [fh, setFh] = useState<FamilyHistoryResponse[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      fetchAllergies(patientId).then(r => setAllergies(r.results)).catch(() => {}),
      fetchPrescriptions(patientId).then(r => setMeds(r.results)).catch(() => {}),
      fetchDiagnoses(patientId).then(r => setDx(r.results)).catch(() => {}),
      fetchMedicalHistory(patientId).then(r => setMh(r.results)).catch(() => {}),
      fetchFamilyHistory(patientId).then(r => setFh(r.results)).catch(() => {}),
    ]).then(() => setLoaded(true));
  }, [patientId]);

  if (!loaded) return <div className="flex justify-center py-8"><div className="h-6 w-6 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>;

  return (
    <AIAssessmentPanel
      patient={patient}
      fhirId={(patient.demographics as Record<string, unknown>)?.fhir_id as string | undefined}
      allergies={allergies}
      medications={meds}
      diagnoses={dx}
      medicalHistory={mh}
      familyHistory={fh}
    />
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   TREATMENT PLANS TAB (Doctor View)
   ══════════════════════════════════════════════════════════════════════════════ */

function TreatmentPlansTab({ patientId }: { patientId: string }) {
  const [plans, setPlans] = useState<DoctorTreatmentPlanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [publishing, setPublishing] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "active" | "draft" | "completed">("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDoctorTreatmentPlans(patientId);
      if (data && data.length > 0) {
        setPlans(data);
        setLoading(false);
        return;
      }
    } catch { /* API not available, try localStorage */ }

    // Fallback: read from localStorage (plans created by clinical-assessment workflow)
    try {
      const stored = JSON.parse(localStorage.getItem("healthos_treatment_plans") || "[]") as DoctorTreatmentPlanResponse[];
      const forPatient = stored.filter(p => p.patient_id === patientId);
      if (forPatient.length > 0) {
        setPlans(forPatient);
      }
    } catch { /* localStorage not available */ }
    setLoading(false);
  }, [patientId]);

  useEffect(() => { load(); }, [load]);

  const handlePublish = async (planId: string) => {
    setPublishing(planId);
    try {
      await publishTreatmentPlan(planId);
      load();
    } catch { /* silent */ }
    setPublishing(null);
  };

  const filtered = filter === "all" ? plans : plans.filter(p => p.status === filter);

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-healthos-200 border-t-healthos-600" /></div>;
  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Treatment Plans</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">{plans.length} plan(s) for this patient</p>
        </div>
        <div className="flex gap-1">
          {(["all", "active", "draft", "completed"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                filter === f ? "bg-healthos-600 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200"
              }`}>{f.charAt(0).toUpperCase() + f.slice(1)}</button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-8 text-center">
          <svg className="mx-auto h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75" />
          </svg>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">No {filter === "all" ? "" : filter + " "}treatment plans found</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Treatment plans are created when a physician approves an AI clinical assessment</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map(tp => (
            <div key={tp.id} className="card !p-0 overflow-hidden">
              {/* Plan Header */}
              <div className="flex items-center justify-between px-5 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
                <div className="flex items-center gap-3">
                  <div className={`h-2.5 w-2.5 rounded-full ${
                    tp.status === "active" ? "bg-emerald-500" : tp.status === "draft" ? "bg-amber-400" : tp.status === "completed" ? "bg-blue-500" : "bg-gray-400"
                  }`} />
                  <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">{tp.plan_title}</h3>
                  <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full ${
                    tp.status === "active" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                    : tp.status === "draft" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                    : tp.status === "completed" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    : "bg-gray-100 text-gray-600"
                  }`}>{tp.status}</span>
                  {tp.is_visible_to_patient && (
                    <span className="text-[9px] font-medium text-healthos-600 bg-healthos-50 dark:bg-healthos-900/20 px-2 py-0.5 rounded-full">Patient Visible</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {tp.status === "draft" && (
                    <button onClick={() => handlePublish(tp.id)} disabled={publishing === tp.id}
                      className="px-3 py-1 text-xs font-medium bg-healthos-600 text-white rounded-lg hover:bg-healthos-700 disabled:opacity-50 transition-all">
                      {publishing === tp.id ? "Publishing..." : "Publish to Patient"}
                    </button>
                  )}
                  <p className="text-[10px] text-gray-400">{new Date(tp.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              {/* Plan Body */}
              <div className="p-5 space-y-4">
                {tp.treatment_goals && (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Treatment Goals</p>
                    <p className="text-sm text-gray-700 dark:text-gray-300">{tp.treatment_goals}</p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Medications */}
                  {tp.medications && tp.medications.length > 0 && (
                    <div className="rounded-lg border border-violet-100 dark:border-violet-900 p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-violet-600 mb-2">
                        Medications ({tp.medications.length})
                      </p>
                      <div className="space-y-1.5">
                        {tp.medications.map((med, i) => {
                          const m = med as Record<string, string>;
                          return (
                            <div key={i} className="flex items-center gap-2 text-[12px] bg-violet-50 dark:bg-violet-950/20 rounded-md px-2.5 py-1.5">
                              <svg className="h-3.5 w-3.5 text-violet-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5" />
                              </svg>
                              <span className="font-medium text-gray-800 dark:text-gray-200">{m.name || m.description || `Medication ${i + 1}`}</span>
                              {m.dosage && <span className="text-gray-500 text-[10px]">{m.dosage}</span>}
                              {m.frequency && <span className="text-gray-400 text-[10px]">&middot; {m.frequency}</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Procedures */}
                  {tp.procedures && tp.procedures.length > 0 && (
                    <div className="rounded-lg border border-cyan-100 dark:border-cyan-900 p-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-cyan-600 mb-2">
                        Procedures & Orders ({tp.procedures.length})
                      </p>
                      <div className="space-y-1.5">
                        {tp.procedures.map((proc, i) => {
                          const p = proc as Record<string, string>;
                          return (
                            <div key={i} className="flex items-center gap-2 text-[12px] bg-cyan-50 dark:bg-cyan-950/20 rounded-md px-2.5 py-1.5">
                              <span className="font-medium text-gray-800 dark:text-gray-200">{p.description || `Procedure ${i + 1}`}</span>
                              {p.cpt_code && <span className="font-mono text-[10px] bg-cyan-200 dark:bg-cyan-800 px-1 rounded">{p.cpt_code}</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Lifestyle & Follow-up */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {tp.lifestyle_modifications && tp.lifestyle_modifications.length > 0 && (
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-green-600 mb-1">Lifestyle Modifications</p>
                      <ul className="list-inside list-disc text-sm text-gray-700 dark:text-gray-300 space-y-0.5">
                        {tp.lifestyle_modifications.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                    </div>
                  )}
                  {tp.follow_up_instructions && (
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600 mb-1">Follow-Up Instructions</p>
                      <p className="text-sm text-gray-700 dark:text-gray-300">{tp.follow_up_instructions}</p>
                    </div>
                  )}
                </div>

                {/* Warning Signs */}
                {tp.warning_signs && tp.warning_signs.length > 0 && (
                  <div className="rounded-md bg-red-50 dark:bg-red-950/20 border border-red-100 dark:border-red-900 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-red-600 mb-1">Warning Signs</p>
                    <ul className="list-inside list-disc text-sm text-red-700 dark:text-red-300 space-y-0.5">
                      {tp.warning_signs.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}

                {/* Dietary / Exercise */}
                {(tp.dietary_recommendations || tp.exercise_recommendations) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {tp.dietary_recommendations && (
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-orange-600 mb-1">Dietary Recommendations</p>
                        <p className="text-sm text-gray-700 dark:text-gray-300">{tp.dietary_recommendations}</p>
                      </div>
                    )}
                    {tp.exercise_recommendations && (
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-teal-600 mb-1">Exercise Recommendations</p>
                        <p className="text-sm text-gray-700 dark:text-gray-300">{tp.exercise_recommendations}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   MAIN PAGE
   ══════════════════════════════════════════════════════════════════════════════ */
const TABS = [
  { key: "overview", label: "Overview" },
  { key: "demographics", label: "Demographics" },
  { key: "diagnoses", label: "Diagnoses" },
  { key: "medications", label: "Medications" },
  { key: "treatment-plans", label: "Treatment Plans" },
  { key: "allergies", label: "Allergies" },
  { key: "medical-history", label: "Medical History" },
  { key: "family-history", label: "Family History" },
  { key: "social-history", label: "Social History" },
  { key: "labs", label: "Lab Results" },
  { key: "ai-recommendations", label: "AI Recommendations" },
  { key: "ai-assessment", label: "AI Assessment" },
  { key: "devices", label: "Devices" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

interface PatientDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function PatientDetailPage({ params }: PatientDetailPageProps) {
  const { id } = use(params);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [patient, setPatient] = useState<PatientData | null>(null);

  useEffect(() => {
    fetchPatient(id).then(setPatient).catch(() => {});
  }, [id]);

  return (
    <div className="space-y-6 bg-mesh min-h-full">
      {/* Patient header (always visible) */}
      <PatientHeader patientId={id} />

      {/* Tab navigation */}
      <div className="overflow-x-auto -mx-2 px-2">
        <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 min-w-max">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-2 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                activeTab === tab.key
                  ? "border-healthos-600 text-healthos-600 dark:text-healthos-400"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <VitalsTrendChart patientId={id} />
              </div>
              <div>
                <RiskScoreGauge patientId={id} />
              </div>
            </div>
            <PatientAlerts patientId={id} />
          </div>
        )}
        {activeTab === "demographics" && patient && <div className="card !p-5"><DemographicsTab patient={patient} /></div>}
        {activeTab === "diagnoses" && <DiagnosesTab patientId={id} />}
        {activeTab === "medications" && <MedicationsTab patientId={id} />}
        {activeTab === "treatment-plans" && <TreatmentPlansTab patientId={id} />}
        {activeTab === "allergies" && <AllergiesTab patientId={id} />}
        {activeTab === "medical-history" && <MedicalHistoryTab patientId={id} />}
        {activeTab === "family-history" && <FamilyHistoryTab patientId={id} />}
        {activeTab === "social-history" && <SocialHistoryTab patientId={id} />}
        {activeTab === "labs" && <LabResultsTab patientId={id} />}
        {activeTab === "ai-recommendations" && <AIRecommendationsTab patientId={id} />}
        {activeTab === "ai-assessment" && patient && <AIAssessmentTab patientId={id} patient={patient} />}
        {activeTab === "devices" && <DevicesTab patientId={id} />}
      </div>
    </div>
  );
}
