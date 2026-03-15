"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { fetchMyProfile, type UserProfile } from "@/lib/api";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Command Center",
  "/patients": "Patient Management",
  "/rpm": "Remote Patient Monitoring",
  "/telehealth": "Telehealth",
  "/operations": "Operations",
  "/analytics": "Analytics & Insights",
  "/ambient-ai": "Ambient AI",
  "/rcm": "Revenue Cycle",
  "/pharmacy": "Pharmacy",
  "/labs": "Lab Results",
  "/imaging": "Medical Imaging",
  "/patient-engagement": "Patient Engagement",
  "/digital-twin": "Digital Twin",
  "/research-genomics": "Research & Genomics",
  "/compliance": "Compliance",
  "/mental-health": "Mental Health",
  "/alerts": "Alerts & Notifications",
  "/agents": "AI Agents",
  "/profile": "My Profile",
};

export function TopBar({ onMenuToggle }: { onMenuToggle?: () => void } = {}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMyProfile().then(setUser).catch(() => {});
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    router.push("/login");
  }

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  const pageTitle = pathname ? PAGE_TITLES[Object.keys(PAGE_TITLES).find((k) => pathname.startsWith(k)) || ""] : "";

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200/80 bg-white/80 px-4 backdrop-blur-sm sm:px-6">
      <div className="flex items-center gap-3">
        {/* Mobile hamburger menu */}
        <button
          onClick={onMenuToggle}
          className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 lg:hidden"
          aria-label="Toggle sidebar"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>

        {/* Breadcrumb / Page title */}
        <div className="flex items-center gap-2">
          {pageTitle && (
            <h1 className="text-sm font-semibold text-gray-700">{pageTitle}</h1>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Search shortcut */}
        <button className="hidden items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm text-gray-400 transition-colors hover:bg-gray-100 sm:flex">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <span className="text-xs">Search...</span>
          <kbd className="rounded border border-gray-300 bg-white px-1.5 py-0.5 text-[10px] font-medium text-gray-500">/</kbd>
        </button>

        {/* Connection indicator */}
        <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 ring-1 ring-inset ring-emerald-500/20">
          <span className="status-dot-live" />
          <span className="hidden text-xs font-medium text-emerald-700 sm:inline">Connected</span>
        </div>

        {/* User avatar + dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 rounded-lg p-1.5 transition-all hover:bg-gray-100"
          >
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt="Avatar"
                className="h-8 w-8 rounded-full object-cover ring-2 ring-white"
              />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-healthos-400 to-healthos-600 text-xs font-bold text-white ring-2 ring-white">
                {initials}
              </div>
            )}
            <svg className={`h-3.5 w-3.5 text-gray-400 transition-transform ${dropdownOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full z-50 mt-2 w-64 animate-scale-in rounded-xl border border-gray-200/80 bg-white py-1 shadow-lg">
              {/* User info header */}
              <div className="border-b border-gray-100 px-4 py-3">
                <p className="text-sm font-semibold text-gray-900">{user?.full_name || "User"}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
                <span className="mt-1.5 inline-block rounded-full bg-healthos-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-healthos-700 ring-1 ring-inset ring-healthos-500/20">
                  {user?.role}
                </span>
              </div>

              {/* Menu items */}
              <div className="py-1">
                <button
                  onClick={() => { setDropdownOpen(false); router.push("/profile"); }}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 transition-colors hover:bg-gray-50"
                >
                  <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                  </svg>
                  My Profile
                </button>
                <button
                  onClick={() => { setDropdownOpen(false); router.push("/profile#security"); }}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 transition-colors hover:bg-gray-50"
                >
                  <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                  </svg>
                  Security Settings
                </button>
              </div>

              <div className="divider" />

              <div className="py-1">
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-600 transition-colors hover:bg-red-50"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                  </svg>
                  Log Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
