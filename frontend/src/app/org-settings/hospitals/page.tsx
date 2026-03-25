"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  fetchHospitals,
  fetchDepartments,
  createHospital,
  createDepartment,
  type HospitalResponse,
  type DepartmentResponse,
} from "@/lib/platform-api";

/* ── tiny icons (inline SVG to avoid extra deps) ───────────────────────────── */
const IconBack = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
);
const IconPlus = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
);
const IconBuilding = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0H5m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
);

/* ── Create Hospital Modal ─────────────────────────────────────────────────── */
function CreateHospitalModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ name: "", address: "", city: "", state: "", zip_code: "", phone: "", email: "", website: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) { setError("Name is required"); return; }
    setSaving(true);
    setError("");
    try {
      await createHospital({ name: form.name, address: form.address || undefined, city: form.city || undefined, state: form.state || undefined, zip_code: form.zip_code || undefined, phone: form.phone || undefined, email: form.email || undefined, website: form.website || undefined });
      setForm({ name: "", address: "", city: "", state: "", zip_code: "", phone: "", email: "", website: "" });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create hospital");
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-lg mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">Create Hospital</h3>
        {error && <div className="mb-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-2 text-sm text-red-700 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Hospital Name *</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. City General Hospital" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Address</label>
              <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">City</label>
              <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">State</label>
              <input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">ZIP Code</label>
              <input value={form.zip_code} onChange={(e) => setForm({ ...form, zip_code: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Phone</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Email</label>
              <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Website</label>
            <input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500 disabled:opacity-50">{saving ? "Creating..." : "Create Hospital"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Create Department Modal ───────────────────────────────────────────────── */
function CreateDepartmentModal({ open, onClose, onCreated, hospitalId, hospitalName }: { open: boolean; onClose: () => void; onCreated: () => void; hospitalId: string; hospitalName: string }) {
  const [form, setForm] = useState({ name: "", location: "", phone: "", email: "", head_of_department: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) { setError("Name is required"); return; }
    setSaving(true);
    setError("");
    try {
      await createDepartment({ hospital_id: hospitalId, name: form.name, location: form.location || undefined, phone: form.phone || undefined, email: form.email || undefined, head_of_department: form.head_of_department || undefined });
      setForm({ name: "", location: "", phone: "", email: "", head_of_department: "" });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create department");
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-md mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-1">Add Department</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Adding to <span className="font-medium">{hospitalName}</span></p>
        {error && <div className="mb-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-2 text-sm text-red-700 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Department Name *</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Cardiology" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Location / Floor</label>
              <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Building A, Floor 3" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Phone</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Email</label>
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Head of Department</label>
            <input value={form.head_of_department} onChange={(e) => setForm({ ...form, head_of_department: e.target.value })} className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="Dr. Jane Smith" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500 disabled:opacity-50">{saving ? "Creating..." : "Add Department"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Hospital Card (expandable with departments) ───────────────────────────── */
function HospitalCard({ hospital, onRefresh }: { hospital: HospitalResponse; onRefresh: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [departments, setDepartments] = useState<DepartmentResponse[]>([]);
  const [loadingDepts, setLoadingDepts] = useState(false);
  const [showAddDept, setShowAddDept] = useState(false);

  const loadDepartments = useCallback(async () => {
    setLoadingDepts(true);
    try {
      const data = await fetchDepartments(hospital.id);
      setDepartments(data);
    } catch { /* ignore */ }
    setLoadingDepts(false);
  }, [hospital.id]);

  useEffect(() => {
    if (expanded) loadDepartments();
  }, [expanded, loadDepartments]);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
      {/* Hospital header */}
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-healthos-100 dark:bg-healthos-900/30 flex items-center justify-center text-healthos-600 dark:text-healthos-400">
          <IconBuilding />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{hospital.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {[hospital.city, hospital.state].filter(Boolean).join(", ") || "No location set"}
            {hospital.phone && ` · ${hospital.phone}`}
          </p>
        </div>
        <span className={`flex-shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${hospital.is_active ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"}`}>
          {hospital.is_active ? "Active" : "Inactive"}
        </span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
      </button>

      {/* Departments panel */}
      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30 p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Departments</h4>
            <button onClick={() => setShowAddDept(true)} className="inline-flex items-center gap-1 rounded-lg bg-healthos-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-healthos-500 transition">
              <IconPlus /> Add Department
            </button>
          </div>

          {loadingDepts ? (
            <div className="flex justify-center py-4"><div className="h-5 w-5 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" /></div>
          ) : departments.length === 0 ? (
            <p className="text-center text-sm text-gray-400 dark:text-gray-500 py-4">No departments yet. Add one to get started.</p>
          ) : (
            <div className="space-y-2">
              {departments.map((dept) => (
                <div key={dept.id} className="flex items-center justify-between rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
                  <div>
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{dept.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {[dept.location, dept.head_of_department && `Head: ${dept.head_of_department}`].filter(Boolean).join(" · ") || "—"}
                    </p>
                  </div>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${dept.is_active ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"}`}>
                    {dept.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              ))}
            </div>
          )}

          <CreateDepartmentModal open={showAddDept} onClose={() => setShowAddDept(false)} onCreated={loadDepartments} hospitalId={hospital.id} hospitalName={hospital.name} />
        </div>
      )}
    </div>
  );
}

/* ── Main Page ─────────────────────────────────────────────────────────────── */
export default function HospitalsPage() {
  const { isAdmin } = useAuth();
  const [hospitals, setHospitals] = useState<HospitalResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const loadHospitals = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchHospitals();
      setHospitals(data);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadHospitals(); }, [loadHospitals]);

  if (!isAdmin) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">Admin access required</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 bg-mesh min-h-full max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/org-settings" className="rounded-lg border border-gray-200 dark:border-gray-700 p-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition">
            <IconBack />
          </a>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Hospitals & Departments</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Configure your facilities and their departments</p>
          </div>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500 transition">
          <IconPlus /> Add Hospital
        </button>
      </div>

      {/* Hospital list */}
      {loading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
        </div>
      ) : hospitals.length === 0 ? (
        <div className="card !p-8 text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400 mb-3">
            <IconBuilding />
          </div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">No hospitals yet</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-4">Create your first hospital to start organizing departments and staff.</p>
          <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-semibold text-white hover:bg-healthos-500">
            <IconPlus /> Create Hospital
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {hospitals.map((h) => (
            <HospitalCard key={h.id} hospital={h} onRefresh={loadHospitals} />
          ))}
        </div>
      )}

      <CreateHospitalModal open={showCreate} onClose={() => setShowCreate(false)} onCreated={loadHospitals} />
    </div>
  );
}
