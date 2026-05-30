"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import type { GuardianEvent } from "@/lib/types";

export type StreamStatus = "connecting" | "open" | "closed";

interface UseEventStream {
  events: GuardianEvent[];
  status: StreamStatus;
}

/**
 * Subscribes to the backend SSE endpoint (GET /events/sse) and accumulates
 * events newest-first. Reconnection is handled natively by EventSource.
 */
export function useEventStream(maxEvents = 200): UseEventStream {
  const [events, setEvents] = useState<GuardianEvent[]>([]);
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const idRef = useRef(0);

  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/events/sse`);

    source.onopen = () => setStatus("open");
    source.onmessage = (e) => {
      let parsed: Partial<GuardianEvent> = {};
      try {
        parsed = JSON.parse(e.data) as Partial<GuardianEvent>;
      } catch {
        parsed = { summary: e.data };
      }
      const event: GuardianEvent = {
        id: parsed.id ?? `${Date.now()}-${idRef.current++}`,
        kind: parsed.kind ?? "message",
        ts: parsed.ts ?? new Date().toISOString(),
        summary: parsed.summary,
        payload: parsed.payload,
      };
      setEvents((prev) => [event, ...prev].slice(0, maxEvents));
    };
    source.onerror = () => {
      // EventSource auto-retries; reflect the transient drop in the UI.
      setStatus(source.readyState === EventSource.CLOSED ? "closed" : "connecting");
    };

    return () => source.close();
  }, [maxEvents]);

  return { events, status };
}
