import { PatientHeader } from "@/components/patients/PatientHeader";
import { VitalsTrendChart } from "@/components/patients/VitalsTrendChart";
import { RiskScoreGauge } from "@/components/patients/RiskScoreGauge";
import { PatientAlerts } from "@/components/patients/PatientAlerts";

interface PatientDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function PatientDetailPage({ params }: PatientDetailPageProps) {
  const { id } = await params;

  return (
    <div className="space-y-6">
      <PatientHeader patientId={id} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Vitals chart — spans 2 columns */}
        <div className="lg:col-span-2">
          <VitalsTrendChart patientId={id} />
        </div>

        {/* Risk score gauge */}
        <div>
          <RiskScoreGauge patientId={id} />
        </div>
      </div>

      {/* Patient alerts */}
      <PatientAlerts patientId={id} />
    </div>
  );
}
