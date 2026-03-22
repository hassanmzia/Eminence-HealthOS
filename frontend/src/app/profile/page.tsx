"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  fetchMyProfile,
  updateMyProfile,
  uploadAvatar,
  deleteAvatar,
  changePassword,
  setupMFA,
  verifyMFA,
  disableMFA,
  deleteMyAccount,
  type UserProfile,
  type MFASetup,
} from "@/lib/api";

type Tab = "profile" | "security" | "danger";

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMyProfile()
      .then((u) => {
        setUser(u);
        setLoading(false);
      })
      .catch(() => {
        router.push("/login");
      });
  }, [router]);

  // Handle hash-based navigation
  useEffect(() => {
    const hash = window.location.hash.replace("#", "");
    if (hash === "security" || hash === "danger") setActiveTab(hash);
  }, []);

  if (loading || !user) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-healthos-200 border-t-healthos-600" />
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "profile", label: "Profile" },
    { key: "security", label: "Security" },
    { key: "danger", label: "Account" },
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Account Settings</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Manage your profile, security, and account preferences.</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`border-b-2 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-healthos-600 text-healthos-600"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "profile" && <ProfileTab user={user} onUpdate={setUser} />}
      {activeTab === "security" && <SecurityTab user={user} onUpdate={setUser} />}
      {activeTab === "danger" && <DangerTab />}
    </div>
  );
}

/* ─── Profile Tab ──────────────────────────────────────────────────────────── */

function ProfileTab({ user, onUpdate }: { user: UserProfile; onUpdate: (u: UserProfile) => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fullName, setFullName] = useState(user.full_name);
  const [email, setEmail] = useState(user.email);
  const [phone, setPhone] = useState(user.phone || "");
  const [specialty, setSpecialty] = useState((user.profile?.specialty as string) || "");
  const [saving, setSaving] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateMyProfile({
        full_name: fullName,
        email,
        phone: phone || undefined,
        profile: { specialty: specialty || undefined },
      });
      onUpdate(updated);
      setMessage({ type: "success", text: "Profile updated successfully." });
    } catch (e: unknown) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Failed to update profile." });
    } finally {
      setSaving(false);
    }
  }

  async function handleAvatarUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingAvatar(true);
    try {
      const updated = await uploadAvatar(file);
      onUpdate(updated);
    } catch {
      setMessage({ type: "error", text: "Failed to upload avatar." });
    } finally {
      setUploadingAvatar(false);
    }
  }

  async function handleRemoveAvatar() {
    try {
      const updated = await deleteAvatar();
      onUpdate(updated);
    } catch {
      setMessage({ type: "error", text: "Failed to remove avatar." });
    }
  }

  const initials = user.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  return (
    <div className="space-y-6">
      {/* Avatar Section */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Profile Picture</h2>
        <div className="mt-4 flex items-center gap-6">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt="Avatar"
              className="h-20 w-20 rounded-full object-cover ring-2 ring-gray-100"
            />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-healthos-100 text-2xl font-bold text-healthos-700 ring-2 ring-gray-100">
              {initials}
            </div>
          )}
          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingAvatar}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50"
              >
                {uploadingAvatar ? "Uploading..." : "Upload Photo"}
              </button>
              {user.avatar_url && (
                <button
                  onClick={handleRemoveAvatar}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Remove
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">JPEG, PNG, or WebP. Max 5 MB.</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleAvatarUpload}
              className="hidden"
            />
          </div>
        </div>
      </div>

      {/* Personal Information */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Personal Information</h2>

        {message && (
          <div
            className={`mt-4 rounded-lg px-4 py-3 text-sm ${
              message.type === "success"
                ? "bg-green-50 text-green-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Phone</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 000-0000"
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Specialty</label>
            <input
              type="text"
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
              placeholder="e.g. Cardiology"
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Role</label>
            <input
              type="text"
              value={user.role}
              disabled
              className="mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm capitalize text-gray-500 dark:text-gray-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Member Since</label>
            <input
              type="text"
              value={new Date(user.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
              disabled
              className="mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-500 dark:text-gray-400"
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-healthos-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Security Tab ─────────────────────────────────────────────────────────── */

function SecurityTab({ user, onUpdate }: { user: UserProfile; onUpdate: (u: UserProfile) => void }) {
  return (
    <div className="space-y-6">
      <ChangePasswordSection />
      <MFASection user={user} onUpdate={onUpdate} />
    </div>
  );
}

function ChangePasswordSection() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "New passwords do not match." });
      return;
    }
    if (newPassword.length < 8) {
      setMessage({ type: "error", text: "Password must be at least 8 characters." });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setMessage({ type: "success", text: "Password changed successfully." });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e: unknown) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Failed to change password." });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Change Password</h2>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Update your password to keep your account secure.</p>

      {message && (
        <div
          className={`mt-4 rounded-lg px-4 py-3 text-sm ${
            message.type === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Current Password</label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">New Password</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Confirm New Password</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={8}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-healthos-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50"
          >
            {saving ? "Updating..." : "Update Password"}
          </button>
        </div>
      </form>
    </div>
  );
}

function MFASection({ user, onUpdate }: { user: UserProfile; onUpdate: (u: UserProfile) => void }) {
  const [mfaSetup, setMfaSetup] = useState<MFASetup | null>(null);
  const [code, setCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [settingUp, setSettingUp] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [showDisable, setShowDisable] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  async function handleSetup() {
    setSettingUp(true);
    setMessage(null);
    try {
      const setup = await setupMFA();
      setMfaSetup(setup);
    } catch {
      setMessage({ type: "error", text: "Failed to start MFA setup." });
    } finally {
      setSettingUp(false);
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    setVerifying(true);
    setMessage(null);
    try {
      await verifyMFA(code);
      onUpdate({ ...user, mfa_enabled: true });
      setMfaSetup(null);
      setCode("");
      setMessage({ type: "success", text: "MFA enabled successfully." });
    } catch {
      setMessage({ type: "error", text: "Invalid verification code. Please try again." });
    } finally {
      setVerifying(false);
    }
  }

  async function handleDisable(e: React.FormEvent) {
    e.preventDefault();
    setDisabling(true);
    setMessage(null);
    try {
      await disableMFA(disableCode);
      onUpdate({ ...user, mfa_enabled: false });
      setShowDisable(false);
      setDisableCode("");
      setMessage({ type: "success", text: "MFA disabled." });
    } catch {
      setMessage({ type: "error", text: "Invalid code. MFA not disabled." });
    } finally {
      setDisabling(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Two-Factor Authentication</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Add an extra layer of security using a TOTP authenticator app.
          </p>
        </div>
        <span
          className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${
            user.mfa_enabled
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
          }`}
        >
          {user.mfa_enabled ? "Enabled" : "Disabled"}
        </span>
      </div>

      {message && (
        <div
          className={`mt-4 rounded-lg px-4 py-3 text-sm ${
            message.type === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {!user.mfa_enabled && !mfaSetup && (
        <div className="mt-4">
          <button
            onClick={handleSetup}
            disabled={settingUp}
            className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50"
          >
            {settingUp ? "Setting up..." : "Enable MFA"}
          </button>
        </div>
      )}

      {mfaSetup && (
        <div className="mt-4 space-y-4">
          <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-4">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">1. Scan this QR code with your authenticator app:</p>
            <div className="mt-3 flex justify-center">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(mfaSetup.provisioning_uri)}`}
                alt="MFA QR Code"
                className="h-48 w-48 rounded-lg"
              />
            </div>
            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
              Or enter this key manually:{" "}
              <code className="rounded bg-gray-200 px-2 py-0.5 font-mono text-xs">{mfaSetup.secret}</code>
            </p>
          </div>

          <form onSubmit={handleVerify}>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">2. Enter the 6-digit code from your app:</p>
            <div className="mt-2 flex gap-3">
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                className="w-32 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-center font-mono text-lg tracking-widest focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
              />
              <button
                type="submit"
                disabled={code.length !== 6 || verifying}
                className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50"
              >
                {verifying ? "Verifying..." : "Verify & Enable"}
              </button>
              <button
                type="button"
                onClick={() => { setMfaSetup(null); setCode(""); }}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {user.mfa_enabled && !showDisable && (
        <div className="mt-4">
          <button
            onClick={() => setShowDisable(true)}
            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
          >
            Disable MFA
          </button>
        </div>
      )}

      {showDisable && (
        <form onSubmit={handleDisable} className="mt-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Enter a code from your authenticator to confirm:</p>
          <div className="mt-2 flex gap-3">
            <input
              type="text"
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="000000"
              maxLength={6}
              className="w-32 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-center font-mono text-lg tracking-widest focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            />
            <button
              type="submit"
              disabled={disableCode.length !== 6 || disabling}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
            >
              {disabling ? "Disabling..." : "Confirm Disable"}
            </button>
            <button
              type="button"
              onClick={() => { setShowDisable(false); setDisableCode(""); }}
              className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

/* ─── Danger Zone Tab ──────────────────────────────────────────────────────── */

function DangerTab() {
  const router = useRouter();
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteMyAccount();
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      router.push("/login");
    } catch {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-red-200 bg-white dark:bg-gray-900 p-6">
        <h2 className="text-lg font-semibold text-red-600">Danger Zone</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Deactivating your account will immediately revoke your access. Contact your organization admin to reactivate.
        </p>

        {!showConfirm ? (
          <button
            onClick={() => setShowConfirm(true)}
            className="mt-4 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
          >
            Deactivate Account
          </button>
        ) : (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Type <strong>DEACTIVATE</strong> to confirm:
            </p>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DEACTIVATE"
              className="w-64 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
            />
            <div className="flex gap-3">
              <button
                onClick={handleDelete}
                disabled={confirmText !== "DEACTIVATE" || deleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? "Deactivating..." : "Confirm Deactivation"}
              </button>
              <button
                onClick={() => { setShowConfirm(false); setConfirmText(""); }}
                className="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
