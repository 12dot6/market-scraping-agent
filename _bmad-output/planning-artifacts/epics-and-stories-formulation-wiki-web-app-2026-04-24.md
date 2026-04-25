# Epics & Stories: Formulation Wiki Web App
_Version 1.0 | 2026-04-24 | Linked PRD: prd-formulation-wiki-web-app-2026-04-24.md_

---

## Epic Overview

| Epic | Title | Phase | PRD Features |
|------|-------|-------|--------------|
| E1 | Backend Foundation | Day 1 | FR-01, FR-08, FR-09 |
| E2 | Job Pipeline & Live Progress | Day 2 | FR-02, FR-03, FR-05 |
| E3 | Results UI & Export | Day 2–3 | FR-04, FR-06 |
| E4 | Global Ingredients & Deployment | Day 3 | FR-07, Deployment |
| E5 | Polish & Quality | Day 3.5 | All FRs |

---

## E1 — Backend Foundation

**Goal:** Runnable FastAPI app with SQLite, scraping, and classification working end-to-end — no UI yet. Proves the pipeline works before any frontend investment.

**Done when:** `POST /api/jobs` accepts URLs, scrapes them sequentially with Playwright, classifies each with Claude API, writes results to SQLite, and `GET /api/jobs/{id}/products` returns the structured result.

---

### Story E1-S1: Project scaffold & Docker skeleton

**As a** developer  
**I want** a working Docker container skeleton with FastAPI + SQLite + Vite placeholder  
**So that** the full dev environment is established from day one

**Acceptance Criteria:**
- `docker compose up` starts without errors
- `GET /` serves a static HTML placeholder from `frontend/dist/`
- `GET /api/health` returns `{"status": "ok"}`
- SQLite file created at `/app/db/formulation_wiki.db` on startup with WAL mode enabled
- `.env` file with `ANTHROPIC_API_KEY` loaded via python-dotenv

**Tasks:**
- [ ] Create `Dockerfile` (Python 3.12-slim, Node for frontend build, Playwright chromium)
- [ ] Create `docker-compose.yml` with volumes for `./db` and `./exports`
- [ ] Create `backend/main.py`, `config.py`, `database.py`
- [ ] Create `models.py` with all four SQLAlchemy models (`jobs`, `products`, `ingredients`, `product_ingredients`)
- [ ] Create `schemas.py` Pydantic models for request/response
- [ ] Create `frontend/` Vite+React scaffold with placeholder page

---

### Story E1-S2: Playwright scraper service

**As a** job runner  
**I want** a scraper that extracts raw ingredient text from a product URL  
**So that** the classification step has something to work with

**Acceptance Criteria:**
- `scrape(url)` returns `{url, name, ingredients_raw}` for a valid Ulta/L'Oreal/Schwarzkopf product URL
- Returns `{"ingredients_raw": "Not listed"}` (no exception raised) for timeout or parse failure
- Single browser instance per call (no pooling), 30s timeout
- One-shot JS extraction logic ported from `.claude/commands/get-ingredients.md`

**Tasks:**
- [ ] Create `backend/services/scraper.py` with `ONE_SHOT_JS` constant and `async scrape()` function
- [ ] Test manually against a real Ulta URL and a real L'Oreal URL
- [ ] Verify heading-click, heading-sibling, body-scan, and regex fallback paths all run without error

---

### Story E1-S3: Claude API classifier service

**As a** job runner  
**I want** a classifier that takes raw ingredient text and returns structured JSON  
**So that** ingredient data can be persisted and displayed with component grouping and dye active flags

**Acceptance Criteria:**
- `classify(name, url, ingredients_raw)` returns valid JSON matching the schema: `{in_scope, scope_reason, components, dye_actives, internal_names}`
- Ingredient mapping file loaded once at module init (prompt cache via `cache_control: ephemeral`)
- Returns `in_scope: false` (not an exception) when the product is not a dye/colour product
- Model: `claude-sonnet-4-6`, max_tokens: 600

**Tasks:**
- [ ] Create `backend/services/classifier.py` 
- [ ] Copy `data/mapped-ingredients.txt` to `backend/data/`
- [ ] Test against a real product with multi-component ingredients
- [ ] Test against a non-dye product (should return `in_scope: false`)

---

### Story E1-S4: Job runner & REST endpoints for job management

**As a** user  
**I want** to submit URLs and retrieve job status and results via API  
**So that** the frontend can wire up to a working backend

**Acceptance Criteria:**
- `POST /api/jobs` with `{urls: [...]}` creates a job record, starts BackgroundTask, returns `{job_id}` immediately
- BackgroundTask: for each URL → scrape → classify → write `products` + `ingredients` + `product_ingredients` rows → update `jobs.processed` count
- `GET /api/jobs` returns list of jobs, most recent first
- `GET /api/jobs/{id}` returns job detail with progress counts
- `GET /api/jobs/{id}/products` returns full product list with classified ingredients

**Tasks:**
- [ ] Create `backend/services/job_runner.py` — orchestrates scrape → classify → DB writes
- [ ] Create `backend/routers/jobs.py` — POST + GET endpoints
- [ ] Create `backend/routers/results.py` — products endpoint
- [ ] Upsert logic for `ingredients` table (increment `count` if name already exists)
- [ ] Test full pipeline: submit 3 URLs → verify DB rows and products endpoint response

---

## E2 — Job Pipeline & Live Progress

**Goal:** Users can submit jobs from the browser, watch real-time progress via SSE, and see a live feed of products as they complete.

**Done when:** Screen 1 (URL input) and Screen 2 (live progress) are fully functional end-to-end.

---

### Story E2-S1: SSE stream endpoint

**As a** frontend  
**I want** a Server-Sent Events stream for job progress  
**So that** the UI can display live updates without polling

**Acceptance Criteria:**
- `GET /api/jobs/{id}/stream` sends SSE events:
  - `product_done`: `{type, name, in_scope, progress: {done, total}}`
  - `job_complete`: `{type, stats: {in_scope, excluded, duration_sec}}`
  - `error`: `{type, url, message}`
- Stream closes cleanly when job completes or client disconnects
- If job is already complete when client connects, sends `job_complete` immediately

**Tasks:**
- [ ] Create `backend/routers/stream.py` with `EventSourceResponse` (via `sse-starlette`)
- [ ] Modify `job_runner.py` to publish events to an in-memory queue per `job_id`
- [ ] Handle client disconnect without crashing the background task

---

### Story E2-S2: Home screen — URL input (Screen 1)

**As a** user  
**I want** to paste or upload URLs and submit a scraping job  
**So that** I can start a batch scrape from the browser

**Acceptance Criteria:**
- Textarea: one URL per line, HTML5 URL validation on submit
- File upload: parses `input.txt` format, strips `#` comments, populates textarea
- Domain chips shown below textarea as URL count changes
- Submit button disabled until ≥1 URL; shows loading state while POST is in-flight
- On success, navigates to `/jobs/{id}` (live progress screen)
- Recent Runs list below input: date, product count, status badge, [View] link

**Tasks:**
- [ ] Create `frontend/src/pages/Home.tsx`
- [ ] Create `frontend/src/components/UrlInput.tsx` with textarea + domain chips
- [ ] Create `frontend/src/components/FileUpload.tsx`
- [ ] Create `frontend/src/components/JobCard.tsx` for recent runs list
- [ ] Create `frontend/src/lib/api.ts` with typed fetch wrapper for `POST /api/jobs` and `GET /api/jobs`

---

### Story E2-S3: Live progress screen (Screen 2)

**As a** user  
**I want** to watch a job run in real time  
**So that** I know how many products have been processed and which are in/out of scope

**Acceptance Criteria:**
- Progress bar showing done/total and % complete
- Estimated time remaining (based on avg time/product so far)
- Live feed panel: product name + in-scope (🟢) or excluded (🔴) badge, appears as SSE events arrive
- Stats panel: running count of in-scope, excluded, errors, avg s/product
- "View Results" button appears (and navigates to `/results/{id}`) when `job_complete` event received
- Page is usable if user navigates directly to `/jobs/{id}` for a completed job

**Tasks:**
- [ ] Create `frontend/src/pages/JobProgress.tsx`
- [ ] Create `frontend/src/components/LiveFeed.tsx`
- [ ] Create `frontend/src/lib/sse.ts` — `useSSE(jobId)` hook using `EventSource`
- [ ] Wire progress bar + stats to SSE state
- [ ] Handle reconnect if SSE connection drops

---

## E3 — Results UI & Export

**Goal:** Users can view per-run results with full ingredient detail, export data, and understand which products were excluded.

**Done when:** Screen 3 (Run Results) with all three tabs and the export bar is functional.

---

### Story E3-S1: ProductCard component

**As a** user  
**I want** to see each product's ingredients grouped by component with dye actives highlighted  
**So that** I can quickly identify formulation patterns and active ingredients

**Acceptance Criteria:**
- Component section headers in ALL CAPS sourced from Claude API `components` field
- Dye actives shown as amber ⚠️ pill inline within ingredient lists
- Dye actives also summarised in card header
- Lists >8 ingredients collapsed with "Show all N ingredients" toggle
- Mapped ingredients (have internal_name): dotted underline + hover tooltip
- In-scope badge (🟢) shown in card header; INCI names preserved exactly as scraped
- Card renders correctly for single-component products (`{"All": [...]}`)

**Tasks:**
- [ ] Create `frontend/src/components/ProductCard.tsx`
- [ ] Create `frontend/src/components/DyeActiveBadge.tsx`
- [ ] Create `frontend/src/components/ScopeBadge.tsx`
- [ ] Implement ingredient collapse/expand logic

---

### Story E3-S2: Ingredient table component (per-run)

**As a** user  
**I want** a sortable, searchable ingredient table for a run's results  
**So that** I can analyse ingredient frequency within a batch

**Acceptance Criteria:**
- Columns: ingredient name, internal name, count, frequency bar
- Sort by count (default) or name — client-side, no API call
- Dye active rows: amber left border
- Search box filters by ingredient name (client-side)
- Toggle: "Dye actives only" filters list
- Row click expands a panel listing which products in this run contain the ingredient

**Tasks:**
- [ ] Create `frontend/src/components/IngredientTable.tsx`
- [ ] Implement client-side sort, search, filter, expand logic
- [ ] `GET /api/jobs/{id}/products` response must include per-ingredient `is_dye_active` and `internal_name`

---

### Story E3-S3: Run Results page with tabs and export bar (Screen 3)

**As a** user  
**I want** a tabbed results view with a persistent export bar  
**So that** I can navigate between products, ingredients, and exclusions and download data

**Acceptance Criteria:**
- Export bar (always visible): run date + stats + [Download CSV] [Download MD] [Download ZIP]
- Three tabs: Products | Ingredients | Excluded
- Products tab: list of ProductCards (in-scope products)
- Ingredients tab: IngredientTable for this run
- Excluded tab: table of excluded products with name, URL, reason
- Page navigable via `/results/{jobId}`

**Tasks:**
- [ ] Create `frontend/src/pages/RunResults.tsx` with tab state
- [ ] Create `frontend/src/components/ExportBar.tsx`
- [ ] Add `GET /api/jobs/{id}/products` query via TanStack Query
- [ ] Add `GET /api/ingredients?job_id={id}` variant for per-run ingredient table

---

### Story E3-S4: Export endpoints

**As a** user  
**I want** to download per-run and global exports as CSV, MD, and ZIP  
**So that** I can use the data in spreadsheets and reports

**Acceptance Criteria:**
- `GET /api/jobs/{id}/export/csv` — ingredients for this run as CSV
- `GET /api/jobs/{id}/export/md` — formatted markdown report for this run
- `GET /api/jobs/{id}/export/zip` — CSV + MD bundled as ZIP
- `GET /api/export/master-csv` — all ingredients across all runs
- Files saved to `/exports/` directory and returned as file download responses
- CSV column order: ingredient, internal_name, count, is_dye_active, component

**Tasks:**
- [ ] Create `backend/services/export_service.py` — generates MD, CSV, ZIP from DB query
- [ ] Create `backend/routers/exports.py` — four endpoints using `FileResponse`
- [ ] Verify master CSV includes deduplicated ingredient rows with total count

---

## E4 — Global Ingredients & Deployment

**Goal:** Cross-run ingredient frequency screen is live, Docker single-container build is verified, and the app is deployable.

**Done when:** Screen 4 (Global Ingredients) works, `docker compose up -d` starts the app cleanly, and a fresh container imports existing data.

---

### Story E4-S1: Global Ingredients screen (Screen 4)

**As a** user  
**I want** to see ingredient frequency across all scraping runs  
**So that** I can identify the most commonly used ingredients in the full dataset

**Acceptance Criteria:**
- Same IngredientTable component as per-run, but queries `GET /api/ingredients` (no job_id filter)
- Run filter dropdown: "All runs" or select a specific run by date
- Date range filter: from/to date pickers
- [Download Master CSV] button triggers `GET /api/export/master-csv`
- Frequency chart (Recharts bar chart) showing top 20 ingredients by count
- Navigable at `/results` (no job ID)

**Tasks:**
- [ ] Create `frontend/src/pages/Ingredients.tsx`
- [ ] Create `frontend/src/components/FrequencyChart.tsx` using Recharts
- [ ] Add run filter + date range query params to `GET /api/ingredients`
- [ ] Wire [Download Master CSV] to export endpoint
- [ ] Add nav link in app header

---

### Story E4-S2: Docker single-container build & data migration

**As a** developer  
**I want** to build and run the full app in a single Docker container  
**So that** deployment is one command

**Acceptance Criteria:**
- `docker compose up -d` builds and starts without errors
- App accessible at `http://localhost:8000`
- Frontend SPA served by FastAPI at `/` with correct React Router client-side routing (fallback to `index.html`)
- SQLite file persisted in `./db/` volume across container restarts
- Exports persisted in `./exports/` volume
- On first run, existing `output/ingredients-master.csv` can be imported into `ingredients` table via a one-shot script

**Tasks:**
- [ ] Finalise `Dockerfile` (multi-stage: Node build → Python runtime)
- [ ] Finalise `docker-compose.yml`
- [ ] Verify `StaticFiles` mount with `html=True` handles React Router paths correctly
- [ ] Write `backend/scripts/import_master.py` for one-time CSV import
- [ ] End-to-end smoke test: submit job → live progress → view results → export

---

## E5 — Polish & Quality

**Goal:** App is production-ready for internal use — handles errors gracefully, works on mobile, and has no embarrassing empty states.

**Done when:** All empty states show meaningful messages, error cases are surfaced clearly, and the UI is usable on a tablet/mobile screen.

---

### Story E5-S1: Empty states & loading skeletons

**As a** user  
**I want** informative empty states and loading feedback  
**So that** the app doesn't feel broken when there's no data yet

**Acceptance Criteria:**
- Home screen: "No runs yet — paste URLs above to get started" when job list is empty
- Run Results (Products tab): "No in-scope products found for this run" if all excluded
- Run Results (Excluded tab): "All products were in scope — nothing excluded" if none excluded
- Global Ingredients: "No ingredients yet — run a scrape to populate this table"
- All data-fetching views show a skeleton/spinner while loading

**Tasks:**
- [ ] Add empty state components to Home, RunResults, Ingredients pages
- [ ] Add loading skeletons (Shadcn Skeleton) to all list/table views
- [ ] Add TanStack Query error boundaries with retry button

---

### Story E5-S2: Error handling & user feedback

**As a** user  
**I want** clear error messages when scraping or classification fails  
**So that** I can act on failures rather than wonder what went wrong

**Acceptance Criteria:**
- SSE `error` events shown in Live Feed with URL + message (e.g., "Timeout after 30s")
- Job with partial failures still shows results for successful products
- `jobs.status` = `failed` if all URLs errored; `complete` if ≥1 succeeded
- API errors (non-200) surfaced as toast notifications in the UI
- Scraper returns `{"ingredients_raw": "Not listed", "error": "..."}` without crashing the job

**Tasks:**
- [ ] Add toast notification system (Shadcn Toast)
- [ ] Review `job_runner.py` error handling — per-URL try/except, job-level status logic
- [ ] Show error count in Live Feed stats panel and Run Results export bar

---

### Story E5-S3: Mobile responsiveness

**As a** user on a tablet or phone  
**I want** the app to be usable on smaller screens  
**So that** I can check job status or browse results away from my desk

**Acceptance Criteria:**
- Home screen: textarea and submit button stack vertically on mobile
- JobProgress: Live Feed and Stats panels stack vertically below progress bar
- RunResults: tabs scroll horizontally if needed; ProductCard readable at 375px width
- IngredientTable: columns collapse gracefully (hide frequency bar on mobile)
- Navigation header collapses to hamburger menu below 768px

**Tasks:**
- [ ] Audit all four screens with Tailwind responsive prefixes (`sm:`, `md:`)
- [ ] Test at 375px (iPhone SE) and 768px (iPad) viewport widths
- [ ] Add responsive nav (Shadcn Sheet for mobile drawer)

---

## Story Sizing Reference

| Story | Effort |
|-------|--------|
| E1-S1 | M (half day) |
| E1-S2 | S (2h) |
| E1-S3 | S (2h) |
| E1-S4 | M (half day) |
| E2-S1 | S (2h) |
| E2-S2 | M (half day) |
| E2-S3 | M (half day) |
| E3-S1 | M (half day) |
| E3-S2 | S (2h) |
| E3-S3 | S (2h) |
| E3-S4 | S (2h) |
| E4-S1 | M (half day) |
| E4-S2 | S (2h) |
| E5-S1 | S (2h) |
| E5-S2 | S (2h) |
| E5-S3 | S (2h) |

**Total: ~3–3.5 days** (matches build timeline in web-app-plan.md)
