"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function OrgSignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [tier, setTier] = useState("starter");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleOrgNameChange(value: string) {
    setOrgName(value);
    // Auto-generate slug from name
    const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 100);
    setOrgSlug(slug);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/organizations/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_name: orgName,
          org_slug: orgSlug,
          tier,
          admin_email: email,
          admin_password: password,
          admin_full_name: fullName,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Signup failed");
        setLoading(false);
        return;
      }

      const data = await res.json();

      // Auto-login: store tokens
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      router.push("/dashboard");
    } catch {
      setError("Unable to connect to server");
      setLoading(false);
    }
  }

  const TIERS = [
    {
      id: "starter",
      name: "Starter",
      price: "Free",
      description: "Up to 5 users, 100 patients, basic features",
      features: ["5 Staff Accounts", "100 Patient Records", "Basic RPM", "Email Support"],
    },
    {
      id: "standard",
      name: "Standard",
      price: "$299/mo",
      description: "Up to 50 users, unlimited patients, full clinical suite",
      features: ["50 Staff Accounts", "Unlimited Patients", "Full Clinical Suite", "AI Diagnostics", "Telehealth", "Priority Support"],
    },
    {
      id: "enterprise",
      name: "Enterprise",
      price: "Custom",
      description: "Unlimited users, dedicated infrastructure, BAA included",
      features: ["Unlimited Users", "Dedicated Infrastructure", "Custom Integrations", "HIPAA BAA Included", "24/7 Support", "SLA Guarantee"],
      disabled: true,
    },
  ];

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-2xl px-6">
        <div className="rounded-2xl border border-slate-700/50 bg-slate-800/60 p-8 shadow-2xl backdrop-blur-sm">
          {/* Header */}
          <div className="mb-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600 shadow-lg shadow-teal-500/20">
              <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-white">Create Your Organization</h1>
            <p className="mt-1 text-sm text-slate-400">
              Set up Eminence HealthOS for your hospital or clinic
            </p>
          </div>

          {/* Step Indicator */}
          <div className="mb-6 flex items-center justify-center gap-3">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${step === 1 ? "bg-teal-500 text-white" : "bg-teal-500/20 text-teal-400"}`}>1</div>
            <div className="h-px w-12 bg-slate-600" />
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${step === 2 ? "bg-teal-500 text-white" : "bg-slate-700 text-slate-400"}`}>2</div>
          </div>

          {error && (
            <div className="mb-4 rounded-lg border border-red-800/50 bg-red-900/30 p-3 text-center text-sm text-red-300">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {step === 1 ? (
              <div className="space-y-5">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Organization Details</h2>

                <div>
                  <label htmlFor="orgName" className="block text-sm font-medium text-slate-300">
                    Organization Name
                  </label>
                  <input
                    id="orgName"
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => handleOrgNameChange(e.target.value)}
                    placeholder="Mercy General Hospital"
                    className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label htmlFor="orgSlug" className="block text-sm font-medium text-slate-300">
                    Organization URL Slug
                  </label>
                  <div className="mt-1 flex items-center rounded-lg border border-slate-600 bg-slate-700/50">
                    <span className="px-3 text-xs text-slate-500">healthos.app/</span>
                    <input
                      id="orgSlug"
                      type="text"
                      required
                      pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
                      value={orgSlug}
                      onChange={(e) => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                      placeholder="mercy-general"
                      className="w-full rounded-r-lg bg-transparent px-2 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none"
                    />
                  </div>
                </div>

                {/* Tier Selection */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-3">Select Plan</label>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    {TIERS.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        disabled={t.disabled}
                        onClick={() => !t.disabled && setTier(t.id)}
                        className={`rounded-lg border p-4 text-left transition ${
                          t.disabled
                            ? "cursor-not-allowed border-slate-700 bg-slate-800/30 opacity-50"
                            : tier === t.id
                            ? "border-teal-500 bg-teal-500/10 ring-1 ring-teal-500"
                            : "border-slate-600 bg-slate-700/30 hover:border-slate-500"
                        }`}
                      >
                        <p className="text-sm font-bold text-white">{t.name}</p>
                        <p className="text-lg font-bold text-teal-400">{t.price}</p>
                        <p className="mt-1 text-[11px] text-slate-400">{t.description}</p>
                        {t.disabled && <p className="mt-1 text-[10px] font-medium text-amber-400">Contact Sales</p>}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => { if (orgName && orgSlug) setStep(2); }}
                  disabled={!orgName || !orgSlug}
                  className="w-full rounded-lg bg-gradient-to-r from-teal-500 to-cyan-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-500/25 transition hover:from-teal-400 hover:to-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue &rarr;
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Admin Account</h2>
                  <button type="button" onClick={() => setStep(1)} className="text-xs text-teal-400 hover:text-teal-300">
                    &larr; Back
                  </button>
                </div>

                <div className="rounded-lg bg-slate-700/30 p-3 text-xs text-slate-400">
                  Creating <span className="font-semibold text-white">{orgName}</span> on the <span className="font-semibold text-teal-400">{tier}</span> plan
                </div>

                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium text-slate-300">
                    Full Name
                  </label>
                  <input
                    id="fullName"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Dr. Jane Smith"
                    className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-slate-300">
                    Admin Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@mercygeneral.com"
                    className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-slate-300">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg bg-gradient-to-r from-teal-500 to-cyan-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-500/25 transition hover:from-teal-400 hover:to-cyan-500 disabled:opacity-50"
                >
                  {loading ? "Creating organization..." : "Create Organization & Sign In"}
                </button>
              </div>
            )}
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-slate-400">
              Already have an account?{" "}
              <Link href="/login" className="font-medium text-teal-400 hover:text-teal-300">Sign in</Link>
            </p>
            <p className="mt-1 text-sm text-slate-400">
              Need enterprise?{" "}
              <span className="font-medium text-teal-400">Contact sales@eminence.health</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
