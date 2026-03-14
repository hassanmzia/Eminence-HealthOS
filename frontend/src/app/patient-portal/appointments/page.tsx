"use client";

import { useEffect, useState } from "react";
import {
  fetchPatientAppointments,
  requestAppointment,
  type PatientAppointment,
} from "@/lib/patient-api";

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<PatientAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRequestForm, setShowRequestForm] = useState(false);

  useEffect(() => {
    fetchPatientAppointments()
      .then(setAppointments)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const now = new Date().toISOString();
  const upcoming = appointments.filter(
    (a) => a.scheduled_at && a.scheduled_at >= now && a.status !== "completed",
  );
  const past = appointments
    .filter((a) => a.status === "completed" || (a.scheduled_at && a.scheduled_at < now))
    .slice(0, 5);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-healthos-200 border-t-healthos-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">Unable to load appointments. Please try again later.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Appointments</h1>
          <p className="mt-1 text-sm text-gray-500">
            View and manage your upcoming and past appointments.
          </p>
        </div>
        <button
          onClick={() => setShowRequestForm(!showRequestForm)}
          className="rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700"
        >
          Request Appointment
        </button>
      </div>

      {/* Request form */}
      {showRequestForm && (
        <RequestAppointmentForm
          onClose={() => setShowRequestForm(false)}
          onSuccess={(appt) => {
            setShowRequestForm(false);
            // Refresh list
            fetchPatientAppointments().then(setAppointments).catch(() => {});
          }}
        />
      )}

      {/* Upcoming */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Upcoming Appointments
        </h2>
        {upcoming.length === 0 ? (
          <p className="text-sm text-gray-500">No upcoming appointments.</p>
        ) : (
          <div className="space-y-3">
            {upcoming.map((appt) => (
              <AppointmentRow key={appt.id} appointment={appt} showActions />
            ))}
          </div>
        )}
      </section>

      {/* Past */}
      <section className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Past Appointments
        </h2>
        {past.length === 0 ? (
          <p className="text-sm text-gray-500">No past appointments.</p>
        ) : (
          <div className="space-y-3">
            {past.map((appt) => (
              <AppointmentRow key={appt.id} appointment={appt} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────

function AppointmentRow({
  appointment,
  showActions,
}: {
  appointment: PatientAppointment;
  showActions?: boolean;
}) {
  const statusColors: Record<string, string> = {
    scheduled: "bg-blue-100 text-blue-700",
    confirmed: "bg-green-100 text-green-700",
    completed: "bg-gray-100 text-gray-600",
    cancelled: "bg-red-100 text-red-600",
    in_progress: "bg-yellow-100 text-yellow-700",
  };

  const isVirtual =
    appointment.type?.toLowerCase().includes("telehealth") ||
    appointment.type?.toLowerCase().includes("virtual");

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-gray-900 capitalize">
            {appointment.type ?? "Appointment"}
          </p>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[appointment.status] ?? "bg-gray-100 text-gray-600"}`}
          >
            {appointment.status}
          </span>
          {isVirtual && (
            <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
              Virtual
            </span>
          )}
        </div>
        {appointment.reason && (
          <p className="mt-1 text-xs text-gray-500">{appointment.reason}</p>
        )}
        <p className="mt-1 text-xs text-gray-400">
          {appointment.scheduled_at
            ? new Date(appointment.scheduled_at).toLocaleString()
            : "Date TBD"}
        </p>
      </div>
      {showActions && isVirtual && appointment.status !== "completed" && (
        <button className="ml-4 shrink-0 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700">
          Join Telehealth
        </button>
      )}
    </div>
  );
}

function RequestAppointmentForm({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (appt: { message: string; appointment_id: string }) => void;
}) {
  const [type, setType] = useState("office_visit");
  const [reason, setReason] = useState("");
  const [preferredDate, setPreferredDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await requestAppointment({
        type,
        reason,
        preferred_date: preferredDate || undefined,
      });
      onSuccess(result);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Failed to request appointment");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-healthos-200 bg-healthos-50 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Request an Appointment
        </h3>
        <button
          onClick={onClose}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Visit Type
          </label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          >
            <option value="office_visit">Office Visit</option>
            <option value="telehealth">Telehealth</option>
            <option value="follow_up">Follow-up</option>
            <option value="lab_work">Lab Work</option>
            <option value="specialist">Specialist Referral</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Reason
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Describe the reason for your visit..."
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Preferred Date (optional)
          </label>
          <input
            type="date"
            value={preferredDate}
            onChange={(e) => setPreferredDate(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
        </div>
        {submitError && (
          <p className="text-sm text-red-600">{submitError}</p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-healthos-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-healthos-700 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Submit Request"}
        </button>
      </form>
    </div>
  );
}
