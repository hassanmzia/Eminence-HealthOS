"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { ToastProvider } from "@/contexts/ToastContext";
import { AuthProvider, useAuth, canAccessRoute } from "@/contexts/AuthContext";
import { CommandPalette } from "@/components/shared/CommandPalette";

const PUBLIC_ROUTES = ["/login", "/register"];

function RouteGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { role, loading, isPatient } = useAuth();

  // Still loading user data — show nothing yet
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
          <span className="text-sm text-gray-500 dark:text-gray-400">Loading...</span>
        </div>
      </div>
    );
  }

  // Patient users trying to access staff routes → redirect to patient portal
  if (isPatient && pathname && !pathname.startsWith("/patient-portal") && pathname !== "/messaging" && pathname !== "/profile") {
    if (typeof window !== "undefined") {
      router.replace("/patient-portal");
    }
    return null;
  }

  // Check route-level access
  if (role && pathname && !canAccessRoute(pathname, role)) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-50 dark:bg-red-950/30">
            <svg className="h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Access Denied</h2>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Your role <span className="font-semibold capitalize text-gray-700 dark:text-gray-300">{role?.replace("_", " ")}</span> does not have permission to access this page.
          </p>
          <button
            onClick={() => router.push("/dashboard")}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function AppShellInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_ROUTES.some((r) => pathname.startsWith(r));
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { loading } = useAuth();

  // Public routes: no shell (login, register)
  if (isPublic) {
    return <>{children}</>;
  }

  // Still loading — show centered spinner
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
          <span className="text-sm text-gray-500 dark:text-gray-400">Loading...</span>
        </div>
      </div>
    );
  }

  return (
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
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6">
          <RouteGuard>{children}</RouteGuard>
        </main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <AppShellInner>{children}</AppShellInner>
          <CommandPalette />
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
