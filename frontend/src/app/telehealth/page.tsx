"use client";

import { useState } from "react";
import { EncounterConsole } from "@/components/telehealth/EncounterConsole";
import { SessionQueue } from "@/components/telehealth/SessionQueue";
import { VisitPreparation } from "@/components/telehealth/VisitPreparation";
import type { TelehealthSession } from "@/lib/api";

export default function TelehealthPage() {
  const [selectedSession, setSelectedSession] = useState<TelehealthSession | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Telehealth</h1>
        <button className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700">
          New Session
        </button>
      </div>

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
