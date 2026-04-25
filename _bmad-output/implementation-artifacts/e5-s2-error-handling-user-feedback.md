# Story E5-S2: Error Handling & User Feedback

**Epic:** E5 — Polish & Quality  
**Story ID:** E5-S2  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want clear error messages when scraping or classification fails  
So that I can act on failures rather than wonder what went wrong

---

## Acceptance Criteria

- [ ] SSE `error` events shown in Live Feed with URL + message (e.g., "Timeout after 30s")
- [ ] Job with partial failures still shows results for successful products
- [ ] `jobs.status` = `failed` if all URLs errored; `complete` if ≥1 succeeded
- [ ] API errors (non-200) surfaced as toast notifications in the UI
- [ ] Scraper returns `{"ingredients_raw": "Not listed", "error": "..."}` without crashing the job

---

## Technical Requirements

### Backend: Scraper Error Returns

Verify `backend/services/scraper.py` already returns on failure:
```python
return {"url": url, "name": "", "ingredients_raw": "Not listed", "error": str(e)}
```

If not, add the `error` field to the return dict.

### Backend: Job Status Logic (in job_runner.py)

Verify the status logic at end of `run_job()`:
```python
# After processing all URLs:
if job.errors == len(urls):
    job.status = "failed"   # ALL failed
else:
    job.status = "complete"  # at least 1 succeeded
```

This must be correct before marking E5-S2 done.

### Backend: Error Count in Job Model

The `errors` field in `Job` model increments per-URL error. Verify this is implemented in E1-S4's `job_runner.py`.

### Frontend: Toast Notification System

Install and configure Shadcn Toast:

```bash
# Install Shadcn toast (if using Shadcn v2 / sonner):
npx shadcn@latest add sonner
# OR: npx shadcn@latest add toast
```

Add `<Toaster>` to `App.tsx`:
```tsx
import { Toaster } from "@/components/ui/sonner";
// OR
import { Toaster } from "@/components/ui/toaster";

function App() {
  return (
    <>
      <RouterProvider ... />
      <Toaster />
    </>
  );
}
```

### Frontend: Toast Usage

```typescript
import { toast } from "sonner";
// OR
import { useToast } from "@/components/ui/use-toast";

// Show error toast
toast.error("Failed to submit job. Please try again.");

// Show success toast
toast.success("Export ready — downloading...");
```

### Frontend: API Error → Toast

In `Home.tsx` submit handler:
```tsx
async function handleSubmit() {
  setSubmitting(true);
  try {
    const { job_id } = await postJob(urls);
    navigate(`/jobs/${job_id}`);
  } catch (err) {
    toast.error("Failed to submit job. Check your connection and try again.");
  } finally {
    setSubmitting(false);
  }
}
```

In `RunResults.tsx` export actions:
```tsx
function download(format: "csv" | "md" | "zip") {
  // window.open doesn't give us error feedback directly
  // Just trigger the download — file download errors are visible in browser
  window.open(`/api/jobs/${jobId}/export/${format}`, "_blank");
}
```

### Frontend: LiveFeed Error Display

The `LiveFeed` component (E2-S3) must display `error` type SSE events. Verify this is implemented:
```tsx
{e.type === "error" ? (
  <div className="flex items-center gap-2 px-4 py-2 border-b bg-red-50">
    <span className="text-red-500 text-sm">⚠ Error processing {e.url}: {e.message}</span>
  </div>
) : (
  // normal product_done row
)}
```

### Frontend: Error Count in Stats Panel

The stats panel in `JobProgress.tsx` shows error count:
```tsx
<StatCard label="Errors" value={errorCount} color="red" />
```

Error count also appears in the export bar (RunResults):
```tsx
{job.errors > 0 && (
  <span className="text-red-500 text-sm">{job.errors} errors</span>
)}
```

### Files to Create/Modify

- **Create:** None (all modifications to existing files)
- **Modify:** `App.tsx` — add `<Toaster />`
- **Modify:** `Home.tsx` — add try/catch + toast on submit
- **Modify:** `RunResults.tsx` — add error count to export bar
- **Modify:** `job_runner.py` — verify error status logic
- **Modify:** `scraper.py` — verify error field in return

---

## Implementation Tasks

- [ ] Add toast notification system (Shadcn Toast / Sonner)
- [ ] Review `job_runner.py` error handling — per-URL try/except, job-level status logic
- [ ] Show error count in Live Feed stats panel and Run Results export bar
- [ ] Add toast on API error in Home.tsx submit handler

---

## Dev Notes

### Sonner vs. Shadcn Toast

Shadcn now recommends `sonner` as the toast library. If the project was scaffolded with newer Shadcn, use `sonner`. If using the older built-in `useToast` hook, that works too. Use one consistently — don't mix both.

### Per-URL Errors: Don't Stop the Job

The `try/except` in `run_job()` catches per-URL errors and continues to the next URL. This is already specced in E1-S4. The E5-S2 story verifies it works correctly by testing a URL that times out or returns a non-200 response.

### Error Message in SSE Event

When publishing the SSE `error` event, include a useful message:
```python
await _publish(job_id, {
    "type": "error",
    "url": url,
    "message": str(e)[:200]  # truncate to 200 chars for readability
})
```

Common messages: "Timeout after 30s", "Page not found (404)", "Classification error: ..."

### Partial Failure: Job Status

Verify with a test: submit 3 URLs, 2 valid products + 1 invalid URL. Expected:
- `job.errors = 1`
- `job.in_scope >= 1`  
- `job.status = "complete"` (not "failed")

### Toast Timing

Show error toast immediately when the API call fails. Don't show a toast for SSE `error` events — those are shown inline in the LiveFeed, which is already visible to the user. Toast is for API-level failures (submit, export endpoints).
