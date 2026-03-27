"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchHospitals,
  fetchDepartments,
  type HospitalResponse,
  type DepartmentResponse,
} from "@/lib/platform-api";

/* Roles that require Hospital + Department assignment */
const STAFF_ROLES = new Set(["clinician", "nurse", "care_manager", "lab_tech", "pharmacist", "office_admin"]);
const PROVIDER_ROLES = new Set(["clinician"]);
const NURSE_ROLES = new Set(["nurse"]);
const OFFICE_ADMIN_ROLES = new Set(["office_admin"]);

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("patient");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Hierarchy state
  const [hospitals, setHospitals] = useState<HospitalResponse[]>([]);
  const [departments, setDepartments] = useState<DepartmentResponse[]>([]);
  const [hospitalId, setHospitalId] = useState("");
  const [departmentId, setDepartmentId] = useState("");

  // Role-specific state
  const [specialty, setSpecialty] = useState("");
  const [npi, setNpi] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [position, setPosition] = useState("");
  const [employeeId, setEmployeeId] = useState("");

  const needsHospital = STAFF_ROLES.has(role);
  const isProvider = PROVIDER_ROLES.has(role);
  const isNurse = NURSE_ROLES.has(role);
  const isOfficeAdmin = OFFICE_ADMIN_ROLES.has(role);

  useEffect(() => {
    fetchHospitals().then(setHospitals).catch(() => {});
  }, []);

  useEffect(() => {
    if (hospitalId) {
      fetchDepartments(hospitalId).then(setDepartments).catch(() => setDepartments([]));
      setDepartmentId("");
    } else {
      setDepartments([]);
    }
  }, [hospitalId]);

  // Reset role-specific fields when role changes
  useEffect(() => {
    setHospitalId(""); setDepartmentId("");
    setSpecialty(""); setNpi(""); setLicenseNumber("");
    setPosition(""); setEmployeeId("");
  }, [role]);

  function canSubmit() {
    if (!fullName || !email || !password) return false;
    if (needsHospital && (!hospitalId || !departmentId)) return false;
    if (isProvider && (!specialty || !npi)) return false;
    if (isNurse && !licenseNumber) return false;
    if (isOfficeAdmin && !employeeId) return false;
    return true;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit()) return;
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
          hospital_id: hospitalId || undefined,
          department_id: departmentId || undefined,
          specialty: specialty || undefined,
          npi: npi || undefined,
          license_number: licenseNumber || undefined,
          position: position || undefined,
          employee_id: employeeId || undefined,
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

  const labelCls = "mb-1 block text-sm font-medium text-slate-300";
  const inputCls = "w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white placeholder-slate-400 focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500";
  const selectCls = "w-full rounded-lg border border-slate-600 bg-slate-700/50 px-4 py-2.5 text-sm text-white focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500";

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
        <div className="rounded-2xl border border-slate-700 bg-slate-800/50 p-5 sm:p-8 shadow-xl backdrop-blur max-h-[80vh] overflow-y-auto">
          <h2 className="mb-6 text-lg font-semibold text-white">Register</h2>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="fullName" className={labelCls}>Full Name</label>
              <input id="fullName" type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputCls} placeholder="Dr. Jane Doe" />
            </div>

            <div>
              <label htmlFor="email" className={labelCls}>Email</label>
              <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} placeholder="clinician@hospital.org" />
            </div>

            <div>
              <label htmlFor="password" className={labelCls}>Password</label>
              <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} placeholder="Min 8 characters" />
            </div>

            <div>
              <label htmlFor="role" className={labelCls}>Role</label>
              <select id="role" value={role} onChange={(e) => setRole(e.target.value)} className={selectCls}>
                <option value="patient">Patient</option>
                <option value="clinician">Clinician / Physician</option>
                <option value="nurse">Nurse</option>
                <option value="office_admin">Office Admin</option>
                <option value="care_manager">Care Manager</option>
                <option value="lab_tech">Lab Technician</option>
                <option value="pharmacist">Pharmacist</option>
                <option value="billing">Billing</option>
                <option value="read_only">Read Only</option>
              </select>
            </div>

            {/* Hospital + Department (for staff roles) */}
            {needsHospital && (
              <>
                <div>
                  <label htmlFor="hospital" className={labelCls}>
                    Hospital <span className="text-red-400">*</span>
                  </label>
                  <select id="hospital" value={hospitalId} onChange={(e) => setHospitalId(e.target.value)} className={selectCls}>
                    <option value="">Select hospital</option>
                    {hospitals.map((h) => (
                      <option key={h.id} value={h.id}>{h.name}</option>
                    ))}
                  </select>
                  {hospitals.length === 0 && (
                    <p className="mt-1 text-xs text-amber-400">No hospitals available. Contact your administrator.</p>
                  )}
                </div>

                <div>
                  <label htmlFor="department" className={labelCls}>
                    Department <span className="text-red-400">*</span>
                  </label>
                  <select id="department" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} disabled={!hospitalId} className={`${selectCls} disabled:opacity-50`}>
                    <option value="">Select department</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                  {hospitalId && departments.length === 0 && (
                    <p className="mt-1 text-xs text-amber-400">No departments in this hospital.</p>
                  )}
                </div>
              </>
            )}

            {/* Provider-specific fields */}
            {isProvider && (
              <>
                <div>
                  <label htmlFor="specialty" className={labelCls}>
                    Specialty <span className="text-red-400">*</span>
                  </label>
                  <input id="specialty" type="text" value={specialty} onChange={(e) => setSpecialty(e.target.value)} className={inputCls} placeholder="e.g. Cardiology, Neurology" />
                </div>
                <div>
                  <label htmlFor="npi" className={labelCls}>
                    NPI Number <span className="text-red-400">*</span>
                  </label>
                  <input id="npi" type="text" value={npi} onChange={(e) => setNpi(e.target.value)} className={inputCls} placeholder="10-digit NPI" />
                </div>
                <div>
                  <label htmlFor="license" className={labelCls}>License Number</label>
                  <input id="license" type="text" value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} className={inputCls} placeholder="Optional" />
                </div>
              </>
            )}

            {/* Nurse-specific fields */}
            {isNurse && (
              <>
                <div>
                  <label htmlFor="license" className={labelCls}>
                    License Number <span className="text-red-400">*</span>
                  </label>
                  <input id="license" type="text" value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} className={inputCls} placeholder="Nursing license #" />
                </div>
                <div>
                  <label htmlFor="specialty" className={labelCls}>Specialty</label>
                  <input id="specialty" type="text" value={specialty} onChange={(e) => setSpecialty(e.target.value)} className={inputCls} placeholder="e.g. ICU, Pediatrics" />
                </div>
              </>
            )}

            {/* Office Admin-specific fields */}
            {isOfficeAdmin && (
              <>
                <div>
                  <label htmlFor="employeeId" className={labelCls}>
                    Employee ID <span className="text-red-400">*</span>
                  </label>
                  <input id="employeeId" type="text" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} className={inputCls} placeholder="EMP-0001" />
                </div>
                <div>
                  <label htmlFor="position" className={labelCls}>Position</label>
                  <input id="position" type="text" value={position} onChange={(e) => setPosition(e.target.value)} className={inputCls} placeholder="e.g. Office Manager" />
                </div>
              </>
            )}

            {/* Hierarchy validation notice */}
            {needsHospital && (!hospitalId || !departmentId) && (
              <div className="rounded-lg bg-amber-500/10 px-4 py-2.5 text-sm text-amber-400">
                Staff roles must be assigned to a Hospital and Department.
              </div>
            )}

            {error && (
              <div className="rounded-lg bg-red-500/10 px-4 py-2.5 text-sm text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !canSubmit()}
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
