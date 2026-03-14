import { AgentMonitor } from "@/components/agents/AgentMonitor";

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Agent Monitor</h1>
        <span className="flex items-center gap-1.5 text-sm text-green-600">
          <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
          Live
        </span>
      </div>
      <AgentMonitor />
    </div>
  );
}
