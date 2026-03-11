"use client";

export function TopBar() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div>
        <h1 className="text-sm font-medium text-gray-500">Clinician Dashboard</h1>
      </div>
      <div className="flex items-center gap-4">
        {/* Connection indicator */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          Live
        </div>
        {/* User avatar placeholder */}
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-healthos-100 text-sm font-medium text-healthos-700">
          C
        </div>
      </div>
    </header>
  );
}
