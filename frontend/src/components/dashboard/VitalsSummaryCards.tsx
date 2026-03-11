"use client";

const SUMMARY_CARDS = [
  { label: "Active Patients", value: "148", change: "+12 this week", color: "text-healthos-600" },
  { label: "Vitals Today", value: "2,847", change: "94% on schedule", color: "text-green-600" },
  { label: "Open Alerts", value: "19", change: "7 critical/high", color: "text-orange-600" },
  { label: "Agent Decisions", value: "1,204", change: "99.2% auto-resolved", color: "text-purple-600" },
];

export function VitalsSummaryCards() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {SUMMARY_CARDS.map((card) => (
        <div key={card.label} className="card">
          <p className="text-sm font-medium text-gray-500">{card.label}</p>
          <p className={`mt-1 text-2xl font-bold ${card.color}`}>{card.value}</p>
          <p className="mt-1 text-xs text-gray-400">{card.change}</p>
        </div>
      ))}
    </div>
  );
}
