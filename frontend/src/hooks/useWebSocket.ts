"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSEvent } from "@/types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:4090";

interface UseWebSocketOptions {
  orgId: string;
  onEvent?: (event: WSEvent) => void;
  reconnectInterval?: number;
}

export function useWebSocket({ orgId, onEvent, reconnectInterval = 3000 }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/${orgId}`);

    ws.onopen = () => setConnected(true);

    ws.onmessage = (event) => {
      try {
        const parsed: WSEvent = JSON.parse(event.data);
        setLastEvent(parsed);
        onEvent?.(parsed);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, reconnectInterval);
    };

    ws.onerror = () => ws.close();

    wsRef.current = ws;
  }, [orgId, onEvent, reconnectInterval]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { connected, lastEvent };
}
