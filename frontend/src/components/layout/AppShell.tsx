"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { ToastProvider } from "@/contexts/ToastContext";
import { CommandPalette } from "@/components/shared/CommandPalette";

const PUBLIC_ROUTES = ["/login", "/register", "/patient-portal"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_ROUTES.some((r) => pathname.startsWith(r));
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (isPublic) {
    return (
      <ThemeProvider>
        <ToastProvider>{children}</ToastProvider>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider>
      <ToastProvider>
        <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
          {/* Mobile sidebar overlay */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 z-40 bg-black/50 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          {/* Sidebar — hidden on mobile, always visible on lg+ */}
          <div
            className={`fixed inset-y-0 left-0 z-50 transform transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <Sidebar onNavigate={() => setSidebarOpen(false)} />
          </div>

          <div className="flex flex-1 flex-col overflow-hidden">
            <TopBar onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />
            <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
          </div>
        </div>

        {/* Global search palette */}
        <CommandPalette />
      </ToastProvider>
    </ThemeProvider>
  );
}
