"use client";

export function TopBar({ onMenuToggle }: { onMenuToggle?: () => void } = {}) {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        {/* Mobile hamburger menu */}
        <button
          onClick={onMenuToggle}
          className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden"
          aria-label="Toggle sidebar"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
        <h1 className="text-sm font-medium text-gray-500">Clinician Dashboard</h1>
      </div>
      <div className="flex items-center gap-4">
        {/* Connection indicator */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          <span className="hidden sm:inline">Live</span>
        </div>
        {/* User avatar placeholder */}
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-healthos-100 text-sm font-medium text-healthos-700">
          C
        </div>
      </div>
    </header>
  );
}
