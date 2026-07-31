"use client";

import { useEffect, useState } from "react";

import { streamUrl } from "./api";

type StreamEvent = {
  event: string;
  kind?: string;
  seq?: number;
  status?: string;
  payload?: any;
  detail?: string;
};

export function useRunStream(runId: number): StreamEvent[] {
  const [events, setEvents] = useState<StreamEvent[]>([]);

  useEffect(() => {
    setEvents([]);
    const source = new EventSource(streamUrl(runId));
    source.onmessage = (e) => {
      try {
        setEvents((prev) => [...prev, JSON.parse(e.data)]);
      } catch {
        // ignore malformed frames
      }
    };
    source.onerror = () => source.close();
    return () => source.close();
  }, [runId]);

  return events;
}
