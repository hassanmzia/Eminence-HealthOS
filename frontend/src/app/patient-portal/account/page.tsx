"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchMyAccount,
  updateMyDemographics,
  updateMyEmergencyContact,
  updateMyInsurance,
  addMyAllergy,
  removeMyAllergy,
  type PatientAccountDetails,
  type PatientDemographics,
  type EmergencyContact,
  type InsuranceInfo,
  type PatientAllergy,
} from "@/lib/patient-api";

// ── Helpers ──────────────────────────────────────────────────────────────────

function clsx(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(" ");
}

type Tab = "demographics" | "emergency" | "insurance" | "allergies";

const TABS: { key: Tab; label: string }[] = [
  { key: "demographics", label: "Demographics" },
  { key: "emergency", label: "Emergency Contact" },
  { key: "insurance", label: "Insurance" },
  { key: "allergies", label: "Allergies" },
];

// ── Main page ────────────────────────────────────────────────────────────────

export default function MyAccountPage() {
  const [account, setAccount] = useState<PatientAccountDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("demographics");

  const load = useCallback(() => {
    setLoading(true);
    fetchMyAccount()
      .then(setAccount)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-healthos-200 border-t-healthos-600" />
      </div>
    );
  }

  if (error || !account) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">
          Unable to load your account details. Please try again later.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          My Account
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          View and update your personal information, emergency contacts,
          insurance, and allergies.
        </p>
        {account.mrn && (
          <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
            MRN: {account.mrn}
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-4 overflow-x-auto" aria-label="Account sections">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={clsx(
                "whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition-colors",
                activeTab === tab.key
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab panels */}
      {activeTab === "demographics" && (
        <DemographicsPanel
          demographics={account.demographics}
          onSaved={load}
        />
      )}
      {activeTab === "emergency" && (
        <EmergencyContactPanel
          contact={account.emergency_contact}
          onSaved={load}
        />
      )}
      {activeTab === "insurance" && (
        <InsurancePanel insurance={account.insurance} onSaved={load} />
      )}
      {activeTab === "allergies" && (
        <AllergiesPanel
          allergies={account.allergies}
          onSaved={load}
        />
      )}
    </div>
  );
}

// ── Demographics panel ───────────────────────────────────────────────────────

function DemographicsPanel({
  demographics,
  onSaved,
}: {
  demographics: PatientDemographics;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState(demographics);

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    try {
      await updateMyDemographics(form);
      setSuccess(true);
      setEditing(false);
      onSaved();
    } catch {
      /* keep form open */
    } finally {
      setSaving(false);
    }
  }

  const fields: {
    label: string;
    name: keyof PatientDemographics;
    type?: string;
    readOnly?: boolean;
  }[] = [
    { label: "First Name", name: "first_name" },
    { label: "Last Name", name: "last_name" },
    { label: "Date of Birth", name: "date_of_birth", type: "date", readOnly: true },
    { label: "Sex", name: "sex", readOnly: true },
    { label: "Gender Identity", name: "gender_identity" },
    { label: "Race", name: "race" },
    { label: "Ethnicity", name: "ethnicity" },
    { label: "Preferred Language", name: "preferred_language" },
    { label: "Email", name: "email", type: "email" },
    { label: "Phone", name: "phone", type: "tel" },
    { label: "Address Line 1", name: "address_line1" },
    { label: "Address Line 2", name: "address_line2" },
    { label: "City", name: "city" },
    { label: "State", name: "state" },
    { label: "Postal Code", name: "postal_code" },
    { label: "Country", name: "country" },
  ];

  return (
    <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Personal Information
        </h2>
        {!editing && (
          <button
            onClick={() => { setEditing(true); setSuccess(false); }}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
          >
            Edit
          </button>
        )}
      </div>

      {success && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          Your information has been updated successfully.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {fields.map(({ label, name, type = "text", readOnly }) => (
            <div key={name}>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {label}
              </label>
              {editing && !readOnly ? (
                <input
                  name={name}
                  type={type}
                  value={form[name] ?? ""}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
                />
              ) : (
                <p className="text-sm text-gray-900 dark:text-gray-100">
                  {form[name] || "—"}
                </p>
              )}
            </div>
          ))}
        </div>

        {editing && (
          <div className="mt-6 flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={() => { setEditing(false); setForm(demographics); }}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </form>
    </section>
  );
}

// ── Emergency Contact panel ──────────────────────────────────────────────────

function EmergencyContactPanel({
  contact,
  onSaved,
}: {
  contact: EmergencyContact;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState(contact);

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    try {
      await updateMyEmergencyContact(form);
      setSuccess(true);
      setEditing(false);
      onSaved();
    } catch {
      /* keep form open */
    } finally {
      setSaving(false);
    }
  }

  const relationships = [
    "Spouse", "Parent", "Child", "Sibling", "Friend", "Guardian", "Other",
  ];

  return (
    <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Emergency Contact
        </h2>
        {!editing && (
          <button
            onClick={() => { setEditing(true); setSuccess(false); }}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
          >
            Edit
          </button>
        )}
      </div>

      {success && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          Emergency contact updated successfully.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Full Name
            </label>
            {editing ? (
              <input
                name="name"
                value={form.name ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            ) : (
              <p className="text-sm text-gray-900 dark:text-gray-100">
                {form.name || "—"}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Phone Number
            </label>
            {editing ? (
              <input
                name="phone"
                type="tel"
                value={form.phone ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            ) : (
              <p className="text-sm text-gray-900 dark:text-gray-100">
                {form.phone || "—"}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Relationship
            </label>
            {editing ? (
              <select
                name="relationship"
                value={form.relationship ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              >
                <option value="">Select...</option>
                {relationships.map((r) => (
                  <option key={r} value={r.toLowerCase()}>
                    {r}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-sm text-gray-900 dark:text-gray-100 capitalize">
                {form.relationship || "—"}
              </p>
            )}
          </div>
        </div>

        {editing && (
          <div className="mt-6 flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={() => { setEditing(false); setForm(contact); }}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </form>
    </section>
  );
}

// ── Insurance panel ──────────────────────────────────────────────────────────

function InsurancePanel({
  insurance,
  onSaved,
}: {
  insurance: InsuranceInfo;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState(insurance);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    try {
      await updateMyInsurance(form);
      setSuccess(true);
      setEditing(false);
      onSaved();
    } catch {
      /* keep form open */
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Insurance Information
        </h2>
        {!editing && (
          <button
            onClick={() => { setEditing(true); setSuccess(false); }}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
          >
            Edit
          </button>
        )}
      </div>

      {success && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          Insurance information updated successfully.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Insurance Provider
            </label>
            {editing ? (
              <input
                name="provider"
                value={form.provider ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            ) : (
              <p className="text-sm text-gray-900 dark:text-gray-100">
                {form.provider || "—"}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Member ID
            </label>
            {editing ? (
              <input
                name="member_id"
                value={form.member_id ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            ) : (
              <p className="text-sm text-gray-900 dark:text-gray-100">
                {form.member_id || "—"}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Group Number
            </label>
            {editing ? (
              <input
                name="group_number"
                value={form.group_number ?? ""}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            ) : (
              <p className="text-sm text-gray-900 dark:text-gray-100">
                {form.group_number || "—"}
              </p>
            )}
          </div>
        </div>

        {editing && (
          <div className="mt-6 flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={() => { setEditing(false); setForm(insurance); }}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </form>
    </section>
  );
}

// ── Allergies panel ──────────────────────────────────────────────────────────

function AllergiesPanel({
  allergies,
  onSaved,
}: {
  allergies: PatientAllergy[];
  onSaved: () => void;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [form, setForm] = useState({
    allergen: "",
    allergy_type: "drug",
    severity: "moderate",
    reaction: "",
    onset_date: "",
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!form.allergen.trim()) return;
    setSaving(true);
    try {
      await addMyAllergy({
        allergen: form.allergen,
        allergy_type: form.allergy_type,
        severity: form.severity,
        reaction: form.reaction || undefined,
        onset_date: form.onset_date || undefined,
      });
      setForm({ allergen: "", allergy_type: "drug", severity: "moderate", reaction: "", onset_date: "" });
      setShowAdd(false);
      onSaved();
    } catch {
      /* keep form open */
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove(id: string) {
    setRemoving(id);
    try {
      await removeMyAllergy(id);
      onSaved();
    } catch {
      /* ignore */
    } finally {
      setRemoving(null);
    }
  }

  const severityColors: Record<string, string> = {
    mild: "bg-yellow-100 text-yellow-800",
    moderate: "bg-orange-100 text-orange-800",
    severe: "bg-red-100 text-red-800",
  };

  return (
    <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Allergies
        </h2>
        {!showAdd && (
          <button
            onClick={() => setShowAdd(true)}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
          >
            + Add Allergy
          </button>
        )}
      </div>

      {/* Add form */}
      {showAdd && (
        <form
          onSubmit={handleAdd}
          className="mb-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4 space-y-4"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Allergen *
              </label>
              <input
                name="allergen"
                value={form.allergen}
                onChange={handleChange}
                required
                placeholder="e.g. Penicillin, Peanuts"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Type
              </label>
              <select
                name="allergy_type"
                value={form.allergy_type}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              >
                <option value="drug">Drug</option>
                <option value="food">Food</option>
                <option value="environmental">Environmental</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Severity
              </label>
              <select
                name="severity"
                value={form.severity}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              >
                <option value="mild">Mild</option>
                <option value="moderate">Moderate</option>
                <option value="severe">Severe</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Reaction
              </label>
              <input
                name="reaction"
                value={form.reaction}
                onChange={handleChange}
                placeholder="e.g. Hives, Anaphylaxis"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Onset Date
              </label>
              <input
                name="onset_date"
                type="date"
                value={form.onset_date}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Adding..." : "Add Allergy"}
            </button>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Allergy list */}
      {allergies.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No allergies on record. If you have known allergies, please add them
          using the button above.
        </p>
      ) : (
        <div className="space-y-3">
          {allergies.map((allergy) => (
            <div
              key={allergy.id}
              className="flex items-start justify-between rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {allergy.allergen}
                  </p>
                  <span
                    className={clsx(
                      "rounded-full px-2 py-0.5 text-xs font-medium",
                      severityColors[allergy.severity] ?? "bg-gray-100 text-gray-700",
                    )}
                  >
                    {allergy.severity}
                  </span>
                  <span className="rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300 capitalize">
                    {allergy.allergy_type}
                  </span>
                </div>
                {allergy.reaction && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Reaction: {allergy.reaction}
                  </p>
                )}
                {allergy.onset_date && (
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Since: {new Date(allergy.onset_date).toLocaleDateString()}
                  </p>
                )}
              </div>
              <button
                onClick={() => handleRemove(allergy.id)}
                disabled={removing === allergy.id}
                className="ml-3 shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 transition-colors"
              >
                {removing === allergy.id ? "Removing..." : "Remove"}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
