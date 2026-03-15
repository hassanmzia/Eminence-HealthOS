"use client";

import { useState } from "react";
import { EncounterConsole } from "@/components/telehealth/EncounterConsole";
import { SessionQueue } from "@/components/telehealth/SessionQueue";
import { VisitPreparation } from "@/components/telehealth/VisitPreparation";
import { createTelehealthSession, type TelehealthSession } from "@/lib/api";

export default function TelehealthPage() {
  const [selectedSession, setSelectedSession] = useState<TelehealthSession | null>(null);
  const [showNewSession, setShowNewSession] = useState(false);
  const [creating, setCreating] = useState(false);
  const [sessionForm, setSessionForm] = useState({ patientName: "", reason: "", sessionType: "video" });

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const session = await createTelehealthSession({
        patient_name: sessionForm.patientName,
        reason: sessionForm.reason,
        session_type: sessionForm.sessionType,
      });
      setSelectedSession(session);
      setShowNewSession(false);
      setSessionForm({ patientName: "", reason: "", sessionType: "video" });
    } catch {
      // Silently handle — session queue will refresh
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Telehealth</h1>
        <button
          onClick={() => setShowNewSession(true)}
          className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700"
        >
          New Session
        </button>
      </div>

      {/* New Session Modal */}
      {showNewSession && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowNewSession(false)}>
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">New Telehealth Session</h2>
              <button onClick={() => setShowNewSession(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Patient Name *</label>
                <input required value={sessionForm.patientName} onChange={(e) => setSessionForm({ ...sessionForm, patientName: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Maria Garcia" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Session Type *</label>
                <select required value={sessionForm.sessionType} onChange={(e) => setSessionForm({ ...sessionForm, sessionType: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500">
                  <option value="video">Video Call</option>
                  <option value="audio">Audio Only</option>
                  <option value="chat">Chat</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason for Visit</label>
                <input value={sessionForm.reason} onChange={(e) => setSessionForm({ ...sessionForm, reason: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500" placeholder="e.g. Follow-up on blood pressure" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowNewSession(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={creating} className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 disabled:opacity-50">{creating ? "Creating..." : "Start Session"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Session queue and active encounter */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6">
          <SessionQueue
            selectedSessionId={selectedSession?.session_id}
            onSelectSession={setSelectedSession}
          />
          <VisitPreparation sessionId={selectedSession?.session_id} />
        </div>
        <div className="lg:col-span-2">
          <EncounterConsole sessionId={selectedSession?.session_id} />
        </div>
      </div>
    </div>
  );
}
