# Story E2-S3: Live Progress Screen (Screen 2)

**Epic:** E2 — Job Pipeline & Live Progress  
**Story ID:** E2-S3  
**Status:** review  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want to watch a job run in real time  
So that I know how many products have been processed and which are in/out of scope

---

## Acceptance Criteria

- [x] Progress bar showing done/total and % complete
- [x] Estimated time remaining (based on avg time/product so far)
- [x] Live feed panel: product name + in-scope (🟢) or excluded (🔴) badge, appears as SSE events arrive
- [x] Stats panel: running count of in-scope, excluded, errors, avg s/product
- [x] "View Results" button appears (and navigates to `/results/{id}`) when `job_complete` event received
- [x] Page is usable if user navigates directly to `/jobs/{id}` for a completed job

---

## Technical Requirements

### Files to Create

```
frontend/src/
├── pages/
│   └── JobProgress.tsx
├── components/
│   └── LiveFeed.tsx
└── lib/
    └── sse.ts                 ← useSSE hook
```

### sse.ts — useSSE Hook

```typescript
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
        isComplete: event.type === "job_complete",
      }));
      if (event.type === "job_complete") es.close();
    };
    
    es.onerror = () => {
      // EventSource auto-reconnects; onerror fires before reconnect attempt
      setState(s => ({ ...s, isConnecting: true }));
    };
    
    return () => es.close();
  }, [jobId]);

  return state;
}
```

### JobProgress.tsx Key Structure

```tsx
export default function JobProgress() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { events, isComplete, isConnecting } = useSSE(jobId!);
  const startTime = useRef(Date.now());

  // Derive state from events
  const lastProgress = [...events].reverse().find(e => e.type === "product_done")?.progress;
  const done = lastProgress?.done ?? 0;
  const total = lastProgress?.total ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const inScopeCount = events.filter(e => e.type === "product_done" && e.in_scope).length;
  const excludedCount = events.filter(e => e.type === "product_done" && !e.in_scope).length;
  const errorCount = events.filter(e => e.type === "error").length;

  const elapsed = (Date.now() - startTime.current) / 1000;
  const avgPerProduct = done > 0 ? elapsed / done : 0;
  const remainingSec = avgPerProduct * (total - done);

  const completionStats = events.find(e => e.type === "job_complete")?.stats;

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Status header */}
      <h1>{isConnecting ? "Connecting..." : isComplete ? "Complete" : "Running..."}</h1>
      
      {/* Progress bar */}
      <Progress value={pct} className="h-3 my-4" />
      <p>{done}/{total} products ({pct}%)</p>
      {!isComplete && done > 0 && (
        <p className="text-sm text-muted-foreground">
          ~{formatDuration(remainingSec)} remaining
        </p>
      )}
      
      {/* Stats panel */}
      <div className="grid grid-cols-4 gap-4 my-6">
        <StatCard label="In Scope" value={inScopeCount} color="green" />
        <StatCard label="Excluded" value={excludedCount} color="amber" />
        <StatCard label="Errors" value={errorCount} color="red" />
        <StatCard label="Avg s/product" value={avgPerProduct.toFixed(1)} />
      </div>
      
      {/* Live feed */}
      <LiveFeed events={events} />
      
      {/* View Results button */}
      {isComplete && (
        <Button onClick={() => navigate(`/results/${jobId}`)} className="mt-6">
          View Results →
        </Button>
      )}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}
```

### LiveFeed.tsx

```tsx
interface LiveFeedProps {
  events: SSEEvent[];
}

export function LiveFeed({ events }: LiveFeedProps) {
  const feedEvents = events.filter(e => e.type === "product_done" || e.type === "error");

  return (
    <div className="border rounded-lg overflow-y-auto max-h-80">
      {feedEvents.length === 0 && (
        <p className="p-4 text-muted-foreground text-sm">Waiting for first product...</p>
      )}
      {feedEvents.map((e, i) => (
        <div key={i} className="flex items-center gap-3 px-4 py-2 border-b last:border-0">
          {e.type === "error" ? (
            <span className="text-red-500 text-sm">⚠ Error: {e.url}</span>
          ) : (
            <>
              <span>{e.in_scope ? "🟢" : "🔴"}</span>
              <span className="text-sm flex-1 truncate">{e.name}</span>
              <Badge variant={e.in_scope ? "success" : "secondary"}>
                {e.in_scope ? "In scope" : "Excluded"}
              </Badge>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
```

### Direct Navigation to Completed Job

When a user navigates to `/jobs/{id}` for an already-complete job:
- SSE stream connects → backend sends `job_complete` immediately (per E2-S1 spec)
- `isComplete` becomes `true` quickly
- "View Results" button appears
- The live feed shows no product events (since none were streamed live) — that's OK

Optionally: Also fetch job status via `GET /api/jobs/{id}` on mount to show initial progress counts even before SSE connects.

---

## Implementation Tasks

- [x] Create `frontend/src/pages/JobProgress.tsx`
- [x] Create `frontend/src/components/LiveFeed.tsx`
- [x] Create `frontend/src/lib/sse.ts` — `useSSE(jobId)` hook using `EventSource`
- [x] Wire progress bar + stats to SSE state
- [x] Handle reconnect if SSE connection drops

---

## Dev Notes

### SSE Reconnect

Browser `EventSource` auto-reconnects after a connection drop. The `onerror` callback fires on each reconnect attempt. Show "Reconnecting..." status during `isConnecting`. On reconnect to a complete job, `job_complete` is sent immediately (backend handles this).

### Avoid Duplicate Events on Reconnect

`EventSource` does NOT replay missed events automatically (no `Last-Event-ID` sent by backend). Events seen before reconnect are in `state.events` array (React state). New events after reconnect are appended. This means post-reconnect duplicate `job_complete` is possible — handle by checking `isComplete` before setting it again (`s.isComplete || event.type === "job_complete"`).

### Progress Bar — Shadcn Progress

Use `<Progress value={pct} />` from Shadcn. The `value` prop is 0-100. The bar is determinate (shows actual %).

### Stats Panel Grid

Use 4-column grid (`grid-cols-4`) on desktop, 2-column on mobile (`grid-cols-2 md:grid-cols-4`). Each stat is a simple card with label + value.

### Estimated Time Remaining

Calculate based on real elapsed time since the page mounted (`useRef(Date.now())`), not from the SSE `duration_sec` (which is only available in `job_complete`). Reset on reconnect? No — keep the original start time. This gives a reasonable estimate.

### UX: Never Show Passive Spinner

Per the UX spec: never show a spinner-only state. Always show explicit text status:
- "Connecting..." when `isConnecting`
- "Running — processing products..." when connected and not complete
- "Complete" when `isComplete`

---

## Dev Agent Record

### Implementation Plan

Implemented all five tasks from the story spec in a single session:

1. `frontend/src/lib/sse.ts` — `useSSE` hook using browser `EventSource`. Guards against duplicate `job_complete` on reconnect via `s.isComplete || event.type === "job_complete"`. Auto-reconnect is handled natively by `EventSource`; `onerror` sets `isConnecting: true` to show reconnect status.

2. `frontend/src/components/ui/progress.tsx` — Shadcn-style `Progress` component (not pre-existing in the project). Uses a `div`-based approach with `forwardRef`, clamps value 0–100, `h-full` inner bar driven by inline `width` style.

3. `frontend/src/components/LiveFeed.tsx` — scrollable feed of `product_done` and `error` events. Uses the project's existing `Badge` component (variant `"green"` / `"secondary"`).

4. `frontend/src/pages/JobProgress.tsx` — full page deriving all state from the `SSEState.events` array. Progress bar, 2×4 stats grid, live feed, and "View Results" button.

5. `frontend/src/App.tsx` — replaced `/jobs/:jobId` `PlaceholderPage` with the real `<JobProgress />` component.

TypeScript type check (`tsc --noEmit`) passes with exit code 0.

**Frontend tests:** No test framework (Vitest/Jest) is configured in this project. No frontend test files exist. Tests would need a separate setup story.

### Completion Notes

All 5 implementation tasks checked. All acceptance criteria satisfied:
- ✅ Progress bar with done/total and %
- ✅ Estimated time remaining displayed while running
- ✅ Live feed with 🟢/🔴 badges per event
- ✅ Stats panel: in-scope, excluded, errors, avg s/product
- ✅ "View Results" button on job_complete
- ✅ Direct navigation to completed job works (SSE reconnect → immediate job_complete)

### Debug Log

No blocking issues. One deviation from spec: Badge `variant="success"` doesn't exist in the project's badge.tsx; used `variant="green"` which is defined.

---

## File List

- `frontend/src/lib/sse.ts` (created)
- `frontend/src/components/ui/progress.tsx` (created)
- `frontend/src/components/LiveFeed.tsx` (created)
- `frontend/src/pages/JobProgress.tsx` (created)
- `frontend/src/App.tsx` (modified)

---

## Change Log

- 2026-04-25: Implemented E2-S3 Live Progress Screen — SSE hook, Progress component, LiveFeed, JobProgress page, App routing wired (Srini / AI)
