"use client";

import { useState } from "react";
import {
  generateClinicalNote,
  generateFollowUp,
  type ClinicalNote,
  type ClinicalNoteSection,
} from "@/lib/api";
import { NoteReview } from "./NoteReview";

type Tab = "encounter" | "notes" | "plan";

interface FollowUpPlan {
  follow_up_days: number;
  monitoring: string;
  action_items: string[];
  patient_education: string[];
}

interface Props {
  sessionId?: string;
}

export function EncounterConsole({ sessionId }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("encounter");
  const [clinicalNote, setClinicalNote] = useState<ClinicalNote | null>(null);
  const [followUp, setFollowUp] = useState<FollowUpPlan | null>(null);
  const [notesLoading, setNotesLoading] = useState(false);
  const [planLoading, setPlanLoading] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);

  async function handleGenerateNote() {
    if (!sessionId) return;
    setNotesLoading(true);
    setNotesError(null);
    try {
      const result = await generateClinicalNote(sessionId, {});

      // Build sections from the API response
      let sections: ClinicalNoteSection[] = [];
      const rawSections =
        (result.sections as ClinicalNoteSection[]) ||
        (result.notes as ClinicalNoteSection[]) ||
        [];

      if (rawSections.length > 0) {
        sections = rawSections;
      } else {
        // Fallback: build from top-level SOAP fields
        if (result.subjective)
          sections.push({
            section: "Subjective",
            content: result.subjective as string,
            confidence: (result.confidence as Record<string, number>)?.subjective,
          });
        if (result.objective)
          sections.push({
            section: "Objective",
            content: result.objective as string,
            confidence: (result.confidence as Record<string, number>)?.objective,
          });
        if (result.assessment)
          sections.push({
            section: "Assessment",
            content: result.assessment as string,
            confidence: (result.confidence as Record<string, number>)?.assessment,
          });
        if (result.plan)
          sections.push({
            section: "Plan",
            content: Array.isArray(result.plan)
              ? (result.plan as string[]).join("\n")
              : (result.plan as string),
            confidence: (result.confidence as Record<string, number>)?.plan,
          });
        if (sections.length === 0) {
          sections = [
            { section: "Note", content: JSON.stringify(result, null, 2) },
          ];
        }
      }

      const note: ClinicalNote = {
        note_id: (result.note_id as string) || crypto.randomUUID(),
        session_id: sessionId,
        status: "draft",
        sections,
        generated_at:
          (result.generated_at as string) || new Date().toISOString(),
        generated_by: (result.generated_by as string) || "Clinical Note Agent",
        overall_confidence: result.overall_confidence as number | undefined,
      };

      setClinicalNote(note);
    } catch {
      setNotesError("Failed to generate clinical note");
    } finally {
      setNotesLoading(false);
    }
  }

  async function handleGenerateFollowUp() {
    if (!sessionId) return;
    setPlanLoading(true);
    setPlanError(null);
    try {
      const result = await generateFollowUp(sessionId, {});
      setFollowUp({
        follow_up_days: (result.follow_up_days as number) || 14,
        monitoring: (result.monitoring as string) || "",
        action_items: (result.action_items as string[]) || [],
        patient_education: (result.patient_education as string[]) || [],
      });
    } catch {
      setPlanError("Failed to generate follow-up plan");
    } finally {
      setPlanLoading(false);
    }
  }

  return (
    <div className="card">
      {/* Tab bar */}
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
        {(["encounter", "notes", "plan"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "notes"
              ? "Clinical Notes"
              : tab === "plan"
                ? "Follow-Up Plan"
                : "Encounter"}
          </button>
        ))}
      </div>

      {/* Encounter tab */}
      {activeTab === "encounter" && (
        <div className="space-y-4">
          {/* Video placeholder */}
          <div className="flex h-64 items-center justify-center rounded-lg bg-gray-900 text-gray-400">
            <div className="text-center">
              <svg
                className="mx-auto h-12 w-12"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"
                />
              </svg>
              <p className="mt-2 text-sm">Video encounter area</p>
              <p className="text-xs text-gray-500">
                {sessionId
                  ? 'Click "Start Visit" to begin'
                  : "Select a session from the queue"}
              </p>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-center gap-3">
            <button
              disabled={!sessionId}
              className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              Start Visit
            </button>
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Mute
            </button>
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Camera
            </button>
            <button className="rounded-lg bg-red-600 px-6 py-2 text-sm font-medium text-white hover:bg-red-700">
              End Visit
            </button>
          </div>

          {/* AI Agent sidebar */}
          {sessionId && (
            <div className="rounded-lg border border-healthos-100 bg-healthos-50 p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-healthos-700">
                <span className="h-2 w-2 animate-pulse rounded-full bg-healthos-500" />
                AI Agent Insights
              </div>
              <p className="mt-2 text-xs text-gray-500">
                AI insights will appear here during the encounter.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Clinical Notes tab */}
      {activeTab === "notes" && (
        <div className="space-y-4">
          {!sessionId ? (
            <p className="py-8 text-center text-sm text-gray-400">
              Select a session to generate notes
            </p>
          ) : clinicalNote && !notesLoading ? (
            /* ── Show the HITL NoteReview component ── */
            <NoteReview
              sessionId={sessionId}
              note={clinicalNote}
              onNoteUpdated={(updated) => setClinicalNote(updated)}
              onRegenerate={handleGenerateNote}
            />
          ) : notesLoading ? (
            <div className="py-8 text-center text-sm text-gray-400">
              Generating clinical note...
            </div>
          ) : notesError ? (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-red-400">{notesError}</p>
              <button
                onClick={handleGenerateNote}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-gray-400">
                No clinical notes generated yet
              </p>
              <button
                onClick={handleGenerateNote}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
              >
                Generate SOAP Note
              </button>
            </div>
          )}
        </div>
      )}

      {/* Follow-Up Plan tab */}
      {activeTab === "plan" && (
        <div className="space-y-4">
          {!sessionId ? (
            <p className="py-8 text-center text-sm text-gray-400">
              Select a session to generate a follow-up plan
            </p>
          ) : !followUp && !planLoading ? (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-gray-400">
                No follow-up plan generated yet
              </p>
              <button
                onClick={handleGenerateFollowUp}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
              >
                Generate Follow-Up Plan
              </button>
            </div>
          ) : planLoading ? (
            <div className="py-8 text-center text-sm text-gray-400">
              Generating follow-up plan...
            </div>
          ) : planError ? (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-red-400">{planError}</p>
              <button
                onClick={handleGenerateFollowUp}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
              >
                Retry
              </button>
            </div>
          ) : followUp ? (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-700">
                  Follow-Up Care Plan
                </h3>
                <span className="text-xs text-gray-400">
                  Follow-up in {followUp.follow_up_days} days
                </span>
              </div>

              {followUp.monitoring && (
                <div>
                  <h4 className="text-xs font-medium uppercase text-gray-400">
                    Monitoring
                  </h4>
                  <p className="mt-1 text-sm text-gray-700">
                    {followUp.monitoring}
                  </p>
                </div>
              )}

              {followUp.action_items.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium uppercase text-gray-400">
                    Action Items
                  </h4>
                  <ul className="mt-1 space-y-1">
                    {followUp.action_items.map((item) => (
                      <li
                        key={item}
                        className="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5 rounded border-gray-300"
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {followUp.patient_education.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium uppercase text-gray-400">
                    Patient Education
                  </h4>
                  <ul className="mt-1 space-y-0.5">
                    {followUp.patient_education.map((item) => (
                      <li key={item} className="text-sm text-gray-600">
                        &bull; {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex gap-2">
                <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
                  Finalize Plan
                </button>
                <button
                  onClick={handleGenerateFollowUp}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Regenerate
                </button>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
