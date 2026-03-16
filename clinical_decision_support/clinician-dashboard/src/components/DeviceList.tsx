import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchDevices, deleteDevice, unassignDevice, DEVICE_TYPES, type Device } from "../lib/deviceApi";

interface DeviceListProps {
  onSelectDevice: (device: Device) => void;
  onCreateNew: () => void;
  onAssign: (device: Device) => void;
}

export function DeviceList({ onSelectDevice, onCreateNew, onAssign }: DeviceListProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [assignedFilter, setAssignedFilter] = useState<string>("");
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["devices", search, statusFilter, typeFilter, assignedFilter],
    queryFn: () => fetchDevices({
      search: search || undefined,
      status: statusFilter || undefined,
      type: typeFilter || undefined,
      assigned: assignedFilter || undefined,
      limit: 100
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDevice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });

  const unassignMutation = useMutation({
    mutationFn: (deviceId: number) => unassignDevice(deviceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });

  const handleDelete = (device: Device) => {
    if (confirm(`Are you sure you want to retire device "${device.name}"?`)) {
      deleteMutation.mutate(device.id);
    }
  };

  const handleUnassign = (device: Device) => {
    if (confirm(`Unassign "${device.name}" from ${device.assigned_patient_name}?`)) {
      unassignMutation.mutate(device.id);
    }
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, { bg: string; fg: string }> = {
      active: { bg: "#e9f7ef", fg: "#1f7a3a" },
      inactive: { bg: "#f5f5f5", fg: "#666" },
      maintenance: { bg: "#fff3d6", fg: "#8a5a00" },
      retired: { bg: "#ffe5e5", fg: "#9b1c1c" },
    };
    const c = colors[status] || colors.inactive;
    return (
      <span style={{ padding: "2px 8px", borderRadius: 999, background: c.bg, color: c.fg, fontSize: 11, fontWeight: 600 }}>
        {status.toUpperCase()}
      </span>
    );
  };

  const getDeviceTypeLabel = (type: string) => {
    return DEVICE_TYPES.find(t => t.value === type)?.label || type;
  };

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Device Management</h2>
        <button
          onClick={onCreateNew}
          style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: "pointer" }}
        >
          + Add Device
        </button>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search by name, ID, or serial..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: 200, padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd" }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd" }}
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="maintenance">Maintenance</option>
          <option value="retired">Retired</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd" }}
        >
          <option value="">All Types</option>
          {DEVICE_TYPES.map(t => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <select
          value={assignedFilter}
          onChange={(e) => setAssignedFilter(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #ddd" }}
        >
          <option value="">All Devices</option>
          <option value="true">Assigned</option>
          <option value="false">Unassigned</option>
        </select>
      </div>

      {isLoading && <div style={{ padding: 20, textAlign: "center", color: "#666" }}>Loading devices...</div>}

      {error && (
        <div style={{ padding: 12, background: "#ffe5e5", borderRadius: 8, color: "#9b1c1c" }}>
          Failed to load devices. Please try again.
        </div>
      )}

      {data && (
        <>
          <div style={{ marginBottom: 12, fontSize: 13, color: "#666" }}>
            Showing {data.results.length} of {data.total} devices
          </div>

          <div className="table-responsive" style={{ border: "1px solid #eee", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#f9f9f9" }}>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Device ID</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Name</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Type</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Location</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Assigned To</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Status</th>
                  <th style={{ padding: 12, textAlign: "left", borderBottom: "1px solid #eee" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((device) => (
                  <tr key={device.id} style={{ cursor: "pointer" }} onClick={() => onSelectDevice(device)}>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", fontFamily: "monospace", fontSize: 13 }}>
                      {device.device_id}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", fontWeight: 500 }}>
                      {device.name}
                      {device.manufacturer && (
                        <div style={{ fontSize: 12, color: "#666" }}>{device.manufacturer}</div>
                      )}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", fontSize: 13 }}>
                      {getDeviceTypeLabel(device.device_type)}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee", fontSize: 13 }}>
                      {device.facility && <div>{device.facility}</div>}
                      {(device.room || device.bed) && (
                        <div style={{ color: "#666" }}>
                          {[device.department, device.room && `Room ${device.room}`, device.bed && `Bed ${device.bed}`]
                            .filter(Boolean).join(", ")}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                      {device.assigned_patient_name ? (
                        <span style={{ padding: "2px 8px", borderRadius: 999, background: "#e0f2fe", color: "#0369a1", fontSize: 12 }}>
                          {device.assigned_patient_name}
                        </span>
                      ) : (
                        <span style={{ color: "#999", fontSize: 12 }}>Unassigned</span>
                      )}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee" }}>
                      {statusBadge(device.status)}
                      {device.battery_level !== null && device.battery_level !== undefined && (
                        <div style={{ fontSize: 11, color: device.battery_level < 20 ? "#dc2626" : "#666", marginTop: 4 }}>
                          Battery: {device.battery_level}%
                        </div>
                      )}
                    </td>
                    <td style={{ padding: 12, borderBottom: "1px solid #eee" }} onClick={(e) => e.stopPropagation()}>
                      <div style={{ display: "flex", gap: 6 }}>
                        {device.assigned_patient_id ? (
                          <button
                            onClick={() => handleUnassign(device)}
                            style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #ddd", background: "white", cursor: "pointer", fontSize: 12 }}
                          >
                            Unassign
                          </button>
                        ) : (
                          <button
                            onClick={() => onAssign(device)}
                            style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #2563eb", background: "#eff6ff", color: "#2563eb", cursor: "pointer", fontSize: 12 }}
                          >
                            Assign
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(device)}
                          style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #ddd", background: "white", cursor: "pointer", fontSize: 12 }}
                        >
                          Retire
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: 40, textAlign: "center", color: "#666" }}>
                      No devices found. Add a new device to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
