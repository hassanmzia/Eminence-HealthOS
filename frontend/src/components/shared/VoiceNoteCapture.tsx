"use client";

import { useState, useCallback } from "react";
import { useVoiceToText } from "@/hooks/useVoiceToText";

interface VoiceNoteCaptureProps {
  onNoteSaved?: (note: string) => void;
  placeholder?: string;
  className?: string;
}

export function VoiceNoteCapture({
  onNoteSaved,
  placeholder = "Start speaking or type your clinical note...",
  className = "",
}: VoiceNoteCaptureProps) {
  const [noteText, setNoteText] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const handleResult = useCallback(
    (text: string, isFinal: boolean) => {
      if (isFinal) {
        setNoteText((prev) => prev + (prev ? " " : "") + text);
      }
    },
    []
  );

  const handleError = useCallback((error: string) => {
    console.warn("Voice recognition error:", error);
  }, []);

  const {
    isListening,
    isSupported,
    interimTranscript,
    toggleListening,
    resetTranscript,
  } = useVoiceToText({
    onResult: handleResult,
    onError: handleError,
  });

  const handleSave = async () => {
    if (!noteText.trim()) return;
    setIsSaving(true);
    // Simulate save
    await new Promise((r) => setTimeout(r, 800));
    onNoteSaved?.(noteText);
    setNoteText("");
    resetTranscript();
    setIsSaving(false);
  };

  const handleClear = () => {
    setNoteText("");
    resetTranscript();
  };

  return (
    <div className={`card ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Voice Clinical Note
        </h3>
        <div className="flex items-center gap-2">
          {isListening && (
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
              </span>
              <span className="text-xs font-medium text-red-600 dark:text-red-400">Recording</span>
            </div>
          )}
          {!isSupported && (
            <span className="text-xs text-amber-600 dark:text-amber-400">Voice not supported in this browser</span>
          )}
        </div>
      </div>

      {/* Text area */}
      <div className="relative">
        <textarea
          value={noteText + (interimTranscript ? (noteText ? " " : "") + interimTranscript : "")}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder={placeholder}
          rows={6}
          className="input resize-none font-mono text-sm"
        />
        {interimTranscript && (
          <div className="absolute bottom-2 left-3 right-3">
            <span className="text-xs italic text-gray-400">
              {interimTranscript}
            </span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Mic button */}
          <button
            onClick={toggleListening}
            disabled={!isSupported}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
              isListening
                ? "bg-red-50 text-red-700 ring-1 ring-red-200 hover:bg-red-100 dark:bg-red-950/50 dark:text-red-400 dark:ring-red-800"
                : "bg-healthos-50 text-healthos-700 ring-1 ring-healthos-200 hover:bg-healthos-100 dark:bg-healthos-950/50 dark:text-healthos-400 dark:ring-healthos-800"
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isListening ? (
              <>
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
                Stop
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                </svg>
                Record
              </>
            )}
          </button>

          {noteText && (
            <button
              onClick={handleClear}
              className="btn-ghost text-xs"
            >
              Clear
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">{noteText.split(/\s+/).filter(Boolean).length} words</span>
          <button
            onClick={handleSave}
            disabled={!noteText.trim() || isSaving}
            className="btn-primary text-xs disabled:opacity-50"
          >
            {isSaving ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            ) : (
              "Save Note"
            )}
          </button>
        </div>
      </div>

      {/* Quick templates */}
      <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-800">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-gray-400">Quick Templates</p>
        <div className="flex flex-wrap gap-1.5">
          {[
            "Patient presents with...",
            "Assessment: ",
            "Plan: ",
            "Follow-up in...",
            "Vitals within normal limits.",
            "No acute distress noted.",
          ].map((template) => (
            <button
              key={template}
              onClick={() => setNoteText((prev) => prev + (prev ? " " : "") + template)}
              className="rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
            >
              {template}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
