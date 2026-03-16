import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSimulatorStatus,
  startSimulator,
  stopSimulator,
  triggerSimulator,
  getAssignedDevices,
  getPatientProfiles,
  setPatientCondition,
  resetStats,
  PATIENT_CONDITIONS,
} from "../lib/simulatorApi";

export function SimulatorControl() {
  const queryClient = useQueryClient();
  const [interval, setInterval] = useState(30);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [selectedCondition, setSelectedCondition] = useState("normal");

  const statusQuery = useQuery({
    queryKey: ["simulator-status"],
    queryFn: getSimulatorStatus,
    refetchInterval: 5000,
  });

  const devicesQuery = useQuery({
    queryKey: ["simulator-devices"],
    queryFn: getAssignedDevices,
    refetchInterval: 10000,
  });

  const profilesQuery = useQuery({
    queryKey: ["patient-profiles"],
    queryFn: getPatientProfiles,
    refetchInterval: 10000,
  });

  const startMutation = useMutation({
    mutationFn: () => startSimulator(interval),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["simulator-status"] }),
  });

  const stopMutation = useMutation({
    mutationFn: stopSimulator,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["simulator-status"] }),
  });

  const triggerMutation = useMutation({
    mutationFn: triggerSimulator,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["simulator-status"] }),
  });

  const conditionMutation = useMutation({
    mutationFn: (data: { patient_id: string; condition: string }) => setPatientCondition(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["patient-profiles"] }),
  });

  const resetMutation = useMutation({
    mutationFn: resetStats,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["simulator-status"] }),
  });

  const status = statusQuery.data;
  const devices = devicesQuery.data?.devices || [];
  const profiles = profilesQuery.data || {};

  const handleSetCondition = () => {
    if (selectedDevice) {
      const device = devices.find(d => d.device_id === selectedDevice);
      if (device) {
        const patientFhirId = `patient-${device.patient_id}`;
        conditionMutation.mutate({ patient_id: patientFhirId, condition: selectedCondition });
      }
    }
  };

  const cardStyle = {
    border: "1px solid #eee",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  };

  const buttonStyle = (active: boolean, color: string = "#2563eb") => ({
    padding: "8px 16px",
    borderRadius: 8,
    border: "none",
    background: active ? color : "#e5e7eb",
    color: active ? "white" : "#666",
    cursor: "pointer",
    fontWeight: 500,
    fontSize: 14,
  });

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginTop: 0, marginBottom: 16 }}>IoT Simulator</h2>

      {/* Status Card */}
      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16 }}>Simulator Status</h3>
            <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>
              Generates synthetic vitals for assigned devices
            </div>
          </div>
          <div style={{
            padding: "4px 12px",
            borderRadius: 999,
            background: status?.running ? "#dcfce7" : "#f3f4f6",
            color: status?.running ? "#166534" : "#666",
            fontWeight: 600,
            fontSize: 13,
          }}>
            {status?.running ? "RUNNING" : "STOPPED"}
          </div>
        </div>

        {statusQuery.error && (
          <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c", marginBottom: 16 }}>
            Cannot connect to simulator service. Make sure it's running on port 8004.
          </div>
        )}

        {status && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 16 }}>
            <div style={{ textAlign: "center", padding: 12, background: "#f9fafb", borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#2563eb" }}>{status.devices_count}</div>
              <div style={{ fontSize: 12, color: "#666" }}>Active Devices</div>
            </div>
            <div style={{ textAlign: "center", padding: 12, background: "#f9fafb", borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#059669" }}>{status.observations_sent}</div>
              <div style={{ fontSize: 12, color: "#666" }}>Observations Sent</div>
            </div>
            <div style={{ textAlign: "center", padding: 12, background: "#f9fafb", borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: status.errors_count > 0 ? "#dc2626" : "#666" }}>
                {status.errors_count}
              </div>
              <div style={{ fontSize: 12, color: "#666" }}>Errors</div>
            </div>
            <div style={{ textAlign: "center", padding: 12, background: "#f9fafb", borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#7c3aed" }}>{status.interval}s</div>
              <div style={{ fontSize: 12, color: "#666" }}>Interval</div>
            </div>
          </div>
        )}

        {status?.last_run && (
          <div style={{ fontSize: 12, color: "#666", marginBottom: 16 }}>
            Last run: {new Date(status.last_run).toLocaleString()}
          </div>
        )}

        {/* Controls */}
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{ fontSize: 13, color: "#333" }}>Interval (sec):</label>
            <input
              type="number"
              min={5}
              max={300}
              value={interval}
              onChange={(e) => setInterval(Number(e.target.value))}
              style={{ width: 70, padding: "6px 8px", borderRadius: 6, border: "1px solid #ddd" }}
            />
          </div>

          {status?.running ? (
            <button
              onClick={() => stopMutation.mutate()}
              disabled={stopMutation.isPending}
              style={buttonStyle(true, "#dc2626")}
            >
              {stopMutation.isPending ? "Stopping..." : "Stop Simulator"}
            </button>
          ) : (
            <button
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
              style={buttonStyle(true, "#059669")}
            >
              {startMutation.isPending ? "Starting..." : "Start Simulator"}
            </button>
          )}

          <button
            onClick={() => triggerMutation.mutate()}
            disabled={triggerMutation.isPending}
            style={buttonStyle(true)}
          >
            {triggerMutation.isPending ? "Generating..." : "Generate Once"}
          </button>

          <button
            onClick={() => resetMutation.mutate()}
            style={{ ...buttonStyle(false), background: "white", border: "1px solid #ddd" }}
          >
            Reset Stats
          </button>
        </div>
      </div>

      {/* Assigned Devices */}
      <div style={cardStyle}>
        <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Assigned Devices ({devices.length})</h3>

        {devices.length === 0 ? (
          <div style={{ padding: 20, textAlign: "center", color: "#666", background: "#f9fafb", borderRadius: 8 }}>
            No devices assigned to patients. Assign devices in Device Management to start generating vitals.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {devices.map((device) => {
              const patientFhirId = `patient-${device.patient_id}`;
              const profile = profiles[patientFhirId];
              return (
                <div
                  key={device.device_id}
                  onClick={() => setSelectedDevice(device.device_id)}
                  style={{
                    padding: 12,
                    border: selectedDevice === device.device_id ? "2px solid #2563eb" : "1px solid #eee",
                    borderRadius: 8,
                    cursor: "pointer",
                    background: selectedDevice === device.device_id ? "#eff6ff" : "white",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{device.name}</div>
                      <div style={{ fontSize: 12, color: "#666" }}>
                        {device.device_id} → {device.patient_name}
                      </div>
                      <div style={{ fontSize: 11, color: "#999", marginTop: 4 }}>
                        Capabilities: {device.capabilities?.join(", ") || "default vitals"}
                      </div>
                    </div>
                    {profile && (
                      <div style={{
                        padding: "2px 8px",
                        borderRadius: 999,
                        background: profile.condition === "normal" ? "#dcfce7" : "#fef3c7",
                        color: profile.condition === "normal" ? "#166534" : "#92400e",
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {profile.condition.toUpperCase()}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Patient Condition Control */}
      {devices.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: 16 }}>Set Patient Condition</h3>
          <div style={{ fontSize: 13, color: "#666", marginBottom: 16 }}>
            Simulate different clinical scenarios by setting patient conditions. This affects the vitals generated.
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
            <div>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4, color: "#333" }}>Device</label>
              <select
                value={selectedDevice || ""}
                onChange={(e) => setSelectedDevice(e.target.value || null)}
                style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", minWidth: 200 }}
              >
                <option value="">Select a device...</option>
                {devices.map((d) => (
                  <option key={d.device_id} value={d.device_id}>
                    {d.name} ({d.patient_name})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4, color: "#333" }}>Condition</label>
              <select
                value={selectedCondition}
                onChange={(e) => setSelectedCondition(e.target.value)}
                style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", minWidth: 150 }}
              >
                {PATIENT_CONDITIONS.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSetCondition}
              disabled={!selectedDevice || conditionMutation.isPending}
              style={buttonStyle(!!selectedDevice)}
            >
              {conditionMutation.isPending ? "Setting..." : "Set Condition"}
            </button>
          </div>

          {selectedCondition && (
            <div style={{ marginTop: 12, padding: 12, background: "#f9fafb", borderRadius: 8, fontSize: 13 }}>
              <strong>{PATIENT_CONDITIONS.find(c => c.value === selectedCondition)?.label}:</strong>{" "}
              {PATIENT_CONDITIONS.find(c => c.value === selectedCondition)?.description}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
