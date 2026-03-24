"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("clinician");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
          role,
          org_slug: "eminence-demo",
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Registration failed");
        setLoading(false);
        return;
      }

      router.push("/login");
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
            Create your account
          </p>
        </div>

        {/* Register card */}
        <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5 sm:p-8 shadow-xl backdrop-blur">
          <h2 className="mb-6 text-lg font-semibold text-white">Register</h2>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="fullName" className="mb-1 block text-sm font-medium text-slate-300">
                Full Name
              </label>
              <input
                id="fullName"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder-slate-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
                placeholder="Dr. Jane Doe"
              />
            </div>

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

            <div>
              <label htmlFor="role" className="mb-1 block text-sm font-medium text-slate-300">
                Role
              </label>
              <select
                id="role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              >
                <option value="clinician">Clinician</option>
                <option value="nurse">Nurse</option>
                <option value="care_manager">Care Manager</option>
                <option value="patient">Patient</option>
              </select>
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
              {loading ? "Creating account..." : "Create account"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            Already have an account?{" "}
            <Link href="/login" className="text-healthos-400 hover:text-healthos-300">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
