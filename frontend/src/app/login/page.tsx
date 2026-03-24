"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth, type Role } from "@/contexts/AuthContext";

/** Return the correct landing page for each role. */
function getLandingPage(role: string): string {
  switch (role) {
    case "patient":
      return "/patient-portal";
    case "clinician":
      return "/clinical-workspace";
    case "office_admin":
      return "/operations";
    default:
      return "/dashboard";
  }
}

export default function LoginPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Invalid credentials");
        setLoading(false);
        return;
      }

      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      // Fetch user profile into AuthContext so role is available immediately
      await refreshUser();

      // Read the role from the JWT payload to determine landing page
      // (refreshUser populates the context, but we need the role for redirect)
      try {
        const payload = JSON.parse(atob(data.access_token.split(".")[1]));
        const landing = getLandingPage(payload.role || "");
        router.push(landing);
      } catch {
        router.push("/dashboard");
      }
    } catch {
      setError("Unable to connect to server");
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-md px-6">
        {/* Logo / Brand */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-healthos-600 text-xl font-bold text-white shadow-lg shadow-healthos-600/30">
            E
          </div>
          <h1 className="text-2xl font-bold text-white">Eminence HealthOS</h1>
          <p className="mt-1 text-sm text-slate-400">
            The AI Operating System for Digital Healthcare
          </p>
        </div>

        {/* Login card */}
        <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5 sm:p-8 shadow-xl backdrop-blur">
          <h2 className="mb-6 text-lg font-semibold text-white">Sign in to your account</h2>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-300">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder-slate-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                placeholder="clinician@hospital.org"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder-slate-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                placeholder="Enter your password"
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-500/10 px-4 py-2.5 text-sm text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-healthos-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-healthos-700 focus:outline-none focus:ring-2 focus:ring-healthos-500 focus:ring-offset-2 focus:ring-offset-slate-800 disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-healthos-400 hover:text-healthos-300">
              Register
            </Link>
          </p>
          <p className="mt-2 text-center text-sm text-slate-400">
            Setting up a new organization?{" "}
            <Link href="/signup" className="text-teal-400 hover:text-teal-300">
              Create Organization
            </Link>
          </p>

          <p className="mt-3 text-center text-xs text-slate-500">
            Protected health information (PHI) access is logged and audited.
          </p>
        </div>
      </div>
    </div>
  );
}
