"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { AdminDashboard } from "@/components/dashboard/AdminDashboard";
import { ClinicianDashboard } from "@/components/dashboard/ClinicianDashboard";
import { NurseDashboard } from "@/components/dashboard/NurseDashboard";
import { OfficeAdminDashboard } from "@/components/dashboard/OfficeAdminDashboard";
import { LabTechDashboard } from "@/components/dashboard/LabTechDashboard";
import { PharmacistDashboard } from "@/components/dashboard/PharmacistDashboard";
import { BillingDashboard } from "@/components/dashboard/BillingDashboard";
import { ReadOnlyDashboard } from "@/components/dashboard/ReadOnlyDashboard";

export default function DashboardPage() {
  const { role, user, loading } = useAuth();
  const router = useRouter();

  if (loading || !user || !role) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-healthos-500 border-t-transparent" />
      </div>
    );
  }

  switch (role) {
    case "admin":
      return <AdminDashboard />;
    case "clinician":
      return <ClinicianDashboard />;
    case "nurse":
      return <NurseDashboard />;
    case "office_admin":
      return <OfficeAdminDashboard />;
    case "care_manager":
      return <NurseDashboard />;
    case "lab_tech":
      return <LabTechDashboard />;
    case "pharmacist":
      return <PharmacistDashboard />;
    case "billing":
      return <BillingDashboard />;
    case "read_only":
      return <ReadOnlyDashboard />;
    case "patient":
      // Patient shouldn't be on /dashboard — RouteGuard handles redirect
      router.replace("/patient-portal");
      return null;
    default:
      return <NurseDashboard />;
  }
}
