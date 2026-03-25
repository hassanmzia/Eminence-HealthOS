"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchQuestionnaireTemplates,
  fetchMyQuestionnaires,
  createQuestionnaire,
  updateQuestionnaire,
  type QuestionnaireTemplate,
  type QuestionnaireRecord,
  type QuestionnaireSection,
  type QuestionnaireField,
} from "@/lib/patient-api";

function clsx(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(" ");
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function QuestionnairesPage() {
  const [templates, setTemplates] = useState<QuestionnaireTemplate[]>([]);
  const [records, setRecords] = useState<QuestionnaireRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeForm, setActiveForm] = useState<string | null>(null);
  const [editingRecord, setEditingRecord] = useState<QuestionnaireRecord | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, r] = await Promise.all([
        fetchQuestionnaireTemplates(),
        fetchMyQuestionnaires(),
      ]);
      setTemplates(t.templates);
      setRecords(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
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

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">Unable to load questionnaires. Please try again later.</p>
      </div>
    );
  }

  // If filling a form
  if (activeForm) {
    const template = templates.find((t) => t.type === activeForm);
    if (!template) return null;
    return (
      <QuestionnaireFormView
        template={template}
        existing={editingRecord}
        onBack={() => {
          setActiveForm(null);
          setEditingRecord(null);
          load();
        }}
      />
    );
  }

  const submitted = records.filter((r) => r.status === "submitted" || r.status === "reviewed");
  const drafts = records.filter((r) => r.status === "draft");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Health Questionnaires
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Complete pre-visit questionnaires to help your care team prepare for
          your appointment.
        </p>
      </div>

      {/* Available questionnaires */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Start a New Questionnaire
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <button
              key={t.type}
              onClick={() => {
                setEditingRecord(null);
                setActiveForm(t.type);
              }}
              className="group rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 text-left transition-colors hover:border-healthos-300 hover:bg-healthos-50 dark:hover:bg-healthos-900/20"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-healthos-100 text-healthos-700">
                  <FormIcon type={t.type} />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-healthos-700">
                  {t.title}
                </h3>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {t.description}
              </p>
              <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                {t.sections.length} section{t.sections.length !== 1 ? "s" : ""} &middot;{" "}
                {t.sections.reduce((sum, s) => sum + s.fields.length, 0)} questions
              </p>
            </button>
          ))}
        </div>
      </section>

      {/* Drafts */}
      {drafts.length > 0 && (
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
            Drafts (In Progress)
          </h2>
          <div className="space-y-3">
            {drafts.map((r) => {
              const tmpl = templates.find((t) => t.type === r.questionnaire_type);
              return (
                <div
                  key={r.id}
                  className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {tmpl?.title ?? r.questionnaire_type}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Started: {r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setEditingRecord(r);
                      setActiveForm(r.questionnaire_type);
                    }}
                    className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
                  >
                    Continue
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Submitted */}
      {submitted.length > 0 && (
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
            Submitted Questionnaires
          </h2>
          <div className="space-y-3">
            {submitted.map((r) => {
              const tmpl = templates.find((t) => t.type === r.questionnaire_type);
              return (
                <div
                  key={r.id}
                  className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-4"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {tmpl?.title ?? r.questionnaire_type}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Submitted: {r.submitted_at ? new Date(r.submitted_at).toLocaleDateString() : "—"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={clsx(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        r.status === "reviewed"
                          ? "bg-green-100 text-green-700"
                          : "bg-blue-100 text-blue-700",
                      )}
                    >
                      {r.status === "reviewed" ? "Reviewed" : "Submitted"}
                    </span>
                    {r.reviewer_notes && (
                      <span className="text-xs text-gray-500" title={r.reviewer_notes}>
                        Has notes
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Questionnaire form view ──────────────────────────────────────────────────

function QuestionnaireFormView({
  template,
  existing,
  onBack,
}: {
  template: QuestionnaireTemplate;
  existing: QuestionnaireRecord | null;
  onBack: () => void;
}) {
  const [responses, setResponses] = useState<Record<string, unknown>>(
    existing?.responses ?? {},
  );
  const [currentSection, setCurrentSection] = useState(0);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [recordId, setRecordId] = useState<string | null>(existing?.id ?? null);

  const sections = template.sections;
  const section = sections[currentSection];
  const isLast = currentSection === sections.length - 1;
  const isFirst = currentSection === 0;

  function setField(key: string, value: unknown) {
    setResponses((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSaveDraft() {
    setSaving(true);
    setSuccess(null);
    try {
      if (recordId) {
        await updateQuestionnaire(recordId, { responses, status: "draft" });
      } else {
        const created = await createQuestionnaire({
          questionnaire_type: template.type,
          responses,
          status: "draft",
        });
        setRecordId(created.id);
      }
      setSuccess("Draft saved.");
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setSuccess(null);
    try {
      if (recordId) {
        await updateQuestionnaire(recordId, { responses, status: "submitted" });
      } else {
        await createQuestionnaire({
          questionnaire_type: template.type,
          responses,
          status: "submitted",
        });
      }
      setSuccess("Questionnaire submitted successfully!");
      setTimeout(onBack, 1500);
    } catch {
      /* ignore */
    } finally {
      setSubmitting(false);
    }
  }

  // Count answered fields in current section
  const answeredInSection = section.fields.filter((f) => {
    const val = responses[f.key];
    if (f.type === "boolean") return val === true;
    return val !== undefined && val !== null && val !== "";
  }).length;

  // Total progress
  const totalFields = sections.reduce((s, sec) => s + sec.fields.length, 0);
  const totalAnswered = sections.reduce(
    (s, sec) =>
      s +
      sec.fields.filter((f) => {
        const val = responses[f.key];
        if (f.type === "boolean") return val === true;
        return val !== undefined && val !== null && val !== "";
      }).length,
    0,
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          &larr; Back
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {template.title}
          </h1>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
            {template.description}
          </p>
        </div>
      </div>

      {/* Progress */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
          <span>
            Section {currentSection + 1} of {sections.length}: {section.label}
          </span>
          <span>
            {totalAnswered} of {totalFields} fields completed
          </span>
        </div>
        <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-800">
          <div
            className="h-2 rounded-full bg-healthos-600 transition-all"
            style={{ width: `${totalFields > 0 ? (totalAnswered / totalFields) * 100 : 0}%` }}
          />
        </div>
        {/* Section pills */}
        <div className="mt-3 flex flex-wrap gap-2">
          {sections.map((s, i) => (
            <button
              key={s.key}
              onClick={() => setCurrentSection(i)}
              className={clsx(
                "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                i === currentSection
                  ? "bg-healthos-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Form fields */}
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="mb-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
          {section.label}
        </h2>
        <p className="mb-5 text-xs text-gray-400">
          {answeredInSection} of {section.fields.length} answered in this section
        </p>

        <div className="space-y-4">
          {section.fields.map((field) => (
            <FieldInput
              key={field.key}
              field={field}
              value={responses[field.key]}
              onChange={(val) => setField(field.key, val)}
            />
          ))}
        </div>
      </section>

      {/* Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-3">
          {!isFirst && (
            <button
              onClick={() => setCurrentSection((i) => i - 1)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Previous
            </button>
          )}
          {!isLast && (
            <button
              onClick={() => setCurrentSection((i) => i + 1)}
              className="rounded-lg bg-healthos-600 px-5 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors"
            >
              Next Section
            </button>
          )}
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleSaveDraft}
            disabled={saving}
            className="rounded-lg border border-gray-300 dark:border-gray-600 px-5 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save Draft"}
          </button>
          {isLast && (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? "Submitting..." : "Submit Questionnaire"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Field input renderer ─────────────────────────────────────────────────────

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: QuestionnaireField;
  value: unknown;
  onChange: (val: unknown) => void;
}) {
  const inputClass =
    "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none";

  if (field.type === "boolean") {
    return (
      <label className="flex items-center gap-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800 p-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
        <input
          type="checkbox"
          checked={value === true}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-healthos-600 focus:ring-healthos-500"
        />
        <span className="text-sm text-gray-900 dark:text-gray-100">
          {field.label}
        </span>
      </label>
    );
  }

  if (field.type === "select") {
    return (
      <div>
        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
          {field.label}
        </label>
        <select
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className={inputClass}
        >
          <option value="">Select...</option>
          {field.options?.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (field.type === "textarea") {
    return (
      <div>
        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
          {field.label}
        </label>
        <textarea
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          className={inputClass}
          placeholder="Type your answer..."
        />
      </div>
    );
  }

  // text
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
        {field.label}
      </label>
      <input
        type="text"
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
        placeholder="Type your answer..."
      />
    </div>
  );
}

// ── Icons ────────────────────────────────────────────────────────────────────

function FormIcon({ type }: { type: string }) {
  if (type === "review_of_systems") {
    return (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
      </svg>
    );
  }
  if (type === "history_presenting_illness") {
    return (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    );
  }
  // pre_visit or default
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75" />
    </svg>
  );
}
