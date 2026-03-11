"use client";

const SERVICES = [
  { name: "API Server", status: "healthy", latency: "12ms" },
  { name: "PostgreSQL", status: "healthy", latency: "3ms" },
  { name: "Redis", status: "healthy", latency: "1ms" },
  { name: "Kafka", status: "healthy", latency: "8ms" },
  { name: "Qdrant", status: "healthy", latency: "15ms" },
];

export function SystemHealthWidget() {
  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">System Health</h2>
      <div className="space-y-2">
        {SERVICES.map((svc) => (
          <div key={svc.name} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  svc.status === "healthy" ? "bg-green-500" : "bg-red-500"
                }`}
              />
              <span className="text-gray-700">{svc.name}</span>
            </div>
            <span className="text-gray-400">{svc.latency}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
