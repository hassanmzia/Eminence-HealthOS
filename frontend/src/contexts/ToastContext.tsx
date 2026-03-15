"use client";

import { createContext, useContext, useCallback, useState, useEffect, useRef } from "react";

export type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
}

interface ToastContextValue {
  toasts: Toast[];
  toast: (message: string, type?: ToastType, duration?: number) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toasts: [],
  toast: () => {},
  success: () => {},
  error: () => {},
  info: () => {},
  warning: () => {},
  dismiss: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

const ICONS: Record<ToastType, string> = {
  success: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  error: "M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z",
  info: "M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z",
  warning: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
};

const COLORS: Record<ToastType, { bg: string; border: string; icon: string; text: string }> = {
  success: { bg: "bg-emerald-50 dark:bg-emerald-950/80", border: "border-emerald-200 dark:border-emerald-800", icon: "text-emerald-500", text: "text-emerald-800 dark:text-emerald-300" },
  error: { bg: "bg-red-50 dark:bg-red-950/80", border: "border-red-200 dark:border-red-800", icon: "text-red-500", text: "text-red-800 dark:text-red-300" },
  info: { bg: "bg-blue-50 dark:bg-blue-950/80", border: "border-blue-200 dark:border-blue-800", icon: "text-blue-500", text: "text-blue-800 dark:text-blue-300" },
  warning: { bg: "bg-amber-50 dark:bg-amber-950/80", border: "border-amber-200 dark:border-amber-800", icon: "text-amber-500", text: "text-amber-800 dark:text-amber-300" },
};

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [exiting, setExiting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    timerRef.current = setTimeout(() => {
      setExiting(true);
      setTimeout(() => onDismiss(toast.id), 300);
    }, toast.duration);
    return () => clearTimeout(timerRef.current);
  }, [toast.id, toast.duration, onDismiss]);

  const c = COLORS[toast.type];
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border ${c.bg} ${c.border} px-4 py-3 shadow-lg transition-all duration-300 ${
        exiting ? "translate-x-full opacity-0" : "animate-slide-in-left"
      }`}
    >
      <svg className={`h-5 w-5 flex-shrink-0 ${c.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d={ICONS[toast.type]} />
      </svg>
      <p className={`text-sm font-medium ${c.text}`}>{toast.message}</p>
      <button
        onClick={() => { setExiting(true); setTimeout(() => onDismiss(toast.id), 300); }}
        className="ml-auto flex-shrink-0 rounded p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType = "info", duration = 4000) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev.slice(-4), { id, message, type, duration }]);
  }, []);

  const success = useCallback((m: string) => addToast(m, "success"), [addToast]);
  const error = useCallback((m: string) => addToast(m, "error", 6000), [addToast]);
  const info = useCallback((m: string) => addToast(m, "info"), [addToast]);
  const warning = useCallback((m: string) => addToast(m, "warning", 5000), [addToast]);

  return (
    <ToastContext.Provider value={{ toasts, toast: addToast, success, error, info, warning, dismiss }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 sm:bottom-6 sm:right-6">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
