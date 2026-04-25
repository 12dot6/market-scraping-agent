# Story E2-S2: Home Screen — URL Input (Screen 1)

**Epic:** E2 — Job Pipeline & Live Progress  
**Story ID:** E2-S2  
**Status:** review  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want to paste or upload URLs and submit a scraping job  
So that I can start a batch scrape from the browser

---

## Acceptance Criteria

- [ ] Textarea: one URL per line, HTML5 URL validation on submit
- [ ] File upload: parses `input.txt` format, strips `#` comments, populates textarea
- [ ] Domain chips shown below textarea as URL count changes
- [ ] Submit button disabled until ≥1 URL; shows loading state while POST is in-flight
- [ ] On success, navigates to `/jobs/{id}` (live progress screen)
- [ ] Recent Runs list below input: date, product count, status badge, [View] link

---

## Technical Requirements

### Tech Stack

- React 18, TypeScript, Vite
- Tailwind CSS + Shadcn/ui components
- TanStack Query (`@tanstack/react-query`) for API calls
- React Router 6 (`react-router-dom`)

### Files to Create

```
frontend/src/
├── pages/
│   └── Home.tsx
├── components/
│   ├── UrlInput.tsx           ← textarea + domain chips
│   ├── FileUpload.tsx         ← input.txt upload button
│   └── JobCard.tsx            ← recent runs list item
└── lib/
    └── api.ts                 ← typed fetch wrappers
```

### api.ts — Typed API Functions

```typescript
const BASE = "/api";

export interface JobCreated { job_id: string; }
export interface JobSummary {
  id: string;
  status: "queued" | "running" | "complete" | "failed";
  url_count: number;
  processed: number;
  in_scope: number;
  excluded: number;
  errors: number;
  created_at: string;
  completed_at: string | null;
}

export async function postJob(urls: string[]): Promise<JobCreated> {
  const res = await fetch(`${BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ urls }),
  });
  if (!res.ok) throw new Error(`POST /api/jobs failed: ${res.status}`);
  return res.json();
}

export async function getJobs(): Promise<JobSummary[]> {
  const res = await fetch(`${BASE}/jobs`);
  if (!res.ok) throw new Error(`GET /api/jobs failed: ${res.status}`);
  return res.json();
}
```

### UrlInput.tsx Behavior

```typescript
// Props
interface UrlInputProps {
  value: string;
  onChange: (v: string) => void;
}

// Parse URLs from textarea text (one per line, skip blanks)
function parseUrls(text: string): string[] {
  return text.split("\n")
    .map(l => l.trim())
    .filter(l => l.length > 0);
}

// Extract unique domains for chips
function extractDomains(urls: string[]): string[] {
  const domains = new Set<string>();
  for (const url of urls) {
    try { domains.add(new URL(url).hostname.replace("www.", "")); } catch {}
  }
  return [...domains];
}

// HTML5 URL validation: try new URL() for each line
function validateUrls(urls: string[]): string[] {
  return urls.filter(u => {
    try { new URL(u); return false; } catch { return true; } // return invalid
  });
}
```

### FileUpload.tsx — Parse input.txt Format

```typescript
function parseInputFile(text: string): string[] {
  return text.split("\n")
    .map(l => l.trim())
    .filter(l => l.length > 0 && !l.startsWith("#"));
}

// On file select: read, parse, call onParsed(urls)
```

### Home.tsx Key Structure

```tsx
export default function Home() {
  const [urlText, setUrlText] = useState("");
  const navigate = useNavigate();
  const { data: recentJobs } = useQuery({ queryKey: ["jobs"], queryFn: getJobs });
  const [submitting, setSubmitting] = useState(false);

  const urls = parseUrls(urlText);
  const invalidUrls = validateUrls(urls);
  const domains = extractDomains(urls);
  const canSubmit = urls.length > 0 && invalidUrls.length === 0 && !submitting;

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const { job_id } = await postJob(urls);
      navigate(`/jobs/${job_id}`);
    } catch {
      // show error toast (E5-S2)
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <UrlInput value={urlText} onChange={setUrlText} />
      {/* domain chips */}
      {domains.map(d => <Badge key={d}>{d}</Badge>)}
      {/* submit */}
      <Button disabled={!canSubmit} onClick={handleSubmit}>
        {submitting ? "Starting..." : "Start Scraping"}
      </Button>
      <FileUpload onParsed={parsed => setUrlText(parsed.join("\n"))} />
      {/* recent runs */}
      <div>
        {recentJobs?.map(job => <JobCard key={job.id} job={job} />)}
      </div>
    </div>
  );
}
```

### JobCard.tsx

```tsx
// Show: date (formatted), product count (in_scope), status badge, [View] link
// Status badge colors:
//   queued → blue, running → amber, complete → green, failed → red
// Navigate to /results/{job.id} on [View] click
```

### React Router Setup (in App.tsx or main.tsx)

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
<Routes>
  <Route path="/" element={<Home />} />
  <Route path="/jobs/:jobId" element={<JobProgress />} />
  <Route path="/results/:jobId" element={<RunResults />} />
  <Route path="/results" element={<Ingredients />} />
</Routes>
```

### Design System

- Colors: Primary action violet `#7C3AED`, amber accent `#F59E0B`, success `#10B981`
- Submit button: Shadcn `<Button>` with primary variant
- Textarea: Shadcn `<Textarea>`, min 4 rows
- Status badges: Shadcn `<Badge>` with variant mapping
- Domain chips: small `<Badge>` variants (secondary/outline)
- Card spacing: 8px base, `p-4` / `p-6` for sections

---

## Implementation Tasks

- [x] Create `frontend/src/pages/Home.tsx`
- [x] Create `frontend/src/components/UrlInput.tsx` with textarea + domain chips
- [x] Create `frontend/src/components/FileUpload.tsx`
- [x] Create `frontend/src/components/JobCard.tsx` for recent runs list
- [x] Create `frontend/src/lib/api.ts` with typed fetch wrapper for `POST /api/jobs` and `GET /api/jobs`
- [x] Set up React Router in `App.tsx`
- [x] Set up TanStack Query provider in `main.tsx`

---

## Dev Notes

### TanStack Query Provider Setup

Add to `main.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const queryClient = new QueryClient();
ReactDOM.createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>
);
```

### HTML5 URL Validation

Use `try { new URL(line) } catch { invalid }` — don't use regex. Browser `URL` constructor correctly validates URLs including protocol requirement.

Show invalid lines highlighted red in the textarea area or as inline error text below (not blocking toast).

### File Upload — Hidden Input Pattern

```tsx
<input type="file" accept=".txt" style={{ display: "none" }} ref={inputRef}
  onChange={e => { /* read file */ }} />
<Button variant="outline" onClick={() => inputRef.current?.click()}>
  Upload input.txt
</Button>
```

### Recent Runs — Refetch Interval

Use TanStack Query's `refetchInterval: 3000` to keep the job list fresh while jobs are running. Disable it when all visible jobs are in terminal state (complete/failed).

### Navigation After Submit

On successful `POST /api/jobs`, immediately `navigate(\`/jobs/${job_id}\`)`. Do not wait for the job to start running. The JobProgress page (E2-S3) handles the initial "connecting" state.

### UX: Empty Textarea State

Per the UX spec, when textarea is empty, show a placeholder: "Paste one URL per line…". The submit button stays disabled (no URLs). No empty state message needed here — that's for the Recent Runs section below the form.

---

## Dev Agent Record

### Implementation Notes

- Node.js 24 was installed via `winget` (not previously on this machine). React Router 7, TanStack Query 5, Tailwind CSS 3, CVA/clsx/tailwind-merge were added to `package.json`.
- Shadcn/ui components (Button, Textarea, Badge) were written manually (not via `npx shadcn init`) to keep it lightweight. `@` path alias wired in both `tsconfig.json` and `vite.config.ts`.
- `refetchInterval` uses the callback form to disable polling once all visible jobs reach terminal state (`complete`/`failed`), avoiding unnecessary API calls.
- Placeholder `<PlaceholderPage>` components hold `/jobs/:jobId`, `/results/:jobId`, and `/results` routes so the router is fully wired without depending on future stories.
- `validateUrls` returns invalid URLs; `canSubmit` blocks if any exist — HTML5 `new URL()` constructor used per spec, not regex.

### Completion Notes

All 7 tasks complete. All 6 ACs satisfied:
- ✅ Textarea with one-URL-per-line, HTML5 URL validation on submit
- ✅ File upload parses input.txt format (strips `#` comments), populates textarea
- ✅ Domain chips from extracted hostnames
- ✅ Submit disabled until ≥1 valid URL; shows "Starting…" loading state
- ✅ Navigates to `/jobs/{id}` on success
- ✅ Recent Runs list with date, product count, status badge, View link

Build: `tsc && vite build` — clean, no errors.

---

## File List

- `frontend/package.json` — added react-router-dom, @tanstack/react-query, tailwindcss, postcss, autoprefixer, class-variance-authority, clsx, tailwind-merge, lucide-react
- `frontend/tailwind.config.js` — new
- `frontend/postcss.config.js` — new
- `frontend/vite.config.ts` — added `@` path alias
- `frontend/tsconfig.json` — added baseUrl + paths for `@` alias
- `frontend/src/index.css` — new (Tailwind directives)
- `frontend/src/main.tsx` — updated: QueryClientProvider + BrowserRouter
- `frontend/src/App.tsx` — updated: Routes with React Router
- `frontend/src/lib/utils.ts` — new (cn utility)
- `frontend/src/lib/api.ts` — new (typed fetch wrappers)
- `frontend/src/components/ui/button.tsx` — new
- `frontend/src/components/ui/textarea.tsx` — new
- `frontend/src/components/ui/badge.tsx` — new
- `frontend/src/components/UrlInput.tsx` — new
- `frontend/src/components/FileUpload.tsx` — new
- `frontend/src/components/JobCard.tsx` — new
- `frontend/src/pages/Home.tsx` — new

---

## Change Log

- 2026-04-25: Implemented E2-S2 — Home screen with URL textarea, domain chips, file upload, Recent Runs list, React Router + TanStack Query setup.
