"use client";

import { useEffect, useState } from "react";
import {
  fetchPatientMessages,
  sendMessage,
  type PatientMessage,
  type PatientMessagesResponse,
} from "@/lib/patient-api";

export default function MessagesPage() {
  const [data, setData] = useState<PatientMessagesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCompose, setShowCompose] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<PatientMessage | null>(null);

  const loadMessages = () => {
    setLoading(true);
    fetchPatientMessages()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadMessages();
  }, []);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-healthos-200 border-t-healthos-600" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">Unable to load messages. Please try again later.</p>
      </div>
    );
  }

  const messages = data?.messages ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Messages</h1>
          <p className="mt-1 text-sm text-gray-500">
            Secure messaging with your care team.
            {(data?.unread ?? 0) > 0 && (
              <span className="ml-2 inline-flex items-center rounded-full bg-healthos-100 px-2 py-0.5 text-xs font-medium text-healthos-700">
                {data?.unread} unread
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => {
            setShowCompose(!showCompose);
            setSelectedMessage(null);
          }}
          className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700"
        >
          New Message
        </button>
      </div>

      {/* Compose form */}
      {showCompose && (
        <ComposeForm
          onClose={() => setShowCompose(false)}
          onSent={() => {
            setShowCompose(false);
            loadMessages();
          }}
        />
      )}

      {/* Message list + detail */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Inbox list */}
        <div className="lg:col-span-1">
          <div className="rounded-xl border border-gray-200 bg-white">
            <div className="border-b border-gray-100 px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">Inbox</h2>
            </div>
            {messages.length === 0 ? (
              <div className="p-4">
                <p className="text-sm text-gray-500">No messages yet.</p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {messages.map((msg) => (
                  <li key={msg.id}>
                    <button
                      onClick={() => {
                        setSelectedMessage(msg);
                        setShowCompose(false);
                      }}
                      className={`w-full px-4 py-3 text-left transition-colors hover:bg-gray-50 ${
                        selectedMessage?.id === msg.id ? "bg-healthos-50" : ""
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {!msg.is_read && (
                          <span className="h-2 w-2 shrink-0 rounded-full bg-healthos-600" />
                        )}
                        <p
                          className={`truncate text-sm ${
                            msg.is_read
                              ? "font-normal text-gray-700"
                              : "font-semibold text-gray-900"
                          }`}
                        >
                          {msg.subject}
                        </p>
                      </div>
                      <p className="mt-0.5 truncate text-xs text-gray-500">
                        {msg.sender_type === "provider"
                          ? msg.sender_name
                          : "You"}{" "}
                        &middot;{" "}
                        {new Date(msg.created_at).toLocaleDateString()}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Message detail */}
        <div className="lg:col-span-2">
          {selectedMessage ? (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-4 border-b border-gray-100 pb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  {selectedMessage.subject}
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  From:{" "}
                  <span className="font-medium text-gray-700">
                    {selectedMessage.sender_type === "provider"
                      ? selectedMessage.sender_name
                      : "You"}
                  </span>{" "}
                  &middot;{" "}
                  {new Date(selectedMessage.created_at).toLocaleString()}
                </p>
              </div>
              <div className="prose prose-sm max-w-none text-gray-700">
                <p className="whitespace-pre-wrap">{selectedMessage.body}</p>
              </div>
              <div className="mt-6 border-t border-gray-100 pt-4">
                <button
                  onClick={() => setShowCompose(true)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Reply
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 py-20">
              <p className="text-sm text-gray-400">
                Select a message to read, or compose a new one.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Compose Form ─────────────────────────────────────────────────────────────

function ComposeForm({
  onClose,
  onSent,
}: {
  onClose: () => void;
  onSent: () => void;
}) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) return;
    setSending(true);
    setSendError(null);
    try {
      await sendMessage({ subject: subject.trim(), body: body.trim() });
      onSent();
    } catch (err: unknown) {
      setSendError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="rounded-xl border border-healthos-200 bg-healthos-50 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Compose Message
        </h3>
        <button
          onClick={onClose}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            To
          </label>
          <input
            type="text"
            value="Care Team"
            disabled
            className="mt-1 block w-full rounded-lg border border-gray-300 bg-gray-100 px-3 py-2 text-sm text-gray-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Subject
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Message subject..."
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Message
          </label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={5}
            placeholder="Type your message..."
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            required
          />
        </div>
        {sendError && <p className="text-sm text-red-600">{sendError}</p>}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Discard
          </button>
          <button
            type="submit"
            disabled={sending}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50"
          >
            {sending ? "Sending..." : "Send Message"}
          </button>
        </div>
      </form>
    </div>
  );
}
