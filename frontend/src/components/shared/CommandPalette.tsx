"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";

interface SearchItem {
  id: string;
  label: string;
  description?: string;
  href: string;
  section: string;
  icon: string;
}

const SEARCH_ITEMS: SearchItem[] = [
  { id: "dashboard", label: "Dashboard", description: "Command center overview", href: "/dashboard", section: "Pages", icon: "M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6z" },
  { id: "patients", label: "Patients", description: "Patient management", href: "/patients", section: "Pages", icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952" },
  { id: "alerts", label: "Alerts", description: "Notifications & alerts", href: "/alerts", section: "Pages", icon: "M14.857 17.082a23.848 23.848 0 005.454-1.31" },
  { id: "rpm", label: "Remote Patient Monitoring", description: "RPM dashboard", href: "/rpm", section: "Clinical", icon: "M22 12h-4l-3 9L9 3l-3 9H2" },
  { id: "telehealth", label: "Telehealth", description: "Video visits", href: "/telehealth", section: "Clinical", icon: "m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38" },
  { id: "ambient", label: "Ambient AI", description: "Clinical documentation", href: "/ambient-ai", section: "Clinical", icon: "M12 18.75a6 6 0 006-6v-1.5" },
  { id: "pharmacy", label: "Pharmacy", description: "Medications & prescriptions", href: "/pharmacy", section: "Clinical", icon: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5" },
  { id: "labs", label: "Labs", description: "Lab orders & results", href: "/labs", section: "Clinical", icon: "M9.75 3.104v5.714" },
  { id: "imaging", label: "Imaging", description: "Medical imaging studies", href: "/imaging", section: "Clinical", icon: "M6.827 6.175A2.31 2.31 0 015.186 7.23" },
  { id: "mental", label: "Mental Health", description: "Behavioral health", href: "/mental-health", section: "Clinical", icon: "M21 8.25c0-2.485-2.099-4.5-4.688-4.5" },
  { id: "sdoh", label: "SDOH", description: "Social determinants", href: "/sdoh", section: "Clinical", icon: "m2.25 12 8.954-8.955" },
  { id: "rag", label: "Clinical RAG", description: "AI knowledge search", href: "/clinical-intelligence", section: "AI & Intelligence", icon: "m21 21-5.197-5.197" },
  { id: "kg", label: "Knowledge Graph", description: "Medical ontology", href: "/knowledge-graph", section: "AI & Intelligence", icon: "M7.5 14.25v2.25m3-4.5v4.5" },
  { id: "ml", label: "ML Models", description: "Machine learning models", href: "/ml-models", section: "AI & Intelligence", icon: "M9.813 15.904 9 18.75l-.813-2.846" },
  { id: "agents", label: "AI Orchestration", description: "Agent pipelines", href: "/agents", section: "AI & Intelligence", icon: "M9 3v2m6-2v2" },
  { id: "twin", label: "Digital Twin", description: "Patient simulation", href: "/digital-twin", section: "AI & Intelligence", icon: "M15.75 6a3.75 3.75 0 11-7.5 0" },
  { id: "fairness", label: "AI Fairness", description: "Bias monitoring", href: "/fairness", section: "AI & Intelligence", icon: "M12 3v17.25" },
  { id: "ops", label: "Operations", description: "Prior auth & scheduling", href: "/operations", section: "Operations", icon: "M9 5H7a2 2 0 00-2 2v12" },
  { id: "rcm", label: "Revenue Cycle", description: "Claims & billing", href: "/rcm", section: "Operations", icon: "M12 6v12m-3-2.818l.879.659" },
  { id: "analytics", label: "Analytics", description: "Reports & insights", href: "/analytics", section: "Operations", icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25" },
  { id: "compliance", label: "Compliance", description: "HIPAA & governance", href: "/compliance", section: "Operations", icon: "M9 12.75L11.25 15 15 9.75" },
  { id: "ehr", label: "EHR Connect", description: "FHIR integration", href: "/ehr-connect", section: "Operations", icon: "M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244" },
  { id: "research", label: "Research & Genomics", description: "Clinical trials", href: "/research-genomics", section: "Advanced", icon: "M9.75 3.104v5.714" },
  { id: "engage", label: "Patient Engagement", description: "Triage & navigation", href: "/patient-engagement", section: "Advanced", icon: "M15 19.128a9.38 9.38 0 002.625.372" },
  { id: "market", label: "Marketplace", description: "Agent store", href: "/marketplace", section: "Advanced", icon: "M13.5 21v-7.5a.75.75 0 01.75-.75h3" },
  { id: "sim", label: "Simulator", description: "Scenario testing", href: "/simulator", section: "Advanced", icon: "M9.75 3.104v5.714" },
  { id: "timeline", label: "Patient Timeline", description: "Chronological patient history", href: "/patient-timeline", section: "Pages", icon: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" },
  { id: "explain", label: "AI Explainability", description: "SHAP & LIME visualizations", href: "/ai-explainability", section: "AI & Intelligence", icon: "M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" },
  { id: "admin", label: "Admin (RBAC)", description: "Roles & permissions", href: "/admin", section: "Operations", icon: "M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" },
  { id: "audit", label: "Audit Log", description: "System activity log", href: "/audit-log", section: "Operations", icon: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Keyboard shortcut: Cmd+K or /
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const filtered = useMemo(() => {
    if (!query.trim()) return SEARCH_ITEMS;
    const q = query.toLowerCase();
    return SEARCH_ITEMS.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.description?.toLowerCase().includes(q) ||
        item.section.toLowerCase().includes(q)
    );
  }, [query]);

  const grouped = useMemo(() => {
    const groups: Record<string, SearchItem[]> = {};
    filtered.forEach((item) => {
      if (!groups[item.section]) groups[item.section] = [];
      groups[item.section].push(item);
    });
    return groups;
  }, [filtered]);

  const flatItems = useMemo(() => filtered, [filtered]);

  const navigate = useCallback(
    (item: SearchItem) => {
      setOpen(false);
      router.push(item.href);
    },
    [router]
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, flatItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && flatItems[selectedIndex]) {
      navigate(flatItems[selectedIndex]);
    }
  }

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current.querySelector(`[data-index="${selectedIndex}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex]);

  if (!open) return null;

  let flatIndex = -1;

  return (
    <div className="fixed inset-0 z-[90] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />

      {/* Modal */}
      <div className="relative w-full max-w-lg animate-slide-up rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-2xl">
        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-gray-200 dark:border-gray-700 px-4">
          <svg className="h-5 w-5 flex-shrink-0 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search pages, features, tools..."
            className="flex-1 bg-transparent py-4 text-sm text-gray-900 dark:text-gray-100 outline-none placeholder:text-gray-400"
          />
          <kbd className="rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-1.5 py-0.5 text-[11px] font-medium text-gray-500 dark:text-gray-400">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
          {flatItems.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
              No results for &ldquo;{query}&rdquo;
            </div>
          ) : (
            Object.entries(grouped).map(([section, items]) => (
              <div key={section} className="mb-2">
                <p className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {section}
                </p>
                {items.map((item) => {
                  flatIndex++;
                  const idx = flatIndex;
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={item.id}
                      data-index={idx}
                      onClick={() => navigate(item)}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                        isSelected
                          ? "bg-healthos-50 text-healthos-700 dark:bg-healthos-950/50 dark:text-healthos-400"
                          : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                      }`}
                    >
                      <svg className="h-4 w-4 flex-shrink-0 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                      </svg>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{item.label}</p>
                        {item.description && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{item.description}</p>
                        )}
                      </div>
                      {isSelected && (
                        <kbd className="text-[11px] text-gray-500 dark:text-gray-400">Enter</kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 border-t border-gray-200 dark:border-gray-700 px-4 py-2">
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-gray-400">
            <kbd className="rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-1 py-0.5">↑↓</kbd>
            <span>Navigate</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-gray-400">
            <kbd className="rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-1 py-0.5">↵</kbd>
            <span>Open</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-gray-400">
            <kbd className="rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-1.5 py-0.5">⌘K</kbd>
            <span>Toggle</span>
          </div>
        </div>
      </div>
    </div>
  );
}
