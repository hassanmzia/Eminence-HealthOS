"use client";

import { useState, useCallback } from "react";
import {
  signClinicalNote,
  amendClinicalNote,
  type ClinicalNote,
  type ClinicalNoteSection,
} from "@/lib/api";

type NoteStatus = "draft" | "pending_review" | "signed";

interface Props {
  sessionId: string;
  note: ClinicalNote;
  onNoteUpdated: (note: ClinicalNote) => void;
  onRegenerate: () => void;
}

/* ── Confidence helpers ──────────────────────────────────────────────────── */

function confidenceColor(score: number): string {
  if (score >= 0.8) return "text-green-700 bg-green-100";
  if (score >= 0.5) return "text-yellow-700 bg-yellow-100";
  return "text-red-700 bg-red-100";
}

function confidenceDot(score: number): string {
  if (score >= 0.8) return "bg-green-500";
  if (score >= 0.5) return "bg-yellow-500";
  return "bg-red-500";
}

function statusBadge(status: NoteStatus) {
  switch (status) {
    case "draft":
      return (
        <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
          Draft — Requires provider review
        </span>
      );
    case "pending_review":
      return (
        <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
          Pending Review
        </span>
      );
    case "signed":
      return (
        <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
          Signed
        </span>
      );
  }
}

/* ── Sign Confirmation Modal ─────────────────────────────────────────────── */

function SignModal({
  onConfirm,
  onCancel,
  loading,
}: {
  onConfirm: (attestation: string) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [attestation, setAttestation] = useState(
    "I attest that I have reviewed this clinical note and confirm it is accurate and complete.",
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-gray-900 p-4 sm:p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Sign &amp; Finalize Note
        </h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          By signing this note, you confirm that you have reviewed the
          AI-generated content and made any necessary amendments.
        </p>
        <textarea
          value={attestation}
          onChange={(e) => setAttestation(e.target.value)}
          rows={3}
          className="mt-4 w-full rounded-lg border border-gray-300 dark:border-gray-600 p-3 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(attestation)}
            disabled={loading}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50"
          >
            {loading ? "Signing..." : "Sign & Finalize"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Section Editor ──────────────────────────────────────────────────────── */

function SectionEditor({
  section,
  isSigned,
  isModified,
  onSave,
}: {
  section: ClinicalNoteSection;
  isSigned: boolean;
  isModified: boolean;
  onSave: (content: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(section.content);

  function handleSave() {
    onSave(draft);
    setEditing(false);
  }

  function handleCancel() {
    setDraft(section.content);
    setEditing(false);
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
            {section.section}
          </h4>
          {isModified && (
            <span className="rounded bg-orange-100 px-1.5 py-0.5 text-[11px] font-medium text-orange-700">
              Modified
            </span>
          )}
          {section.confidence !== undefined && (
            <span
              className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium ${confidenceColor(section.confidence)}`}
            >
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${confidenceDot(section.confidence)}`}
              />
              {(section.confidence * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>
        {!isSigned && !editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-healthos-600 hover:text-healthos-700"
          >
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="mt-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={4}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 p-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
          <div className="mt-2 flex gap-2">
            <button
              onClick={handleSave}
              className="rounded bg-healthos-600 px-3 py-1 text-xs font-medium text-white hover:bg-healthos-700"
            >
              Save
            </button>
            <button
              onClick={handleCancel}
              className="rounded border border-gray-300 dark:border-gray-600 px-3 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <p className="mt-1 whitespace-pre-line text-sm text-gray-700 dark:text-gray-300">
          {section.content}
        </p>
      )}
    </div>
  );
}

/* ── Main NoteReview Component ───────────────────────────────────────────── */

export function NoteReview({ sessionId, note, onNoteUpdated, onRegenerate }: Props) {
  const [showSignModal, setShowSignModal] = useState(false);
  const [signing, setSigning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track local edits: section name -> edited content
  const [edits, setEdits] = useState<Record<string, string>>({});

  const isSigned = note.status === "signed";

  const handleSectionSave = useCallback(
    (sectionName: string, content: string) => {
      setEdits((prev) => ({ ...prev, [sectionName]: content }));
    },
    [],
  );

  const modifiedSections = Object.keys(edits).filter(
    (key) =>
      edits[key] !==
      note.sections.find((s) => s.section === key)?.content,
  );

  /* ── Save amendments ─────────────────────────────────────────────────── */

  async function handleSaveAmendments() {
    if (modifiedSections.length === 0) return;
    setSaving(true);
    setError(null);
    try {
      const amendments = modifiedSections.map((section) => ({
        section,
        content: edits[section],
      }));
      const updated = await amendClinicalNote(sessionId, note.note_id, amendments);
      onNoteUpdated(updated);
      setEdits({});
    } catch {
      setError("Failed to save amendments");
    } finally {
      setSaving(false);
    }
  }

  /* ── Sign & Finalize ─────────────────────────────────────────────────── */

  async function handleSign(attestation: string) {
    setSigning(true);
    setError(null);
    try {
      // Save any pending edits first
      if (modifiedSections.length > 0) {
        const amendments = modifiedSections.map((section) => ({
          section,
          content: edits[section],
        }));
        await amendClinicalNote(sessionId, note.note_id, amendments);
      }
      const signed = await signClinicalNote(sessionId, note.note_id, attestation);
      onNoteUpdated(signed);
      setEdits({});
      setShowSignModal(false);
    } catch {
      setError("Failed to sign note");
    } finally {
      setSigning(false);
    }
  }

  /* ── Render ──────────────────────────────────────────────────────────── */

  const overallConfidence = note.overall_confidence ?? computeOverallConfidence(note.sections);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          SOAP Note (AI-Generated{isSigned ? " — Signed" : " Draft"})
        </h3>
        {statusBadge(note.status)}
      </div>

      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
        <span>
          Generated: {new Date(note.generated_at).toLocaleString()}
        </span>
        <span>Agent: {note.generated_by}</span>
        {note.signed_at && (
          <span>
            Signed: {new Date(note.signed_at).toLocaleString()} by{" "}
            {note.signed_by}
          </span>
        )}
        {overallConfidence !== null && (
          <span
            className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium ${confidenceColor(overallConfidence)}`}
          >
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${confidenceDot(overallConfidence)}`}
            />
            Overall: {(overallConfidence * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {/* Sections */}
      <div className="space-y-3">
        {note.sections.map((section) => {
          const currentContent = edits[section.section] ?? section.content;
          const isModified =
            edits[section.section] !== undefined &&
            edits[section.section] !== section.content;

          return (
            <SectionEditor
              key={section.section}
              section={{ ...section, content: currentContent }}
              isSigned={isSigned}
              isModified={isModified}
              onSave={(content) => handleSectionSave(section.section, content)}
            />
          );
        })}
      </div>

      {/* Amendments history */}
      {note.amendments && note.amendments.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-3">
          <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
            Amendment History
          </h4>
          <ul className="mt-2 space-y-1">
            {note.amendments.map((a, i) => (
              <li key={i} className="text-xs text-gray-600 dark:text-gray-400">
                <span className="font-medium">{a.section}</span> amended on{" "}
                {new Date(a.amended_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      {/* Action buttons */}
      {!isSigned && (
        <div className="flex gap-2">
          <button
            onClick={() => setShowSignModal(true)}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
          >
            Sign &amp; Finalize
          </button>
          {modifiedSections.length > 0 && (
            <button
              onClick={handleSaveAmendments}
              disabled={saving}
              className="rounded-lg border border-healthos-300 bg-healthos-50 px-4 py-2 text-sm font-medium text-healthos-700 hover:bg-healthos-100 disabled:opacity-50"
            >
              {saving ? "Saving..." : `Save Amendments (${modifiedSections.length})`}
            </button>
          )}
          <button
            onClick={onRegenerate}
            className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Regenerate
          </button>
        </div>
      )}

      {isSigned && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          This note has been signed and finalized. No further edits are
          allowed.
        </div>
      )}

      {/* Sign confirmation modal */}
      {showSignModal && (
        <SignModal
          onConfirm={handleSign}
          onCancel={() => setShowSignModal(false)}
          loading={signing}
        />
      )}
    </div>
  );
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function computeOverallConfidence(
  sections: ClinicalNoteSection[],
): number | null {
  const scores = sections
    .map((s) => s.confidence)
    .filter((c): c is number => c !== undefined);
  if (scores.length === 0) return null;
  return scores.reduce((sum, s) => sum + s, 0) / scores.length;
}
