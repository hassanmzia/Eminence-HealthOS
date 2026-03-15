"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { startVideoSession, endVideoSession } from "@/lib/api";

export type VideoState = "idle" | "connecting" | "connected" | "error";

interface VideoSessionState {
  state: VideoState;
  roomUrl: string | null;
  token: string | null;
  isMuted: boolean;
  isCameraOff: boolean;
  error: string | null;
  demoMode: boolean;
}

export function useVideoSession(sessionId?: string) {
  const [video, setVideo] = useState<VideoSessionState>({
    state: "idle",
    roomUrl: null,
    token: null,
    isMuted: false,
    isCameraOff: false,
    error: null,
    demoMode: false,
  });

  const callFrameRef = useRef<ReturnType<typeof import("@daily-co/daily-js").default.createFrame> | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const startVisit = useCallback(async () => {
    if (!sessionId) return;
    setVideo((v) => ({ ...v, state: "connecting", error: null }));

    try {
      const result = await startVideoSession(sessionId);
      const roomUrl = result.room_url as string;
      const token = result.token as string;
      const demoMode = result.demo_mode as boolean ?? true;

      setVideo((v) => ({
        ...v,
        roomUrl,
        token,
        demoMode,
        state: "connected",
      }));

      // If Daily.co SDK is available and not in demo mode, create the call frame
      if (!demoMode && containerRef.current) {
        try {
          const DailyIframe = (await import("@daily-co/daily-js")).default;
          const frame = DailyIframe.createFrame(containerRef.current, {
            iframeStyle: {
              width: "100%",
              height: "100%",
              border: "0",
              borderRadius: "0.5rem",
            },
            showLeaveButton: false,
            showFullscreenButton: true,
          });
          callFrameRef.current = frame;
          await frame.join({ url: roomUrl, token });
        } catch {
          // SDK not installed or failed — stay in connected state with demo UI
        }
      }
    } catch {
      // API unavailable — enter demo connected state
      setVideo((v) => ({
        ...v,
        state: "connected",
        roomUrl: `https://demo.daily.co/healthos-${sessionId}`,
        token: "demo_token",
        demoMode: true,
      }));
    }
  }, [sessionId]);

  const endVisit = useCallback(async () => {
    if (callFrameRef.current) {
      try {
        await callFrameRef.current.leave();
        callFrameRef.current.destroy();
      } catch {
        // ignore cleanup errors
      }
      callFrameRef.current = null;
    }

    if (sessionId) {
      try {
        await endVideoSession(sessionId);
      } catch {
        // API unavailable
      }
    }

    setVideo({
      state: "idle",
      roomUrl: null,
      token: null,
      isMuted: false,
      isCameraOff: false,
      error: null,
      demoMode: false,
    });
  }, [sessionId]);

  const toggleMute = useCallback(() => {
    if (callFrameRef.current) {
      const newMuted = !video.isMuted;
      callFrameRef.current.setLocalAudio(!newMuted);
    }
    setVideo((v) => ({ ...v, isMuted: !v.isMuted }));
  }, [video.isMuted]);

  const toggleCamera = useCallback(() => {
    if (callFrameRef.current) {
      const newOff = !video.isCameraOff;
      callFrameRef.current.setLocalVideo(!newOff);
    }
    setVideo((v) => ({ ...v, isCameraOff: !v.isCameraOff }));
  }, [video.isCameraOff]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (callFrameRef.current) {
        try {
          callFrameRef.current.leave();
          callFrameRef.current.destroy();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  return {
    ...video,
    containerRef,
    startVisit,
    endVisit,
    toggleMute,
    toggleCamera,
  };
}
