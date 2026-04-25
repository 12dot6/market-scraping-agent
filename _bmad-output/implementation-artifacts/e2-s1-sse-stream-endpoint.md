# Story E2-S1: SSE Stream Endpoint

**Epic:** E2 — Job Pipeline & Live Progress  
**Story ID:** E2-S1  
**Status:** review  
**Date Created:** 2026-04-25

---

## User Story

As a frontend  
I want a Server-Sent Events stream for job progress  
So that the UI can display live updates without polling

---

## Acceptance Criteria

- [ ] `GET /api/jobs/{id}/stream` sends SSE events:
  - `product_done`: `{type, name, in_scope, progress: {done, total}}`
  - `job_complete`: `{type, stats: {in_scope, excluded, duration_sec}}`
  - `error`: `{type, url, message}`
- [ ] Stream closes cleanly when job completes or client disconnects
- [ ] If job is already complete when client connects, sends `job_complete` immediately

---

## Technical Requirements

### Dependencies

- `sse-starlette` (already in requirements.txt from E1-S1): `EventSourceResponse`

### Files to Create/Modify

```
backend/
├── routers/
│   └── stream.py              ← new SSE endpoint
└── services/
    └── job_runner.py          ← MODIFY: add event queue per job_id
```

### In-Memory Event Queue

Modify `job_runner.py` to publish events to an asyncio queue per job:

```python
import asyncio
from collections import defaultdict

# In-memory queues: job_id → list of asyncio.Queue (one per SSE client)
_job_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

def register_queue(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _job_queues[job_id].append(q)
    return q

def unregister_queue(job_id: str, q: asyncio.Queue):
    if job_id in _job_queues:
        _job_queues[job_id].discard(q)  # use list.remove()

async def _publish(job_id: str, event: dict):
    for q in _job_queues.get(job_id, []):
        await q.put(event)
```

### Events Published from job_runner.py

After processing each product in `run_job()`:

```python
# After product persisted:
await _publish(job_id, {
    "type": "product_done",
    "name": product.name or url,
    "in_scope": classify_result["in_scope"],
    "progress": {"done": job.processed, "total": job.url_count}
})

# On error:
await _publish(job_id, {
    "type": "error",
    "url": url,
    "message": str(e)
})

# After job loop completes:
duration = (job.completed_at - job.started_at).total_seconds()
await _publish(job_id, {
    "type": "job_complete",
    "stats": {
        "in_scope": job.in_scope,
        "excluded": job.excluded,
        "duration_sec": round(duration, 1)
    }
})
```

### routers/stream.py

```python
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job
from backend.services.job_runner import register_queue, unregister_queue
import asyncio, json

router = APIRouter(prefix="/api/jobs", tags=["stream"])

@router.get("/{job_id}/stream")
async def stream_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If already complete, send job_complete immediately
    if job.status in ("complete", "failed"):
        async def immediate():
            duration = 0.0
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "job_complete",
                    "stats": {
                        "in_scope": job.in_scope,
                        "excluded": job.excluded,
                        "duration_sec": round(duration, 1)
                    }
                })
            }
        return EventSourceResponse(immediate())
    
    # Live streaming
    queue = register_queue(job_id)
    
    async def generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"event": "message", "data": json.dumps(event)}
                    if event["type"] == "job_complete":
                        break
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}  # keepalive
        finally:
            unregister_queue(job_id, queue)
    
    return EventSourceResponse(generator())
```

### Register Router in main.py

```python
from backend.routers import stream
app.include_router(stream.router)
```

---

## Implementation Tasks

- [x] Create `backend/routers/stream.py` with `EventSourceResponse` (via `sse-starlette`)
- [x] Modify `job_runner.py` to publish events to an in-memory queue per `job_id`
- [x] Handle client disconnect without crashing the background task
- [x] Register stream router in `main.py`

---

## Dev Notes

### sse-starlette EventSourceResponse

`EventSourceResponse` takes an async generator that yields dicts with `"event"` and `"data"` keys. `data` must be a string. Use `json.dumps()` for structured data.

### Client Disconnect

When the client disconnects mid-stream, the async generator raises `asyncio.CancelledError` on the next `await`. The `finally` block in `generator()` handles cleanup (unregistering the queue). Do NOT suppress `CancelledError`.

The background task (`run_job`) is unaffected by client disconnect — it continues running. The published events simply go to an empty queue list after cleanup.

### Thread Safety: BackgroundTask vs SSE Event Loop

`run_job()` runs in the thread pool (sync) or as an asyncio task. The `_publish()` function is `async def` and must be called with `await`. If `run_job` is sync, use `asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, event)` instead of `await _publish()`.

Make `run_job` a proper async function or handle cross-thread queue access carefully.

### 30s Timeout + Ping

The `asyncio.wait_for(queue.get(), timeout=30)` with ping keepalive prevents the SSE connection from timing out on slow scraping jobs. SSE connections that go silent for >60s are typically dropped by proxies/load balancers.

### Reconnect Behavior (Frontend Side)

EventSource auto-reconnects. When the frontend reconnects to a completed job, the `if job.status in ("complete", "failed")` branch sends `job_complete` immediately, so reconnect works correctly.

---

## Dev Agent Record

### Implementation Notes

- `_job_queues` is a `defaultdict(list)` mapping `job_id → list[asyncio.Queue]`, one queue per connected SSE client.
- `unregister_queue` uses `list.remove()` with a `try/except ValueError` to be safe against double-unregister.
- `_publish` iterates over a `list()` copy to avoid mutation issues if unregister happens concurrently.
- `run_job` publishes `product_done` after each successful product (with `job.processed + 1` computed before increment) and `error` on exception, then `job_complete` at the end.
- The SSE generator breaks on `job_complete` and cleans up via `finally: unregister_queue(...)`, so client disconnect is handled by the `CancelledError` propagating to the `finally` block.
- `sse-starlette 2.1.3` is the compatible version — 3.x requires starlette ≥ 0.49.1 which conflicts with fastapi 0.111+.
- Tests reset `AppStatus.should_exit_event` between each test to avoid the asyncio Event loop binding issue in sse-starlette 2.x.

### Completion Notes

All 4 tasks completed. All 3 ACs satisfied:
- ✅ `GET /api/jobs/{id}/stream` sends `product_done`, `job_complete`, and `error` SSE events
- ✅ Stream closes cleanly on `job_complete` (generator breaks) or client disconnect (`CancelledError` → `finally`)
- ✅ Already-complete job sends `job_complete` immediately via the `immediate()` generator

33 tests pass (12 new for E2-S1, 21 existing — no regressions).

---

## File List

- `backend/routers/stream.py` — new SSE endpoint
- `backend/services/job_runner.py` — modified: added queue management and `_publish` calls
- `backend/main.py` — modified: registered `stream.router`
- `tests/test_stream.py` — new: 12 tests covering queue management and SSE endpoint

---

## Change Log

- 2026-04-25: Implemented E2-S1 — SSE stream endpoint with in-memory event queue, product_done/job_complete/error events, and clean disconnect handling.
