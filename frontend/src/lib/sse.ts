import { useState, useEffect } from "react";

export interface SSEEvent {
  type: "product_done" | "job_complete" | "error" | "ping";
  // product_done
  name?: string;
  in_scope?: boolean;
  progress?: { done: number; total: number };
  // job_complete
  stats?: { in_scope: number; excluded: number; duration_sec: number };
  // error
  url?: string;
  message?: string;
}

export interface SSEState {
  events: SSEEvent[];
  isComplete: boolean;
  isConnecting: boolean;
  error: string | null;
}

export function useSSE(jobId: string): SSEState {
  const [state, setState] = useState<SSEState>({
    events: [],
    isComplete: false,
    isConnecting: true,
    error: null,
  });

  useEffect(() => {
    const es = new EventSource(`/api/jobs/${jobId}/stream`);

    es.onopen = () => setState(s => ({ ...s, isConnecting: false }));

    es.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data);
      setState(s => ({
        ...s,
        events: [...s.events, event],
        // Guard against duplicate job_complete on reconnect
        isComplete: s.isComplete || event.type === "job_complete",
      }));
      if (event.type === "job_complete") es.close();
    };

    // EventSource auto-reconnects; onerror fires before each reconnect attempt
    es.onerror = () => {
      setState(s => ({ ...s, isConnecting: true }));
    };

    return () => es.close();
  }, [jobId]);

  return state;
}
