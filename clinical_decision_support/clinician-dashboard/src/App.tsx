import { useMemo, useState } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { PatientPicker } from "./components/PatientPicker";
import { fetchObservations, normalizeVitals } from "./lib/fhirApi";
import { VitalsCharts } from "./components/VitalsCharts";
import { PatientList } from "./components/PatientList";
import { PatientForm } from "./components/PatientForm";
import { PatientImport } from "./components/PatientImport";
import { DeviceList } from "./components/DeviceList";
import { DeviceForm } from "./components/DeviceForm";
import { DeviceAssignment } from "./components/DeviceAssignment";
import { SimulatorControl } from "./components/SimulatorControl";
import { DoctorPortal } from "./components/DoctorPortal";
import { AlertsDashboard } from "./components/AlertsDashboard";
import { AnalyticsDashboard } from "./components/AnalyticsDashboard";
import { UserManagement } from "./components/UserManagement";
import { LabsDashboard } from "./components/LabsDashboard";
import { MedicationsDashboard } from "./components/MedicationsDashboard";
import { LoginPage } from "./components/LoginPage";
import { RegisterPage } from "./components/RegisterPage";
import { AuthProvider, useAuth } from "./context/AuthContext";
import type { Patient } from "./lib/patientApi";
import type { Device } from "./lib/deviceApi";

const qc = new QueryClient();

type View = "dashboard" | "patients" | "devices" | "simulator" | "doctor" | "labs" | "medications" | "alerts" | "analytics" | "users";

// Icons as SVG components
const Icons = {
  dashboard: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v2a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 13a1 1 0 011-1h4a1 1 0 011 1v6a1 1 0 01-1 1h-4a1 1 0 01-1-1v-6z" />
    </svg>
  ),
  patients: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  devices: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
    </svg>
  ),
  simulator: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  doctor: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  labs: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
    </svg>
  ),
  medications: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  alerts: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  ),
  analytics: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  users: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  logout: (
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
    </svg>
  ),
  heartbeat: (
    <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
    </svg>
  ),
};

function VitalsDashboard() {
  const [patientRef, setPatientRef] = useState<string>("");

  const obsQ = useQuery({
    queryKey: ["obs", patientRef],
    queryFn: () => fetchObservations({ patientRef: patientRef || undefined, count: 200 }),
    refetchInterval: 15000,
  });

  const rows = useMemo(() => (obsQ.data ? normalizeVitals(obsQ.data) : []), [obsQ.data]);

  return (
    <div className="animate-fade-in">
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", margin: 0 }}>Vitals Dashboard</h1>
        <p style={{ color: "#6b7280", marginTop: 4, fontSize: 14 }}>Real-time patient vital signs monitoring</p>
      </div>

      {/* Controls Bar */}
      <div className="controls-bar" style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        marginBottom: 24,
        padding: 16,
        background: "white",
        borderRadius: 12,
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        border: "1px solid #e5e7eb",
        flexWrap: "wrap",
      }}>
        <PatientPicker patientRef={patientRef} onChange={setPatientRef} />
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "6px 12px",
            background: obsQ.isFetching ? "#fef3c7" : "#dcfce7",
            borderRadius: 20,
            fontSize: 12,
            fontWeight: 500,
            color: obsQ.isFetching ? "#92400e" : "#166534",
          }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: obsQ.isFetching ? "#f59e0b" : "#10b981",
            }} />
            {obsQ.isFetching ? "Syncing..." : "Live"}
          </div>
          <button
            onClick={() => obsQ.refetch()}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              background: "white",
              color: "#374151",
              fontWeight: 500,
              fontSize: 13,
              display: "flex",
              alignItems: "center",
              gap: 6,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onMouseOver={(e) => e.currentTarget.style.background = "#f9fafb"}
            onMouseOut={(e) => e.currentTarget.style.background = "white"}
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Error State */}
      {obsQ.error && (
        <div style={{
          padding: 16,
          background: "#fef2f2",
          border: "1px solid #fecaca",
          borderRadius: 12,
          marginBottom: 24,
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
        }}>
          <div style={{ color: "#dc2626", marginTop: 2 }}>
            <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 600, color: "#991b1b" }}>FHIR Connection Error</div>
            <div style={{ fontSize: 13, color: "#7f1d1d", marginTop: 2 }}>
              Unable to fetch observations. Please verify the FHIR server is running and accessible.
            </div>
          </div>
        </div>
      )}

      {/* Stats Overview */}
      <div className="stat-grid" style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: 16,
        marginBottom: 24,
      }}>
        <StatCard
          label="Total Observations"
          value={rows.length.toString()}
          icon={<svg width="24" height="24" fill="none" stroke="#3b82f6" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
          color="#3b82f6"
        />
        <StatCard
          label="Data Category"
          value="Vital Signs"
          icon={<svg width="24" height="24" fill="none" stroke="#10b981" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>}
          color="#10b981"
        />
        <StatCard
          label="Refresh Rate"
          value="15 sec"
          icon={<svg width="24" height="24" fill="none" stroke="#8b5cf6" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          color="#8b5cf6"
        />
        <StatCard
          label="Patient Filter"
          value={patientRef || "All Patients"}
          icon={<svg width="24" height="24" fill="none" stroke="#f59e0b" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>}
          color="#f59e0b"
        />
      </div>

      {/* Charts */}
      <div style={{
        background: "white",
        borderRadius: 12,
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        border: "1px solid #e5e7eb",
        overflow: "hidden",
      }}>
        <div style={{
          padding: "16px 20px",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Vitals Timeline</h2>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>
              Showing {rows.length} observations from FHIR server
            </p>
          </div>
        </div>
        <div style={{ padding: 20 }}>
          <VitalsCharts rows={rows} />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: string; icon: React.ReactNode; color: string }) {
  return (
    <div style={{
      background: "white",
      borderRadius: 12,
      padding: 20,
      boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
      border: "1px solid #e5e7eb",
      display: "flex",
      alignItems: "flex-start",
      gap: 16,
    }}>
      <div style={{
        width: 48,
        height: 48,
        borderRadius: 10,
        background: `${color}10`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: "#111827" }}>{value}</div>
      </div>
    </div>
  );
}

function PatientManagement() {
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

  const handleSelectPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setShowForm(true);
  };

  const handleCreateNew = () => {
    setSelectedPatient(null);
    setShowForm(true);
  };

  const handleFormSuccess = () => {
    setShowForm(false);
    setSelectedPatient(null);
  };

  const handleImportSuccess = () => {
    setShowImport(false);
  };

  return (
    <div className="animate-fade-in">
      <PatientList
        onSelectPatient={handleSelectPatient}
        onCreateNew={handleCreateNew}
        onImport={() => setShowImport(true)}
      />

      {showForm && (
        <PatientForm
          patient={selectedPatient}
          onClose={() => {
            setShowForm(false);
            setSelectedPatient(null);
          }}
          onSuccess={handleFormSuccess}
        />
      )}

      {showImport && (
        <PatientImport
          onClose={() => setShowImport(false)}
          onSuccess={handleImportSuccess}
        />
      )}
    </div>
  );
}

function DeviceManagement() {
  const [showForm, setShowForm] = useState(false);
  const [showAssign, setShowAssign] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [deviceToAssign, setDeviceToAssign] = useState<Device | null>(null);

  const handleSelectDevice = (device: Device) => {
    setSelectedDevice(device);
    setShowForm(true);
  };

  const handleCreateNew = () => {
    setSelectedDevice(null);
    setShowForm(true);
  };

  const handleAssign = (device: Device) => {
    setDeviceToAssign(device);
    setShowAssign(true);
  };

  const handleFormSuccess = () => {
    setShowForm(false);
    setSelectedDevice(null);
  };

  const handleAssignSuccess = () => {
    setShowAssign(false);
    setDeviceToAssign(null);
  };

  return (
    <div className="animate-fade-in">
      <DeviceList
        onSelectDevice={handleSelectDevice}
        onCreateNew={handleCreateNew}
        onAssign={handleAssign}
      />

      {showForm && (
        <DeviceForm
          device={selectedDevice}
          onClose={() => {
            setShowForm(false);
            setSelectedDevice(null);
          }}
          onSuccess={handleFormSuccess}
        />
      )}

      {showAssign && deviceToAssign && (
        <DeviceAssignment
          device={deviceToAssign}
          onClose={() => {
            setShowAssign(false);
            setDeviceToAssign(null);
          }}
          onSuccess={handleAssignSuccess}
        />
      )}
    </div>
  );
}

function AuthenticatedApp() {
  const { user, permissions, logout, isLoading } = useAuth();
  const [currentView, setCurrentView] = useState<View>("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  if (isLoading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      }}>
        <div style={{ textAlign: "center", color: "white" }}>
          <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3, margin: "0 auto 16px" }} />
          <div style={{ fontSize: 16, fontWeight: 500 }}>Loading...</div>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
  };

  const navItems: { key: View; label: string; icon: React.ReactNode; permission?: boolean }[] = [
    { key: "dashboard", label: "Vitals Dashboard", icon: Icons.dashboard, permission: true },
    { key: "patients", label: "Patients", icon: Icons.patients, permission: permissions?.can_view_patients },
    { key: "devices", label: "Devices", icon: Icons.devices, permission: true },
    { key: "simulator", label: "IoT Simulator", icon: Icons.simulator, permission: permissions?.can_manage_devices },
    { key: "doctor", label: "Doctor Portal", icon: Icons.doctor, permission: permissions?.can_view_clinical_data },
    { key: "labs", label: "Lab Results", icon: Icons.labs, permission: permissions?.can_view_clinical_data },
    { key: "medications", label: "Medications", icon: Icons.medications, permission: permissions?.can_view_clinical_data },
    { key: "alerts", label: "Alerts", icon: Icons.alerts, permission: permissions?.can_manage_alerts },
    { key: "analytics", label: "Analytics", icon: Icons.analytics, permission: permissions?.can_view_analytics },
    { key: "users", label: "User Management", icon: Icons.users, permission: permissions?.can_manage_users },
  ];

  const filteredNavItems = navItems.filter(item => item.permission);

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#f3f4f6" }}>
      {/* Mobile sidebar overlay */}
      <div
        className={`mobile-sidebar-overlay${mobileSidebarOpen ? " active" : ""}`}
        onClick={() => setMobileSidebarOpen(false)}
      />
      {/* Sidebar */}
      <aside
        className={`app-sidebar${mobileSidebarOpen ? " open" : ""}`}
        style={{
          width: sidebarCollapsed ? 72 : 260,
          background: "linear-gradient(180deg, #1e293b 0%, #0f172a 100%)",
          display: "flex",
          flexDirection: "column",
          transition: "width 0.3s ease, transform 0.3s ease",
          position: "fixed",
          height: "100vh",
          zIndex: 200,
        }}
      >
        {/* Logo */}
        <div style={{
          padding: sidebarCollapsed ? "20px 16px" : "20px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}>
          <div style={{
            width: 40,
            height: 40,
            background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
            borderRadius: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            flexShrink: 0,
          }}>
            {Icons.heartbeat}
          </div>
          {!sidebarCollapsed && (
            <div>
              <div style={{ color: "white", fontWeight: 700, fontSize: 16 }}>HealthCare</div>
              <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 11 }}>Clinical Platform</div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: "16px 12px", overflowY: "auto" }}>
          {filteredNavItems.map((item) => (
            <button
              key={item.key}
              onClick={() => { setCurrentView(item.key); setMobileSidebarOpen(false); }}
              title={sidebarCollapsed ? item.label : undefined}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: sidebarCollapsed ? "12px" : "12px 16px",
                marginBottom: 4,
                borderRadius: 8,
                background: currentView === item.key ? "rgba(59, 130, 246, 0.2)" : "transparent",
                color: currentView === item.key ? "#60a5fa" : "rgba(255,255,255,0.7)",
                border: "none",
                cursor: "pointer",
                transition: "all 0.2s",
                justifyContent: sidebarCollapsed ? "center" : "flex-start",
              }}
              onMouseOver={(e) => {
                if (currentView !== item.key) {
                  e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                }
              }}
              onMouseOut={(e) => {
                if (currentView !== item.key) {
                  e.currentTarget.style.background = "transparent";
                }
              }}
            >
              {item.icon}
              {!sidebarCollapsed && <span style={{ fontSize: 14, fontWeight: 500 }}>{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* User Section */}
        <div style={{
          padding: sidebarCollapsed ? "16px 12px" : "16px 20px",
          borderTop: "1px solid rgba(255,255,255,0.1)",
        }}>
          {!sidebarCollapsed && (
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 12,
            }}>
              <div style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontWeight: 600,
                fontSize: 14,
              }}>
                {user?.display_name?.charAt(0).toUpperCase() || "U"}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: "white", fontWeight: 500, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {user?.display_name}
                </div>
                <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 11 }}>
                  {user?.role?.charAt(0).toUpperCase()}{user?.role?.slice(1)}
                </div>
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            title={sidebarCollapsed ? "Logout" : undefined}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: sidebarCollapsed ? "center" : "flex-start",
              gap: 12,
              padding: sidebarCollapsed ? "12px" : "10px 16px",
              borderRadius: 8,
              background: "rgba(239, 68, 68, 0.1)",
              color: "#f87171",
              border: "none",
              cursor: "pointer",
              transition: "all 0.2s",
              fontSize: 13,
              fontWeight: 500,
            }}
            onMouseOver={(e) => e.currentTarget.style.background = "rgba(239, 68, 68, 0.2)"}
            onMouseOut={(e) => e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)"}
          >
            {Icons.logout}
            {!sidebarCollapsed && "Sign Out"}
          </button>
        </div>

        {/* Collapse Toggle */}
        <button
          className="sidebar-collapse-btn"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          style={{
            position: "absolute",
            right: -12,
            top: "50%",
            transform: "translateY(-50%)",
            width: 24,
            height: 24,
            borderRadius: "50%",
            background: "#1e293b",
            border: "2px solid #3b82f6",
            color: "#3b82f6",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
        >
          <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ transform: sidebarCollapsed ? "rotate(180deg)" : "none", transition: "transform 0.3s" }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </aside>

      {/* Main Content */}
      <main
        className="app-main"
        style={{
          flex: 1,
          marginLeft: sidebarCollapsed ? 72 : 260,
          transition: "margin-left 0.3s ease",
          minHeight: "100vh",
        }}
      >
        {/* Top Header */}
        <header
          className="app-header"
          style={{
            background: "white",
            borderBottom: "1px solid #e5e7eb",
            padding: "16px 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            position: "sticky",
            top: 0,
            zIndex: 50,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Mobile hamburger menu */}
            <button
              className="mobile-menu-btn"
              onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
              aria-label="Toggle menu"
            >
              <svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: "#111827" }}>
              {filteredNavItems.find(n => n.key === currentView)?.label || "Dashboard"}
            </h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div className="header-user-info" style={{ textAlign: "right" }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: "#374151" }}>{user?.display_name}</div>
              <div style={{ fontSize: 11, color: "#6b7280" }}>
                {user?.department || user?.role}
              </div>
            </div>
            <div
              className="header-avatar"
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontWeight: 600,
              }}
            >
              {user?.display_name?.charAt(0).toUpperCase() || "U"}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div
          className="app-content"
          style={{
            padding: 32,
            maxWidth: 1600,
            margin: "0 auto",
          }}
        >
          {currentView === "dashboard" && <VitalsDashboard />}
          {currentView === "patients" && <PatientManagement />}
          {currentView === "devices" && <DeviceManagement />}
          {currentView === "simulator" && <div className="animate-fade-in"><SimulatorControl /></div>}
          {currentView === "doctor" && <div className="animate-fade-in"><DoctorPortal /></div>}
          {currentView === "labs" && <div className="animate-fade-in"><LabsDashboard /></div>}
          {currentView === "medications" && <div className="animate-fade-in"><MedicationsDashboard /></div>}
          {currentView === "alerts" && <div className="animate-fade-in"><AlertsDashboard /></div>}
          {currentView === "analytics" && <div className="animate-fade-in"><AnalyticsDashboard /></div>}
          {currentView === "users" && <div className="animate-fade-in"><UserManagement /></div>}
        </div>
      </main>
    </div>
  );
}

function MainApp() {
  const { isAuthenticated, isLoading } = useAuth();
  const [, setForceRender] = useState(0);
  const [showRegister, setShowRegister] = useState(false);

  if (isLoading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      }}>
        <div style={{ textAlign: "center", color: "white" }}>
          <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3, margin: "0 auto 16px", borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }} />
          <div style={{ fontSize: 16, fontWeight: 500 }}>Loading...</div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (showRegister) {
      return (
        <RegisterPage
          onRegisterSuccess={() => {
            setShowRegister(false);
            setForceRender((n) => n + 1);
          }}
          onBackToLogin={() => setShowRegister(false)}
        />
      );
    }
    return (
      <LoginPage
        onLoginSuccess={() => setForceRender((n) => n + 1)}
        onRegister={() => setShowRegister(true)}
      />
    );
  }

  return <AuthenticatedApp />;
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <MainApp />
      </AuthProvider>
    </QueryClientProvider>
  );
}
