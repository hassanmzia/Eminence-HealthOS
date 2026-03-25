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
  type DiagnosisResponse,
  type PrescriptionResponse,
  type AllergyResponse,
  type MedicalHistoryResponse,
  type SocialHistoryResponse,
  type FamilyHistoryResponse,
  type LabTestResponse,
} from "@/lib/platform-api";
import { PatientHeader } from "@/components/patients/PatientHeader";
import { VitalsTrendChart } from "@/components/patients/VitalsTrendChart";
import { RiskScoreGauge } from "@/components/patients/RiskScoreGauge";
import { PatientAlerts } from "@/components/patients/PatientAlerts";

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
   MAIN PAGE
   ══════════════════════════════════════════════════════════════════════════════ */
const TABS = [
  { key: "overview", label: "Overview" },
  { key: "demographics", label: "Demographics" },
  { key: "diagnoses", label: "Diagnoses" },
  { key: "medications", label: "Medications" },
  { key: "allergies", label: "Allergies" },
  { key: "medical-history", label: "Medical History" },
  { key: "family-history", label: "Family History" },
  { key: "social-history", label: "Social History" },
  { key: "labs", label: "Lab Results" },
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
        {activeTab === "allergies" && <AllergiesTab patientId={id} />}
        {activeTab === "medical-history" && <MedicalHistoryTab patientId={id} />}
        {activeTab === "family-history" && <FamilyHistoryTab patientId={id} />}
        {activeTab === "social-history" && <SocialHistoryTab patientId={id} />}
        {activeTab === "labs" && <LabResultsTab patientId={id} />}
      </div>
    </div>
  );
}
