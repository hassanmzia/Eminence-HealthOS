"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  fetchInbox,
  fetchSentMessages,
  fetchMessageThread,
  sendSecureMessage,
  markMessageRead,
  fetchNotifications,
  fetchUnreadNotificationCount,
  type MessageResponse,
} from "@/lib/platform-api";

/* ── Types ─────────────────────────────────────────────────────────────────── */

type FilterTab = "all" | "unread" | "flagged" | "urgent";
type Priority = "normal" | "urgent";
type Category = "clinical" | "admin" | "referral";
type Status = "online" | "away" | "offline";
type Role = "Physician" | "Nurse" | "Admin" | "Patient";
type AttachmentType = "document" | "image" | "lab_result";

interface Attachment {
  name: string;
  type: AttachmentType;
  size: string;
}

interface Message {
  id: string;
  senderId: string;
  senderName: string;
  content: string;
  timestamp: string;
  isRead: boolean;
  attachments?: Attachment[];
}

interface Conversation {
  id: string;
  participantName: string;
  participantInitial: string;
  participantRole: Role;
  participantStatus: Status;
  lastMessage: string;
  lastMessageAt: string;
  unreadCount: number;
  priority: Priority;
  category: Category;
  isFlagged: boolean;
}

interface Recipient {
  id: string;
  name: string;
  role: Role;
  department: string;
}

/* ── Demo Data ─────────────────────────────────────────────────────────────── */

const CURRENT_USER_ID = "me";

const demoRecipients: Recipient[] = [
  { id: "u1", name: "Dr. Sarah Williams", role: "Physician", department: "Internal Medicine" },
  { id: "u2", name: "Nurse Rachel Adams", role: "Nurse", department: "ICU" },
  { id: "u3", name: "Dr. Michael Patel", role: "Physician", department: "Endocrinology" },
  { id: "u4", name: "James Carter", role: "Admin", department: "Administration" },
  { id: "u5", name: "Dr. Emily Tran", role: "Physician", department: "Cardiology" },
  { id: "u6", name: "Maria Lopez", role: "Patient", department: "N/A" },
  { id: "u7", name: "Nurse Kevin Okafor", role: "Nurse", department: "Oncology" },
];

const demoConversations: Conversation[] = [
  {
    id: "c1",
    participantName: "Dr. Sarah Williams",
    participantInitial: "SW",
    participantRole: "Physician",
    participantStatus: "online",
    lastMessage: "The eGFR is trending down. Can we discuss adjusting the medication regimen?",
    lastMessageAt: "10 min ago",
    unreadCount: 2,
    priority: "urgent",
    category: "clinical",
    isFlagged: false,
  },
  {
    id: "c2",
    participantName: "Nurse Rachel Adams",
    participantInitial: "RA",
    participantRole: "Nurse",
    participantStatus: "online",
    lastMessage: "Vitals for all morning rounds have been recorded and uploaded.",
    lastMessageAt: "25 min ago",
    unreadCount: 0,
    priority: "normal",
    category: "clinical",
    isFlagged: true,
  },
  {
    id: "c3",
    participantName: "Dr. Michael Patel",
    participantInitial: "MP",
    participantRole: "Physician",
    participantStatus: "away",
    lastMessage: "A1C results came back at 8.2%. We need a care plan review for Mrs. Johnson.",
    lastMessageAt: "1h ago",
    unreadCount: 1,
    priority: "normal",
    category: "referral",
    isFlagged: false,
  },
  {
    id: "c4",
    participantName: "James Carter",
    participantInitial: "JC",
    participantRole: "Admin",
    participantStatus: "offline",
    lastMessage: "Prior authorization for MRI has been approved. Documentation attached.",
    lastMessageAt: "2h ago",
    unreadCount: 0,
    priority: "normal",
    category: "admin",
    isFlagged: false,
  },
  {
    id: "c5",
    participantName: "Dr. Emily Tran",
    participantInitial: "ET",
    participantRole: "Physician",
    participantStatus: "online",
    lastMessage: "Cardiology consult report for patient Rodriguez is ready for your review.",
    lastMessageAt: "3h ago",
    unreadCount: 3,
    priority: "urgent",
    category: "referral",
    isFlagged: true,
  },
  {
    id: "c6",
    participantName: "Maria Lopez",
    participantInitial: "ML",
    participantRole: "Patient",
    participantStatus: "offline",
    lastMessage: "Thank you, Doctor. I will schedule the follow-up appointment this week.",
    lastMessageAt: "5h ago",
    unreadCount: 0,
    priority: "normal",
    category: "clinical",
    isFlagged: false,
  },
];

const demoMessages: Record<string, Message[]> = {
  c1: [
    { id: "m1", senderId: "u1", senderName: "Dr. Sarah Williams", content: "Good morning. I noticed Mrs. Santos had elevated BP during the night shift. Can you check on her?", timestamp: "8:15 AM", isRead: true },
    { id: "m2", senderId: CURRENT_USER_ID, senderName: "You", content: "Yes, I will check on her during morning rounds. Her medication may need adjustment.", timestamp: "8:30 AM", isRead: true },
    { id: "m3", senderId: "u1", senderName: "Dr. Sarah Williams", content: "Good idea. Please also order a STAT BMP if BP remains above 150/95.", timestamp: "8:35 AM", isRead: true },
    { id: "m4", senderId: CURRENT_USER_ID, senderName: "You", content: "Will do. Her latest vitals show 148/92. I will recheck in 30 minutes.", timestamp: "9:00 AM", isRead: true, attachments: [{ name: "vitals_santos_0315.pdf", type: "document", size: "124 KB" }] },
    { id: "m5", senderId: "u1", senderName: "Dr. Sarah Williams", content: "Please review the latest lab results for the patient in room 302. I have attached the panel.", timestamp: "9:45 AM", isRead: false, attachments: [{ name: "lab_panel_302.pdf", type: "lab_result", size: "256 KB" }] },
    { id: "m6", senderId: "u1", senderName: "Dr. Sarah Williams", content: "The eGFR is trending down. Can we discuss adjusting the medication regimen?", timestamp: "9:46 AM", isRead: false },
  ],
  c2: [
    { id: "m7", senderId: "u2", senderName: "Nurse Rachel Adams", content: "Morning rounds vitals are all recorded. Room 301-310 complete.", timestamp: "7:00 AM", isRead: true },
    { id: "m8", senderId: CURRENT_USER_ID, senderName: "You", content: "Great, thank you. Any notable changes from yesterday?", timestamp: "7:15 AM", isRead: true },
    { id: "m9", senderId: "u2", senderName: "Nurse Rachel Adams", content: "Room 305 (Mr. Kim) oxygen sat dropped to 91%. I increased supplemental O2 to 3L.", timestamp: "7:20 AM", isRead: true },
    { id: "m10", senderId: CURRENT_USER_ID, senderName: "You", content: "Good catch. Please keep monitoring every 30 minutes and page me if it drops below 90%.", timestamp: "7:30 AM", isRead: true },
    { id: "m11", senderId: "u2", senderName: "Nurse Rachel Adams", content: "Vitals for all morning rounds have been recorded and uploaded.", timestamp: "8:35 AM", isRead: true, attachments: [{ name: "morning_vitals_report.pdf", type: "document", size: "340 KB" }] },
  ],
  c3: [
    { id: "m12", senderId: "u3", senderName: "Dr. Michael Patel", content: "Mrs. Johnson's A1C results just came back. I would like to coordinate on her diabetes management.", timestamp: "10:00 AM", isRead: true },
    { id: "m13", senderId: CURRENT_USER_ID, senderName: "You", content: "What were the results? She was on metformin 1000mg BID.", timestamp: "10:10 AM", isRead: true },
    { id: "m14", senderId: "u3", senderName: "Dr. Michael Patel", content: "A1C results came back at 8.2%. We need a care plan review for Mrs. Johnson.", timestamp: "10:15 AM", isRead: false, attachments: [{ name: "a1c_johnson_results.pdf", type: "lab_result", size: "178 KB" }, { name: "diabetes_care_plan.docx", type: "document", size: "92 KB" }] },
  ],
  c4: [
    { id: "m15", senderId: "u4", senderName: "James Carter", content: "The prior authorization request for the lumbar MRI (patient Hernandez) has been submitted.", timestamp: "1:00 PM", isRead: true },
    { id: "m16", senderId: CURRENT_USER_ID, senderName: "You", content: "Thanks, James. How long do we expect for turnaround?", timestamp: "1:15 PM", isRead: true },
    { id: "m17", senderId: "u4", senderName: "James Carter", content: "Typically 48 hours, but I flagged it as urgent given the clinical presentation.", timestamp: "1:20 PM", isRead: true },
    { id: "m18", senderId: "u4", senderName: "James Carter", content: "Prior authorization for MRI has been approved. Documentation attached.", timestamp: "2:30 PM", isRead: true, attachments: [{ name: "prior_auth_approval.pdf", type: "document", size: "210 KB" }] },
  ],
  c5: [
    { id: "m19", senderId: "u5", senderName: "Dr. Emily Tran", content: "I completed the cardiology consult for patient Rodriguez. Echo shows reduced EF at 35%.", timestamp: "11:00 AM", isRead: true },
    { id: "m20", senderId: CURRENT_USER_ID, senderName: "You", content: "That is concerning. What are your recommendations?", timestamp: "11:15 AM", isRead: true },
    { id: "m21", senderId: "u5", senderName: "Dr. Emily Tran", content: "Recommend starting ACE inhibitor and scheduling follow-up echo in 3 months. Full report attached.", timestamp: "11:20 AM", isRead: false, attachments: [{ name: "echo_rodriguez.pdf", type: "lab_result", size: "512 KB" }, { name: "cardiology_consult.pdf", type: "document", size: "320 KB" }] },
    { id: "m22", senderId: "u5", senderName: "Dr. Emily Tran", content: "Also want to flag: the patient reported occasional chest pain during exertion. We should monitor closely.", timestamp: "11:25 AM", isRead: false },
    { id: "m23", senderId: "u5", senderName: "Dr. Emily Tran", content: "Cardiology consult report for patient Rodriguez is ready for your review.", timestamp: "11:30 AM", isRead: false },
  ],
  c6: [
    { id: "m24", senderId: CURRENT_USER_ID, senderName: "You", content: "Hi Maria, your recent bloodwork results look good. Cholesterol is within normal range now.", timestamp: "2:00 PM", isRead: true },
    { id: "m25", senderId: "u6", senderName: "Maria Lopez", content: "That is wonderful news! The dietary changes must be working.", timestamp: "3:00 PM", isRead: true },
    { id: "m26", senderId: CURRENT_USER_ID, senderName: "You", content: "They certainly are. I would like to see you again in 3 months to re-evaluate. Please schedule at your convenience.", timestamp: "3:10 PM", isRead: true },
    { id: "m27", senderId: "u6", senderName: "Maria Lopez", content: "Thank you, Doctor. I will schedule the follow-up appointment this week.", timestamp: "3:30 PM", isRead: true },
  ],
};

/* ── Helpers ───────────────────────────────────────────────────────────────── */

const roleBadgeColor: Record<Role, string> = {
  Physician: "bg-blue-100 text-blue-700",
  Nurse: "bg-green-100 text-green-700",
  Admin: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300",
  Patient: "bg-orange-100 text-orange-700",
};

const categoryBadge: Record<Category, { label: string; cls: string }> = {
  clinical: { label: "Clinical", cls: "bg-blue-100 text-blue-700" },
  admin: { label: "Admin", cls: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400" },
  referral: { label: "Referral", cls: "bg-green-100 text-green-700" },
};

const statusDot: Record<Status, string> = {
  online: "bg-green-500",
  away: "bg-yellow-400",
  offline: "bg-gray-300",
};

const attachmentIcon: Record<AttachmentType, string> = {
  document: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  image: "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z",
  lab_result: "M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z",
};

/* ── Page Component ────────────────────────────────────────────────────────── */

export default function SecureMessagingPage() {
  const [conversations, setConversations] = useState<Conversation[]>(demoConversations);
  const [messages, setMessages] = useState<Record<string, Message[]>>(demoMessages);
  const [selectedId, setSelectedId] = useState<string | null>("c1");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterTab, setFilterTab] = useState<FilterTab>("all");
  const [newMessage, setNewMessage] = useState("");
  const [showNewModal, setShowNewModal] = useState(false);
  const [recipientSearch, setRecipientSearch] = useState("");
  const [modalRecipient, setModalRecipient] = useState<Recipient | null>(null);
  const [modalSubject, setModalSubject] = useState("");
  const [modalPriority, setModalPriority] = useState<Priority>("normal");
  const [modalBody, setModalBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selected = conversations.find((c) => c.id === selectedId) ?? null;
  const messageList = selectedId ? messages[selectedId] ?? [] : [];

  const totalUnread = conversations.reduce((sum, c) => sum + c.unreadCount, 0);

  // ── Load real data from /messaging/* API (falls back to demo data on error) ──
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [inbox, sent] = await Promise.all([fetchInbox(1, 50), fetchSentMessages(1, 50)]);
        if (cancelled) return;

        // Group messages by thread (using parent_message_id or sender/recipient pair)
        const threadMap = new Map<string, MessageResponse[]>();
        for (const msg of [...inbox, ...sent]) {
          const threadKey = msg.parent_message_id ?? msg.id;
          const existing = threadMap.get(threadKey) ?? [];
          existing.push(msg);
          threadMap.set(threadKey, existing);
        }

        const convList: Conversation[] = [];
        const msgMap: Record<string, Message[]> = {};

        threadMap.forEach((threadMsgs, threadId) => {
          threadMsgs.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
          const last = threadMsgs[threadMsgs.length - 1];
          const unread = threadMsgs.filter((m) => !m.is_read && m.sender_id !== "me").length;
          const partnerId = last.sender_id === "me" ? last.recipient_id : last.sender_id;

          convList.push({
            id: threadId,
            participantName: partnerId.slice(0, 8),
            participantInitial: partnerId.slice(0, 2).toUpperCase(),
            participantRole: "Physician" as Role,
            participantStatus: "online" as Status,
            lastMessage: last.body.slice(0, 100),
            lastMessageAt: new Date(last.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            unreadCount: unread,
            priority: "normal" as Priority,
            category: "clinical" as Category,
            isFlagged: false,
          });

          msgMap[threadId] = threadMsgs.map((m) => ({
            id: m.id,
            senderId: m.sender_id,
            senderName: m.sender_id === "me" ? "You" : m.sender_id.slice(0, 8),
            content: m.subject ? `[${m.subject}] ${m.body}` : m.body,
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            isRead: m.is_read,
          }));
        });

        if (convList.length > 0) {
          setConversations(convList);
          setMessages(msgMap);
          setSelectedId(convList[0].id);
        }
      } catch {
        // API unavailable — keep demo data
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messageList.length]);

  /* ── Select conversation & mark as read ── */

  const selectConversation = useCallback(
    (convId: string) => {
      setSelectedId(convId);

      // Attempt to fetch full thread from API
      fetchMessageThread(convId)
        .then((threadMsgs) => {
          if (threadMsgs.length > 0) {
            setMessages((prev) => ({
              ...prev,
              [convId]: threadMsgs.map((m) => ({
                id: m.id,
                senderId: m.sender_id,
                senderName: m.sender_id === "me" ? "You" : m.sender_id.slice(0, 8),
                content: m.subject ? `[${m.subject}] ${m.body}` : m.body,
                timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                isRead: m.is_read,
              })),
            }));
          }
        })
        .catch(() => {
          /* offline/demo — keep existing local messages */
        });

      const conv = conversations.find((c) => c.id === convId);
      if (conv && conv.unreadCount > 0) {
        // Mark unread messages in this thread as read via API
        const threadMessages = messages[convId] ?? [];
        const unreadIds = threadMessages
          .filter((m) => !m.isRead && m.senderId !== CURRENT_USER_ID)
          .map((m) => m.id);

        for (const msgId of unreadIds) {
          markMessageRead(msgId).catch(() => {
            /* offline/demo */
          });
        }

        // Optimistically update local state
        setConversations((prev) =>
          prev.map((c) => (c.id === convId ? { ...c, unreadCount: 0 } : c))
        );
        setMessages((prev) => ({
          ...prev,
          [convId]: (prev[convId] ?? []).map((m) => ({ ...m, isRead: true })),
        }));
      }
    },
    [conversations, messages],
  );

  /* ── Toggles ── */

  const toggleUrgent = () => {
    if (!selectedId) return;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === selectedId
          ? { ...c, priority: c.priority === "urgent" ? "normal" : "urgent" }
          : c
      )
    );
  };

  const toggleFlag = () => {
    if (!selectedId) return;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === selectedId ? { ...c, isFlagged: !c.isFlagged } : c
      )
    );
  };

  /* ── Send message ── */

  const handleSend = async () => {
    if (!newMessage.trim() || !selectedId || sending) return;
    setSending(true);
    const msg: Message = {
      id: `m-${Date.now()}`,
      senderId: CURRENT_USER_ID,
      senderName: "You",
      content: newMessage,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      isRead: true,
    };
    setMessages((prev) => ({
      ...prev,
      [selectedId]: [...(prev[selectedId] ?? []), msg],
    }));
    setConversations((prev) =>
      prev.map((c) =>
        c.id === selectedId
          ? { ...c, lastMessage: newMessage, lastMessageAt: "Just now" }
          : c
      )
    );
    const body = newMessage;
    setNewMessage("");

    // Fire-and-forget real API send
    try {
      const conv = conversations.find((c) => c.id === selectedId);
      if (conv) {
        await sendSecureMessage({
          recipient_id: conv.id,
          subject: "",
          body,
          parent_message_id: selectedId,
        });
      }
    } catch {
      // Offline/demo mode — message already shown locally
    } finally {
      setSending(false);
    }
  };

  /* ── New message modal send ── */

  const handleModalSend = async () => {
    if (!modalRecipient || !modalBody.trim() || sending) return;
    setSending(true);

    // Fire-and-forget real API send
    sendSecureMessage({
      recipient_id: modalRecipient.id,
      subject: modalSubject,
      body: modalBody,
    }).catch(() => { /* offline/demo */ });
    const newConvId = `c-${Date.now()}`;
    const newConv: Conversation = {
      id: newConvId,
      participantName: modalRecipient.name,
      participantInitial: modalRecipient.name.split(" ").map((w) => w[0]).join("").slice(0, 2),
      participantRole: modalRecipient.role,
      participantStatus: "online",
      lastMessage: modalBody.slice(0, 80),
      lastMessageAt: "Just now",
      unreadCount: 0,
      priority: modalPriority,
      category: "clinical",
      isFlagged: false,
    };
    const firstMsg: Message = {
      id: `m-${Date.now()}`,
      senderId: CURRENT_USER_ID,
      senderName: "You",
      content: modalSubject ? `[${modalSubject}] ${modalBody}` : modalBody,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      isRead: true,
    };
    setConversations((prev) => [newConv, ...prev]);
    setMessages((prev) => ({ ...prev, [newConvId]: [firstMsg] }));
    setSelectedId(newConvId);
    setShowNewModal(false);
    setRecipientSearch("");
    setModalRecipient(null);
    setModalSubject("");
    setModalPriority("normal");
    setModalBody("");
    setSending(false);
  };

  /* ── Filtering ── */

  const filteredConversations = conversations.filter((c) => {
    if (searchQuery && !c.participantName.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (filterTab === "unread" && c.unreadCount === 0) return false;
    if (filterTab === "flagged" && !c.isFlagged) return false;
    if (filterTab === "urgent" && c.priority !== "urgent") return false;
    return true;
  });

  const filteredRecipients = recipientSearch.length > 0
    ? demoRecipients.filter(
        (r) =>
          r.name.toLowerCase().includes(recipientSearch.toLowerCase()) ||
          r.role.toLowerCase().includes(recipientSearch.toLowerCase()) ||
          r.department.toLowerCase().includes(recipientSearch.toLowerCase())
      )
    : [];

  const filterTabs: { key: FilterTab; label: string }[] = [
    { key: "all", label: "All" },
    { key: "unread", label: "Unread" },
    { key: "flagged", label: "Flagged" },
    { key: "urgent", label: "Urgent" },
  ];

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col animate-fade-in-up">
      {/* ── Header ── */}
      <div className="px-3 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 sm:gap-4 min-w-0">
          {/* Mobile back button when viewing conversation */}
          {selectedId && (
            <button
              onClick={() => setSelectedId(null)}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 md:hidden"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
              </svg>
            </button>
          )}
          <div className="hidden sm:flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-healthos-100">
            <svg className="w-5 h-5 text-healthos-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 sm:gap-3">
              <h1 className="text-base sm:text-xl font-bold text-gray-900 dark:text-gray-100 truncate">Secure Messaging</h1>
              {totalUnread > 0 && (
                <span className="relative flex h-5 sm:h-6 min-w-[20px] sm:min-w-[24px] items-center justify-center rounded-full bg-red-500 px-1.5 sm:px-2 text-[10px] sm:text-xs font-bold text-white flex-shrink-0">
                  {totalUnread}
                  <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-40" />
                </span>
              )}
            </div>
            <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 hidden xs:block">HIPAA-compliant clinical communications</p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-green-50 border border-green-200 px-3 py-1 text-xs font-medium text-green-700">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            HIPAA Compliant
          </span>
          <button
            onClick={() => setShowNewModal(true)}
            className="rounded-lg bg-healthos-600 px-3 sm:px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span className="hidden sm:inline">New Message</span>
          </button>
        </div>
      </div>

      {/* ── Split Layout ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Left Sidebar (hidden on mobile when conversation selected) */}
        <div className={`${selectedId ? 'hidden md:flex' : 'flex'} w-full md:w-1/3 md:max-w-md md:min-w-[280px] border-r border-gray-200 dark:border-gray-700 flex-col bg-white dark:bg-gray-900`}>
          {/* Search */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
              />
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex border-b border-gray-200 dark:border-gray-700 px-3">
            {filterTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilterTab(tab.key)}
                className={`flex-1 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                  filterTab === tab.key
                    ? "border-healthos-600 text-healthos-600"
                    : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="p-6 text-center">
                <div className="inline-block w-6 h-6 border-2 border-healthos-600 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading messages...</p>
              </div>
            )}
            {!loading && filteredConversations.length === 0 && (
              <div className="p-6 text-center text-sm text-gray-500 dark:text-gray-400">No conversations found.</div>
            )}
            {filteredConversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                className={`w-full text-left p-4 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                  selectedId === conv.id ? "bg-healthos-50 border-l-[3px] border-l-healthos-500" : ""
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Avatar */}
                  <div className="relative flex-shrink-0">
                    <div className="w-10 h-10 rounded-full bg-healthos-100 flex items-center justify-center text-sm font-semibold text-healthos-700">
                      {conv.participantInitial}
                    </div>
                    {conv.priority === "urgent" && (
                      <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-red-500 rounded-full border-2 border-white" />
                    )}
                  </div>
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className={`text-sm truncate ${conv.unreadCount > 0 ? "font-bold text-gray-900 dark:text-gray-100" : "font-medium text-gray-700 dark:text-gray-300"}`}>
                        {conv.participantName}
                      </p>
                      <span className="text-[11px] text-gray-500 dark:text-gray-400 whitespace-nowrap">{conv.lastMessageAt}</span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className={`inline-block rounded px-1.5 py-0.5 text-[11px] font-medium ${categoryBadge[conv.category].cls}`}>
                        {categoryBadge[conv.category].label}
                      </span>
                      {conv.isFlagged && (
                        <svg className="w-3 h-3 text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M5 5a2 2 0 012-2h10l-3 7 3 7H7a2 2 0 01-2-2V5z" />
                        </svg>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-1">{conv.lastMessage}</p>
                  </div>
                  {/* Unread badge */}
                  {conv.unreadCount > 0 && (
                    <span className="flex-shrink-0 w-5 h-5 bg-healthos-600 text-white text-[11px] font-bold rounded-full flex items-center justify-center">
                      {conv.unreadCount}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Right Panel (Conversation) — full width on mobile */}
        <div className={`${selectedId ? 'flex' : 'hidden md:flex'} flex-1 flex-col bg-gray-50 dark:bg-gray-800 min-w-0`}>
          {selected ? (
            <>
              {/* Conversation Header */}
              <div className="px-3 sm:px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-full bg-healthos-100 flex items-center justify-center text-sm font-semibold text-healthos-700">
                      {selected.participantInitial}
                    </div>
                    <div className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white ${statusDot[selected.participantStatus]}`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-sm text-gray-900 dark:text-gray-100">{selected.participantName}</p>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${roleBadgeColor[selected.participantRole]}`}>
                        {selected.participantRole}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <div className={`w-2 h-2 rounded-full ${statusDot[selected.participantStatus]}`} />
                      <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">{selected.participantStatus}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={toggleUrgent}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium border transition-colors ${
                      selected.priority === "urgent"
                        ? "bg-red-50 border-red-200 text-red-700"
                        : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    <span className="flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                      {selected.priority === "urgent" ? "Urgent" : "Mark Urgent"}
                    </span>
                  </button>
                  <button
                    onClick={toggleFlag}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium border transition-colors ${
                      selected.isFlagged
                        ? "bg-yellow-50 border-yellow-200 text-yellow-700"
                        : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    <span className="flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill={selected.isFlagged ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10l-3 7 3 7H7a2 2 0 01-2-2V5z" />
                      </svg>
                      {selected.isFlagged ? "Flagged" : "Flag"}
                    </span>
                  </button>
                </div>
              </div>

              {/* Messages Thread */}
              <div className="flex-1 overflow-y-auto px-3 sm:px-6 py-3 sm:py-4 space-y-3 sm:space-y-4">
                {messageList.map((msg) => {
                  const isSelf = msg.senderId === CURRENT_USER_ID;
                  return (
                    <div key={msg.id} className={`flex ${isSelf ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[70%] ${isSelf ? "items-end" : "items-start"}`}>
                        <div
                          className={`rounded-2xl px-4 py-3 ${
                            isSelf
                              ? "bg-healthos-100 text-gray-900 dark:text-gray-100 rounded-br-md"
                              : "bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-bl-md"
                          }`}
                        >
                          {!isSelf && (
                            <p className="text-xs font-semibold text-healthos-700 mb-1">{msg.senderName}</p>
                          )}
                          <p className="text-sm leading-relaxed">{msg.content}</p>
                          {/* Attachments */}
                          {msg.attachments && msg.attachments.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-2">
                              {msg.attachments.map((att, i) => (
                                <span
                                  key={i}
                                  className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium ${
                                    isSelf ? "bg-healthos-200/60 text-healthos-800" : "bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300"
                                  }`}
                                >
                                  <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d={attachmentIcon[att.type]} />
                                  </svg>
                                  <span className="truncate max-w-[120px]">{att.name}</span>
                                  <span className="text-[11px] opacity-60">{att.size}</span>
                                  <button className="ml-1 opacity-60 hover:opacity-100">
                                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                  </button>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        {/* Timestamp + read receipt */}
                        <div className={`flex items-center gap-1.5 mt-1 px-1 ${isSelf ? "justify-end" : "justify-start"}`}>
                          <span className="text-[11px] text-gray-500 dark:text-gray-400">{msg.timestamp}</span>
                          {isSelf && (
                            <svg className={`w-3 h-3 ${msg.isRead ? "text-healthos-500" : "text-gray-300"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d={msg.isRead ? "M5 13l4 4L19 7" : "M5 13l4 4L19 7"} />
                            </svg>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="px-3 sm:px-6 py-3 sm:py-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 safe-bottom">
                <div className="flex items-end gap-3">
                  <button className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-300 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 flex-shrink-0">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                    </svg>
                  </button>
                  <div className="flex-1 relative">
                    <textarea
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      placeholder="Type a secure message..."
                      rows={2}
                      maxLength={2000}
                      className="w-full px-4 py-2.5 text-sm bg-gray-50 dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none resize-none"
                    />
                    <span className="absolute bottom-2 right-3 text-[11px] text-gray-300">
                      {newMessage.length}/2000
                    </span>
                  </div>
                  <button
                    onClick={handleSend}
                    disabled={!newMessage.trim() || sending}
                    className="p-2.5 bg-healthos-600 text-white rounded-xl hover:bg-healthos-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                  >
                    {sending ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    )}
                  </button>
                </div>
                <div className="flex items-center justify-center gap-1.5 mt-2">
                  <svg className="w-3 h-3 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400">End-to-end encrypted &middot; HIPAA-compliant &middot; Audit logged</span>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
              <div className="text-center">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Select a conversation to start messaging</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Or create a new message using the button above</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── New Message Modal ── */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="card w-full max-w-lg mx-4 animate-fade-in-up">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">New Message</h2>
                <button
                  onClick={() => setShowNewModal(false)}
                  className="p-1 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Recipient Search */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">To</label>
                {modalRecipient ? (
                  <div className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${roleBadgeColor[modalRecipient.role]}`}>
                      {modalRecipient.role}
                    </span>
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{modalRecipient.name}</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">{modalRecipient.department}</span>
                    <button onClick={() => setModalRecipient(null)} className="ml-auto text-gray-500 dark:text-gray-400 hover:text-gray-600">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search by name, role, or department..."
                      value={recipientSearch}
                      onChange={(e) => setRecipientSearch(e.target.value)}
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
                    />
                    {filteredRecipients.length > 0 && (
                      <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg max-h-48 overflow-y-auto">
                        {filteredRecipients.map((r) => (
                          <button
                            key={r.id}
                            onClick={() => {
                              setModalRecipient(r);
                              setRecipientSearch("");
                            }}
                            className="w-full text-left px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center gap-2 text-sm"
                          >
                            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${roleBadgeColor[r.role]}`}>
                              {r.role}
                            </span>
                            <span className="font-medium">{r.name}</span>
                            <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">{r.department}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Subject */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Subject</label>
                <input
                  type="text"
                  placeholder="Message subject (optional)"
                  value={modalSubject}
                  onChange={(e) => setModalSubject(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none"
                />
              </div>

              {/* Priority */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setModalPriority("normal")}
                    className={`rounded-lg px-4 py-2 text-sm font-medium border transition-colors ${
                      modalPriority === "normal"
                        ? "bg-healthos-50 border-healthos-300 text-healthos-700"
                        : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    Normal
                  </button>
                  <button
                    onClick={() => setModalPriority("urgent")}
                    className={`rounded-lg px-4 py-2 text-sm font-medium border transition-colors ${
                      modalPriority === "urgent"
                        ? "bg-red-50 border-red-300 text-red-700"
                        : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                    }`}
                  >
                    Urgent
                  </button>
                </div>
              </div>

              {/* Message Body */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Message</label>
                <textarea
                  placeholder="Type your message..."
                  rows={5}
                  maxLength={2000}
                  value={modalBody}
                  onChange={(e) => setModalBody(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm focus:border-healthos-500 focus:ring-1 focus:ring-healthos-500 outline-none resize-none"
                />
                <p className="text-[11px] text-gray-500 dark:text-gray-400 text-right mt-1">{modalBody.length}/2000</p>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between">
                <button className="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                  Attach Files
                </button>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowNewModal(false)}
                    className="rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleModalSend}
                    disabled={!modalRecipient || !modalBody.trim() || sending}
                    className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white hover:bg-healthos-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {sending && (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    )}
                    {sending ? "Sending..." : "Send Message"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
