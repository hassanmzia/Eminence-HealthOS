"use client";

import { useState } from "react";
import {
  MessageSquare,
  Send,
  Search,
  Paperclip,
  User,
  Clock,
  ChevronRight,
} from "lucide-react";
import clsx from "clsx";

/* ── Types ─────────────────────────────────────────────────────────────────── */

interface MessageThread {
  id: string;
  participant_name: string;
  participant_role: string;
  participant_id: string;
  last_message: string;
  last_message_at: string;
  unread_count: number;
  is_online: boolean;
}

interface Message {
  id: string;
  sender_id: string;
  sender_name: string;
  sender_role: string;
  content: string;
  timestamp: string;
  is_read: boolean;
  attachments?: { name: string; url: string }[];
}

/* ── Placeholder data ──────────────────────────────────────────────────────── */

const placeholderThreads: MessageThread[] = [
  { id: "t1", participant_name: "Dr. Sarah Williams", participant_role: "physician", participant_id: "u1", last_message: "Please review the latest lab results for the patient in room 302.", last_message_at: "10 min ago", unread_count: 2, is_online: true },
  { id: "t2", participant_name: "Nurse Rachel Adams", participant_role: "nurse", participant_id: "u2", last_message: "Vitals have been recorded for all morning rounds.", last_message_at: "25 min ago", unread_count: 0, is_online: true },
  { id: "t3", participant_name: "Dr. Michael Patel", participant_role: "physician", participant_id: "u3", last_message: "The A1C results came back. Can we schedule a care plan review?", last_message_at: "1h ago", unread_count: 1, is_online: false },
  { id: "t4", participant_name: "PharmD Lisa Chen", participant_role: "pharmacist", participant_id: "u4", last_message: "Drug interaction alert has been reviewed and cleared.", last_message_at: "2h ago", unread_count: 0, is_online: false },
  { id: "t5", participant_name: "Care Coord. John Davis", participant_role: "nurse", participant_id: "u5", last_message: "Discharge planning documents are ready for review.", last_message_at: "3h ago", unread_count: 0, is_online: true },
];

const initialMessages: Record<string, Message[]> = {
  t1: [
    { id: "m1", sender_id: "u1", sender_name: "Dr. Sarah Williams", sender_role: "physician", content: "Good morning. I noticed Mrs. Santos BP was elevated during the night shift. Can you check on her?", timestamp: "8:15 AM", is_read: true },
    { id: "m2", sender_id: "me", sender_name: "You", sender_role: "self", content: "Yes, I will check on her during morning rounds. Her medication may need adjustment.", timestamp: "8:30 AM", is_read: true },
    { id: "m3", sender_id: "u1", sender_name: "Dr. Sarah Williams", sender_role: "physician", content: "Good idea. Also, please order a STAT BMP if the BP remains above 150/95.", timestamp: "8:35 AM", is_read: true },
    { id: "m4", sender_id: "me", sender_name: "You", sender_role: "self", content: "Will do. Her latest vitals show 148/92. I will recheck in 30 minutes.", timestamp: "9:00 AM", is_read: true },
    { id: "m5", sender_id: "u1", sender_name: "Dr. Sarah Williams", sender_role: "physician", content: "Please review the latest lab results for the patient in room 302.", timestamp: "9:45 AM", is_read: false },
    { id: "m6", sender_id: "u1", sender_name: "Dr. Sarah Williams", sender_role: "physician", content: "The AI agent flagged a potential kidney function concern. eGFR trending down.", timestamp: "9:46 AM", is_read: false },
  ],
};

const roleColors: Record<string, string> = {
  physician: "text-blue-600",
  nurse: "text-green-600",
  pharmacist: "text-purple-600",
  patient: "text-orange-600",
  admin: "text-gray-600",
};

/* ── Page Component ────────────────────────────────────────────────────────── */

export default function SecureMessagingPage() {
  const [selectedThread, setSelectedThread] = useState<string | null>("t1");
  const [newMessage, setNewMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [localMessages, setLocalMessages] = useState<Record<string, Message[]>>(initialMessages);

  const threadList = placeholderThreads;
  const messageList = selectedThread ? localMessages[selectedThread] ?? [] : [];
  const selectedThreadData = threadList.find((t) => t.id === selectedThread);

  const filteredThreads = searchQuery
    ? threadList.filter((t) =>
        t.participant_name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : threadList;

  const handleSend = () => {
    if (!newMessage.trim() || !selectedThread) return;
    const newMsg: Message = {
      id: `m-${Date.now()}`,
      sender_id: "me",
      sender_name: "You",
      sender_role: "self",
      content: newMessage,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      is_read: true,
    };
    setLocalMessages((prev) => ({
      ...prev,
      [selectedThread]: [...(prev[selectedThread] ?? []), newMsg],
    }));
    setNewMessage("");
  };

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-white flex items-center gap-3">
        <MessageSquare className="w-6 h-6 text-indigo-600" />
        <div>
          <h1 className="text-lg font-bold text-gray-900">
            Secure Messaging
          </h1>
          <p className="text-xs text-gray-500">
            HIPAA-compliant care team communication
          </p>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Thread List */}
        <div className="w-80 border-r border-gray-200 flex flex-col bg-white">
          {/* Search */}
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm bg-gray-100 rounded-lg border-none focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>

          {/* Threads */}
          <div className="flex-1 overflow-y-auto">
            {filteredThreads.map((thread) => (
              <button
                key={thread.id}
                onClick={() => setSelectedThread(thread.id)}
                className={clsx(
                  "w-full text-left p-3 border-b border-gray-100 hover:bg-gray-50 transition-colors",
                  selectedThread === thread.id &&
                    "bg-indigo-50 border-l-2 border-l-indigo-500"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="relative flex-shrink-0">
                    <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                      <User className="w-5 h-5 text-gray-400" />
                    </div>
                    {thread.is_online && (
                      <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-sm truncate">
                        {thread.participant_name}
                      </p>
                      {thread.unread_count > 0 && (
                        <span className="w-5 h-5 bg-indigo-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center flex-shrink-0">
                          {thread.unread_count}
                        </span>
                      )}
                    </div>
                    <p
                      className={`text-xs ${roleColors[thread.participant_role] || "text-gray-500"}`}
                    >
                      {thread.participant_role}
                    </p>
                    <p className="text-xs text-gray-500 truncate mt-1">
                      {thread.last_message}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-0.5 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {thread.last_message_at}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Message Area */}
        <div className="flex-1 flex flex-col bg-gray-50">
          {selectedThread && selectedThreadData ? (
            <>
              {/* Thread Header */}
              <div className="p-4 border-b border-gray-200 bg-white flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                      <User className="w-5 h-5 text-gray-400" />
                    </div>
                    {selectedThreadData.is_online && (
                      <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold text-sm">
                      {selectedThreadData.participant_name}
                    </p>
                    <p
                      className={`text-xs ${roleColors[selectedThreadData.participant_role]}`}
                    >
                      {selectedThreadData.participant_role}{" "}
                      {selectedThreadData.is_online ? "- Online" : "- Offline"}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messageList.map((msg) => {
                  const isSelf = msg.sender_id === "me";
                  return (
                    <div
                      key={msg.id}
                      className={clsx(
                        "flex",
                        isSelf ? "justify-end" : "justify-start"
                      )}
                    >
                      <div
                        className={clsx(
                          "max-w-[70%] rounded-2xl px-4 py-2.5",
                          isSelf
                            ? "bg-indigo-600 text-white rounded-br-md"
                            : "bg-white border border-gray-200 rounded-bl-md"
                        )}
                      >
                        {!isSelf && (
                          <p
                            className={clsx(
                              "text-xs font-medium mb-1",
                              roleColors[msg.sender_role]
                            )}
                          >
                            {msg.sender_name}
                          </p>
                        )}
                        <p className="text-sm">{msg.content}</p>
                        <p
                          className={clsx(
                            "text-[10px] mt-1",
                            isSelf ? "text-indigo-200" : "text-gray-400"
                          )}
                        >
                          {msg.timestamp}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Input */}
              <div className="p-4 border-t border-gray-200 bg-white">
                <div className="flex items-center gap-2">
                  <button className="p-2 text-gray-400 hover:text-gray-700 transition-colors rounded-lg hover:bg-gray-100">
                    <Paperclip className="w-5 h-5" />
                  </button>
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={(e) =>
                      e.key === "Enter" && !e.shiftKey && handleSend()
                    }
                    placeholder="Type a message..."
                    className="flex-1 px-4 py-2.5 text-sm bg-gray-100 rounded-xl border-none focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!newMessage.trim()}
                    className="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-[10px] text-gray-400 mt-2 text-center">
                  Messages are encrypted end-to-end and HIPAA-compliant. All
                  communication is logged for audit purposes.
                </p>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">
                  Select a conversation to start messaging
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
