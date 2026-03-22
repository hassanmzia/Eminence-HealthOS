"use client";

import { useState } from "react";
import {
  generateClinicalNote,
  generateFollowUp,
  type ClinicalNote,
  type ClinicalNoteSection,
} from "@/lib/api";
import { NoteReview } from "./NoteReview";
import { useVideoSession } from "@/hooks/useVideoSession";

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
  const video = useVideoSession(sessionId);

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
      <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-1">
        {(["encounter", "notes", "plan"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
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
          {/* Video area */}
          <div
            ref={video.containerRef}
            className="relative flex h-64 items-center justify-center overflow-hidden rounded-lg bg-gray-900 text-gray-500 dark:text-gray-400"
          >
            {video.state === "idle" && (
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
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {sessionId
                    ? 'Click "Start Visit" to begin'
                    : "Select a session from the queue"}
                </p>
              </div>
            )}

            {video.state === "connecting" && (
              <div className="text-center">
                <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-gray-500 border-t-white" />
                <p className="mt-3 text-sm text-gray-300">Connecting to video...</p>
              </div>
            )}

            {video.state === "connected" && video.demoMode && (
              <div className="text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-healthos-600">
                  <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
                  </svg>
                </div>
                <p className="mt-3 text-sm text-green-400">Visit in Progress</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Video provider: Daily.co (demo mode)
                </p>
                <div className="mt-2 flex items-center justify-center gap-2">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                  <span className="text-xs text-green-400">Connected</span>
                  {video.isMuted && <span className="rounded bg-red-900/50 px-1.5 py-0.5 text-[11px] text-red-300">Muted</span>}
                  {video.isCameraOff && <span className="rounded bg-red-900/50 px-1.5 py-0.5 text-[11px] text-red-300">Camera Off</span>}
                </div>
              </div>
            )}

            {video.state === "error" && (
              <div className="text-center">
                <p className="text-sm text-red-400">Connection failed</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{video.error}</p>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center justify-center gap-3">
            {video.state === "idle" || video.state === "error" ? (
              <button
                disabled={!sessionId}
                onClick={video.startVisit}
                className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                Start Visit
              </button>
            ) : (
              <>
                <button
                  onClick={video.toggleMute}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    video.isMuted
                      ? "border-red-300 bg-red-50 text-red-700"
                      : "border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  {video.isMuted ? "Unmute" : "Mute"}
                </button>
                <button
                  onClick={video.toggleCamera}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    video.isCameraOff
                      ? "border-red-300 bg-red-50 text-red-700"
                      : "border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                  }`}
                >
                  {video.isCameraOff ? "Camera On" : "Camera Off"}
                </button>
                <button
                  onClick={video.endVisit}
                  className="rounded-lg bg-red-600 px-6 py-2 text-sm font-medium text-white hover:bg-red-700"
                >
                  End Visit
                </button>
              </>
            )}
          </div>

          {/* AI Agent sidebar */}
          {sessionId && (
            <div className="rounded-lg border border-healthos-100 bg-healthos-50 p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-healthos-700">
                <span className="h-2 w-2 animate-pulse rounded-full bg-healthos-500" />
                AI Agent Insights
              </div>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {video.state === "connected"
                  ? "Listening to encounter... AI-generated SOAP notes will be available when the visit ends."
                  : "AI insights will appear here during the encounter."}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Clinical Notes tab */}
      {activeTab === "notes" && (
        <div className="space-y-4">
          {!sessionId ? (
            <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
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
            <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
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
              <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">
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
            <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
              Select a session to generate a follow-up plan
            </p>
          ) : !followUp && !planLoading ? (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">
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
            <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
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
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Follow-Up Care Plan
                </h3>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Follow-up in {followUp.follow_up_days} days
                </span>
              </div>

              {followUp.monitoring && (
                <div>
                  <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                    Monitoring
                  </h4>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    {followUp.monitoring}
                  </p>
                </div>
              )}

              {followUp.action_items.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                    Action Items
                  </h4>
                  <ul className="mt-1 space-y-1">
                    {followUp.action_items.map((item) => (
                      <li
                        key={item}
                        className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
                      >
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5 rounded border-gray-300 dark:border-gray-600"
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {followUp.patient_education.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                    Patient Education
                  </h4>
                  <ul className="mt-1 space-y-0.5">
                    {followUp.patient_education.map((item) => (
                      <li key={item} className="text-sm text-gray-600 dark:text-gray-400">
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
                  className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
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
