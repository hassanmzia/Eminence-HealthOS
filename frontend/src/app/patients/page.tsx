"use client";

import { useState } from "react";
import { PatientList } from "@/components/patients/PatientList";

export default function PatientsPage() {
  const [search, setSearch] = useState("");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Patients</h1>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search patients..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-healthos-500 focus:outline-none focus:ring-1 focus:ring-healthos-500"
          />
        </div>
      </div>
      <PatientList search={search} />
    </div>
  );
}
