"use client";

import { useState, useEffect, createContext, useContext } from "react";

type Breakpoint = "xs" | "sm" | "md" | "lg" | "xl" | "2xl";

interface ResponsiveContextValue {
  breakpoint: Breakpoint;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  width: number;
}

const ResponsiveContext = createContext<ResponsiveContextValue>({
  breakpoint: "lg",
  isMobile: false,
  isTablet: false,
  isDesktop: true,
  width: 1024,
});

export function useResponsive() {
  return useContext(ResponsiveContext);
}

function getBreakpoint(width: number): Breakpoint {
  if (width < 640) return "xs";
  if (width < 768) return "sm";
  if (width < 1024) return "md";
  if (width < 1280) return "lg";
  if (width < 1536) return "xl";
  return "2xl";
}

export function ResponsiveProvider({ children }: { children: React.ReactNode }) {
  const [width, setWidth] = useState(typeof window !== "undefined" ? window.innerWidth : 1024);

  useEffect(() => {
    const handleResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const breakpoint = getBreakpoint(width);
  const isMobile = width < 768;
  const isTablet = width >= 768 && width < 1024;
  const isDesktop = width >= 1024;

  return (
    <ResponsiveContext.Provider value={{ breakpoint, isMobile, isTablet, isDesktop, width }}>
      {children}
    </ResponsiveContext.Provider>
  );
}

/** Responsive grid that adjusts columns based on screen size */
export function ResponsiveGrid({
  children,
  className = "",
  minColWidth = 300,
}: {
  children: React.ReactNode;
  className?: string;
  minColWidth?: number;
}) {
  return (
    <div
      className={`grid gap-4 ${className}`}
      style={{ gridTemplateColumns: `repeat(auto-fit, minmax(${minColWidth}px, 1fr))` }}
    >
      {children}
    </div>
  );
}

/** Stacks children vertically on mobile, horizontally on desktop */
export function ResponsiveStack({
  children,
  className = "",
  gap = "gap-4",
  breakAt = "md",
}: {
  children: React.ReactNode;
  className?: string;
  gap?: string;
  breakAt?: "sm" | "md" | "lg";
}) {
  const flexDir = breakAt === "sm" ? "sm:flex-row" : breakAt === "lg" ? "lg:flex-row" : "md:flex-row";
  return (
    <div className={`flex flex-col ${flexDir} ${gap} ${className}`}>
      {children}
    </div>
  );
}

/** Shows/hides content based on breakpoint */
export function ShowAbove({ breakpoint, children }: { breakpoint: "sm" | "md" | "lg" | "xl"; children: React.ReactNode }) {
  const classes: Record<string, string> = {
    sm: "hidden sm:block",
    md: "hidden md:block",
    lg: "hidden lg:block",
    xl: "hidden xl:block",
  };
  return <div className={classes[breakpoint]}>{children}</div>;
}

export function ShowBelow({ breakpoint, children }: { breakpoint: "sm" | "md" | "lg" | "xl"; children: React.ReactNode }) {
  const classes: Record<string, string> = {
    sm: "sm:hidden",
    md: "md:hidden",
    lg: "lg:hidden",
    xl: "xl:hidden",
  };
  return <div className={classes[breakpoint]}>{children}</div>;
}

/** Touch-friendly tap target wrapper */
export function TapTarget({
  children,
  onClick,
  className = "",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`min-h-[44px] min-w-[44px] touch-manipulation ${className}`}
    >
      {children}
    </button>
  );
}

/** Pull-to-refresh component for mobile */
export function PullToRefresh({
  onRefresh,
  children,
}: {
  onRefresh: () => Promise<void>;
  children: React.ReactNode;
}) {
  const [pulling, setPulling] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const threshold = 80;

  useEffect(() => {
    let startY = 0;
    const container = document.querySelector("main");
    if (!container) return;

    const handleTouchStart = (e: TouchEvent) => {
      if (container.scrollTop === 0) {
        startY = e.touches[0].clientY;
        setPulling(true);
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!pulling) return;
      const currentY = e.touches[0].clientY;
      const distance = Math.max(0, currentY - startY);
      setPullDistance(Math.min(distance, threshold * 1.5));
    };

    const handleTouchEnd = async () => {
      if (pullDistance >= threshold && !refreshing) {
        setRefreshing(true);
        await onRefresh();
        setRefreshing(false);
      }
      setPulling(false);
      setPullDistance(0);
    };

    container.addEventListener("touchstart", handleTouchStart, { passive: true });
    container.addEventListener("touchmove", handleTouchMove, { passive: true });
    container.addEventListener("touchend", handleTouchEnd);

    return () => {
      container.removeEventListener("touchstart", handleTouchStart);
      container.removeEventListener("touchmove", handleTouchMove);
      container.removeEventListener("touchend", handleTouchEnd);
    };
  }, [pulling, pullDistance, refreshing, onRefresh]);

  return (
    <div>
      {/* Pull indicator */}
      {(pulling || refreshing) && (
        <div
          className="flex items-center justify-center overflow-hidden transition-all"
          style={{ height: refreshing ? 48 : pullDistance * 0.5 }}
        >
          {refreshing ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 dark:border-gray-600 border-t-healthos-600" />
          ) : (
            <svg
              className="h-5 w-5 text-gray-500 dark:text-gray-400 transition-transform"
              style={{ transform: `rotate(${(pullDistance / threshold) * 180}deg)` }}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5 12 21m0 0-7.5-7.5M12 21V3" />
            </svg>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

/** Bottom sheet for mobile (replaces modals on small screens) */
export function BottomSheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] md:hidden">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute bottom-0 left-0 right-0 animate-slide-up rounded-t-2xl bg-white dark:bg-gray-900 max-h-[85vh] overflow-hidden">
        {/* Handle bar */}
        <div className="flex justify-center pt-3 pb-2">
          <div className="h-1 w-10 rounded-full bg-gray-300 dark:bg-gray-600" />
        </div>
        {title && (
          <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 pb-3 dark:border-gray-700">
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
            <button onClick={onClose} className="rounded-lg p-1 text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-300">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
        <div className="overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}
