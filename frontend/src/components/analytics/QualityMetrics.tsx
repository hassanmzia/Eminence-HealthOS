"use client";

const HEDIS_MEASURES = [
  { measure: "Blood Pressure Control", rate: 0.74, target: 0.70, met: true },
  { measure: "Diabetes HbA1c Control", rate: 0.62, target: 0.65, met: false },
  { measure: "Preventive Screenings", rate: 0.78, target: 0.80, met: false },
  { measure: "Medication Adherence", rate: 0.83, target: 0.80, met: true },
  { measure: "Follow-Up After Discharge", rate: 0.71, target: 0.75, met: false },
  { measure: "Care Plan Completion", rate: 0.88, target: 0.85, met: true },
];

export function QualityMetrics() {
  const overallScore = HEDIS_MEASURES.reduce((s, m) => s + m.rate, 0) / HEDIS_MEASURES.length;
  const metCount = HEDIS_MEASURES.filter((m) => m.met).length;

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Quality Metrics</h2>
        <div className="flex items-center gap-2">
          <span className="rounded bg-healthos-50 px-2 py-0.5 text-xs font-medium text-healthos-700">
            {metCount}/{HEDIS_MEASURES.length} targets met
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {HEDIS_MEASURES.map((m) => (
          <div key={m.measure}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-medium text-gray-900">{m.measure}</span>
              <div className="flex items-center gap-2">
                <span className={m.met ? "text-green-600" : "text-red-600"}>
                  {(m.rate * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-gray-400">/ {(m.target * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div className="relative h-2 rounded-full bg-gray-100">
              <div
                className={`h-2 rounded-full ${m.met ? "bg-green-500" : "bg-red-400"}`}
                style={{ width: `${m.rate * 100}%` }}
              />
              <div
                className="absolute top-0 h-2 w-0.5 bg-gray-400"
                style={{ left: `${m.target * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-lg bg-gray-50 p-3">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">Overall Quality Score</span>
          <span className="text-lg font-bold text-healthos-600">{overallScore.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}
