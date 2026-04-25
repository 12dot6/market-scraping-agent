# Formulation Wiki — Web App Build Plan
_Last reviewed: 2026-04-24 | Simplified for small user base, 10K total products_

---

## Context

Scrapes hair colour/dye-adjacent product ingredients from retailer websites (Ulta, L'Oreal, Schwarzkopf, etc.), classifies them via Claude API, and builds a master ingredient frequency database. Currently runs via Claude Code's `/get-ingredients` slash command — this plan productionises it as a standalone web app.

**Scale:** Small set of users. 10K products extracted over time (not concurrently). No high-traffic requirements.

---

## Architecture Review — What Was Cut and Why

The previous plan was designed for enterprise scale. For a small internal tool processing 10K products over time, the following were removed:

| Removed | Replaced with | Reason |
|---|---|---|
| PostgreSQL + Docker DB service | **SQLite** | 10K products ≈ <50MB. SQLite with WAL mode handles this trivially. No server process, no Docker service, file lives next to the app. |
| Celery + Redis + separate worker container | **FastAPI BackgroundTasks** | Celery is for distributed, high-concurrency workloads. A single background task running overnight to process 10K products is sufficient. Eliminates Redis entirely. |
| Next.js (App Router) | **Vite + React SPA** | Next.js SSR/RSC is for SEO and public-facing sites. An internal tool needs none of it. Vite builds a static SPA served directly by FastAPI — no separate frontend service. |
| BrowserPool (5 parallel contexts) | **Single Playwright browser** | Parallel scraping needs coordination logic. Sequential scraping at 5s/product processes 10K in ~14 hours — perfectly fine running overnight as a background job. |
| Alembic migrations | **SQLAlchemy `create_all()`** | Migration tooling is for team environments where schema changes need to be tracked and rolled back. For a single-developer tool, auto-creating tables on startup is simpler and sufficient. |
| TanStack Table | **Simple table component** | TanStack Table shines with 100K+ rows and complex features. Our ingredient list is small — a clean styled HTML table with client-side sort is enough. |
| react-hook-form + zod | **Native HTML5 validation** | URL textarea validation (is it a URL? is it blank?) doesn't need a form library. |
| structlog | **Python `logging`** | Structured JSON logging is for log aggregation pipelines. Standard logging is fine here. |
| 5 Docker services | **1 Docker service** | FastAPI serves the Vite build as static files. Single container, single port, one command to run. |

**Features preserved:** all UI screens, live progress, ingredient display with component grouping and dye active highlights, per-run and global exports (CSV/MD/ZIP), URL input from UI, charts.

---

## Simplified Architecture

```
┌──────────────────────────────────────────┐
│  Browser                                  │
│  Vite + React SPA (served by FastAPI)    │
│  URL Input → Progress → Results + Export │
└──────────────┬───────────────────────────┘
               │ REST + SSE
┌──────────────▼───────────────────────────┐
│  FastAPI  (single process)               │
│  ├── API routers                         │
│  ├── SSE endpoint (job progress)         │
│  ├── BackgroundTask (job runner)         │
│  │     ├── Playwright (headless, single) │
│  │     └── Claude API (classify + map)  │
│  ├── Static file serving (React build)  │
│  └── SQLite via SQLAlchemy              │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│  SQLite  +  /exports/  (local files)     │
└──────────────────────────────────────────┘
```

One process. One database file. One Docker container.

---

## Tech Stack

```
Frontend                Backend               Infrastructure
──────────────────      ──────────────────    ─────────────
Vite + React 18         FastAPI               SQLite (WAL mode)
Tailwind CSS            Playwright (async)    Docker (1 container)
Shadcn/ui               Anthropic SDK         /exports/ file store
TanStack Query          SQLAlchemy 2.0
Recharts                Pydantic v2
React Router 6          python-dotenv
```

### Design system
- **Component library:** Shadcn/ui — pre-built accessible components, fully themeable
- **Color palette:**
  - Primary: `#7C3AED` (violet)
  - Accent: `#F59E0B` (amber — also used for dye active highlights)
  - Success: `#10B981` (emerald — in-scope badge)
  - Danger: `#EF4444` (red — excluded badge, errors)
  - Background: `#FAFAF9` (warm off-white)
  - Card: `#FFFFFF` with `shadow-sm`

---

## Project Structure

```
formulation-wiki-app/
│
├── backend/
│   ├── main.py                  ← FastAPI app, routers, serves frontend /dist
│   ├── config.py                ← python-dotenv settings
│   ├── database.py              ← SQLite engine, session, create_all on startup
│   ├── models.py                ← SQLAlchemy ORM models
│   ├── schemas.py               ← Pydantic request/response schemas
│   │
│   ├── routers/
│   │   ├── jobs.py              ← POST /jobs, GET /jobs, GET /jobs/{id}
│   │   ├── results.py           ← GET /jobs/{id}/products, GET /ingredients
│   │   ├── exports.py           ← GET /jobs/{id}/export/csv|md|zip, /master-csv
│   │   └── stream.py            ← GET /jobs/{id}/stream  (SSE)
│   │
│   ├── services/
│   │   ├── scraper.py           ← Playwright headless, one-shot JS extraction
│   │   ├── classifier.py        ← Claude API classify + parse + map
│   │   ├── job_runner.py        ← BackgroundTask: scrape → classify → save
│   │   └── export_service.py    ← generates MD / CSV / ZIP from DB
│   │
│   └── data/
│       └── mapped-ingredients.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx              ← React Router routes
│   │   ├── pages/
│   │   │   ├── Home.tsx         ← Screen 1: URL input + recent jobs
│   │   │   ├── JobProgress.tsx  ← Screen 2: live progress via SSE
│   │   │   ├── RunResults.tsx   ← Screen 3: per-run products + exports
│   │   │   └── Ingredients.tsx  ← Screen 4: global ingredient table
│   │   ├── components/
│   │   │   ├── UrlInput.tsx
│   │   │   ├── FileUpload.tsx
│   │   │   ├── JobCard.tsx
│   │   │   ├── LiveFeed.tsx
│   │   │   ├── ProductCard.tsx
│   │   │   ├── IngredientTable.tsx
│   │   │   ├── FrequencyChart.tsx
│   │   │   ├── DyeActiveBadge.tsx
│   │   │   ├── ScopeBadge.tsx
│   │   │   └── ExportBar.tsx
│   │   └── lib/
│   │       ├── api.ts           ← typed fetch wrappers
│   │       └── sse.ts           ← SSE hook
│   └── dist/                   ← Vite build output, served by FastAPI
│
├── db/
│   └── formulation_wiki.db     ← SQLite file (persisted via Docker volume)
│
├── exports/                    ← generated CSV/MD/ZIP files
│
├── Dockerfile                  ← single image: builds frontend + runs backend
├── docker-compose.yml          ← single service
└── .env
```

---

## Database Schema (SQLite)

```sql
-- jobs: one per scraping run
CREATE TABLE jobs (
    id            TEXT PRIMARY KEY,          -- UUID
    status        TEXT NOT NULL,             -- queued | running | complete | failed
    submitted_at  TEXT DEFAULT (datetime('now')),
    started_at    TEXT,
    completed_at  TEXT,
    urls          TEXT NOT NULL,             -- JSON array of submitted URLs
    total         INTEGER DEFAULT 0,
    processed     INTEGER DEFAULT 0,
    in_scope      INTEGER DEFAULT 0,
    excluded      INTEGER DEFAULT 0,
    error         TEXT
);

-- products: one per scraped product URL
CREATE TABLE products (
    id            TEXT PRIMARY KEY,          -- UUID
    job_id        TEXT REFERENCES jobs(id),
    url           TEXT NOT NULL,
    name          TEXT,
    in_scope      INTEGER NOT NULL,          -- 0 or 1
    scope_reason  TEXT,
    ingredients_raw TEXT,
    scraped_at    TEXT DEFAULT (datetime('now'))
);

-- ingredients: global frequency registry
CREATE TABLE ingredients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,      -- lowercased, normalised
    internal_name TEXT,
    count         INTEGER DEFAULT 1
);

-- product_ingredients: junction
CREATE TABLE product_ingredients (
    product_id    TEXT REFERENCES products(id),
    ingredient_id INTEGER REFERENCES ingredients(id),
    is_dye_active INTEGER DEFAULT 0,
    component     TEXT,                      -- "Color Developer", "Cream Pigment" etc.
    PRIMARY KEY (product_id, ingredient_id)
);
```

SQLite WAL mode enabled on startup:
```python
@event.listens_for(engine, "connect")
def set_wal_mode(conn, _):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
```

---

## API Endpoints

```
# Jobs
POST  /api/jobs                   body: { urls: string[] }  → { job_id }
GET   /api/jobs                   → job list (most recent first)
GET   /api/jobs/{id}              → job detail + progress counts
GET   /api/jobs/{id}/stream       → SSE stream (live progress events)

# Results
GET   /api/jobs/{id}/products     → product list for this run
GET   /api/ingredients            ?sort=count&dye_active=true → global list

# Exports
GET   /api/jobs/{id}/export/csv   → download run ingredient CSV
GET   /api/jobs/{id}/export/md    → download run MD report
GET   /api/jobs/{id}/export/zip   → download CSV + MD zipped
GET   /api/export/master-csv      → download global ingredients-master.csv
```

SSE event shape:
```json
{ "type": "product_done",  "name": "IGK 4N Brown", "in_scope": true,  "progress": { "done": 12, "total": 48 } }
{ "type": "product_done",  "name": "CÉCRED Drops",  "in_scope": false, "progress": { "done": 13, "total": 48 } }
{ "type": "job_complete",  "stats": { "in_scope": 41, "excluded": 7, "duration_sec": 183 } }
{ "type": "error",         "url": "https://...", "message": "Timeout after 30s" }
```

---

## Backend — Key Implementation

### main.py — single process, serves frontend
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from database import create_tables
from routers import jobs, results, exports, stream

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()          # create SQLite tables if not exist
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(jobs.router,    prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(stream.router,  prefix="/api")

# Serve React SPA — must be last
app.mount("/", StaticFiles(directory="../frontend/dist", html=True))
```

### routers/jobs.py — submit job as BackgroundTask
```python
from fastapi import APIRouter, BackgroundTasks
from services.job_runner import run_job

router = APIRouter()

@router.post("/jobs")
async def submit_job(payload: JobRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = create_job(db, payload.urls)
    background_tasks.add_task(run_job, job.id)  # runs in background, API returns immediately
    return {"job_id": job.id}
```

### services/scraper.py — single Playwright browser, sequential
```python
from playwright.async_api import async_playwright

ONE_SHOT_JS = """() => {
  const HEADING = /ingr|compos|inhalt|ingrédients|składn|成分|전성분|ingredienti|ingredientes|المكونات/i;
  const STOP   = /how to use|features|results|our active|product details|ratings|read more|description|benefits|directions/i;
  const MAX = 1500;

  const allBtns = [...document.querySelectorAll('button,h3,h4,[role=tab],summary')]
    .filter(el => HEADING.test(el.textContent) && el.textContent.trim().length < 60);
  const btn = allBtns.find(el => /^ingredients$/i.test(el.textContent.trim())) || allBtns[0];
  if (btn) {
    btn.click();
    const scope = btn.closest('[class*="Accordion" i],[class*="panel" i],[class*="tab" i]') || btn.parentElement;
    const inner = scope && [...scope.querySelectorAll('[class*="body" i],[class*="content" i],[class*="inner" i]')]
      .find(el => el !== btn && el.textContent.trim().length > 30);
    const t = inner ? inner.textContent.trim().slice(0, MAX) : '';
    if (t.length > 30) return t;
  }
  const h = [...document.querySelectorAll('h1,h2,h3,h4,strong,label')]
    .filter(el => HEADING.test(el.textContent) && el.textContent.trim().length < 60);
  const heading = h.find(el => /^ingredients$/i.test(el.textContent.trim())) || h[0];
  if (heading) {
    let text = '', el = heading.nextElementSibling;
    while (el && text.length < MAX) { text += el.textContent; el = el.nextElementSibling; }
    const s = text.search(STOP);
    const r = (s > 50 ? text.slice(0, s) : text).trim().slice(0, MAX);
    if (r.length > 30) return r;
  }
  const body = document.body.innerText;
  const idx = body.search(/\\bingredients\\b/i);
  if (idx !== -1) {
    let chunk = body.slice(idx, idx + MAX);
    const s = chunk.search(STOP); if (s > 50) chunk = chunk.slice(0, s);
    if (chunk.trim().length > 30) return chunk.trim();
  }
  const matches = body.match(/(?:[A-Z][A-Z\\d\\s\\-\\/\\(\\)]{5,},\\s*){3,}[A-Z][A-Z\\d\\s\\-\\/\\(\\)]{5,}/g);
  return matches ? matches.sort((a,b) => b.length - a.length)[0].slice(0, MAX) : null;
}"""

async def scrape(url: str) -> dict:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000)
            name = (await page.title()).split(" | ")[0].split(" - ")[0].strip()
            ingredients = await page.evaluate(ONE_SHOT_JS)
            return {"url": url, "name": name, "ingredients_raw": ingredients or "Not listed"}
        except Exception as e:
            return {"url": url, "name": "", "ingredients_raw": "Not listed", "error": str(e)}
        finally:
            await browser.close()
```

### services/classifier.py — Claude API, mapping cached once at module load
```python
import anthropic, json
from pathlib import Path

client   = anthropic.AsyncAnthropic()
MAPPING  = Path("data/mapped-ingredients.txt").read_text()  # loaded once at startup

SYSTEM = """You are an ingredient classifier for hair colour products.
Return JSON only:
{
  "in_scope": true/false,
  "scope_reason": "...",
  "components": {
    "Component Name": ["ingredient 1", "ingredient 2"],
    "Another Component": ["..."]
  },
  "dye_actives": ["ingredient name if it is a dye active"],
  "internal_names": {"ingredient": "mapped name or null"}
}
Use "components" to group ingredients by product section (e.g. Developer, Pigment, Mask).
If the product has no sections, use {"All": [...]} as the single component.
Dye actives: p-Phenylenediamine, Resorcinol, Aminophenol, Hydrogen Peroxide,
Persulfate, Acid Violet, Basic Red, HC Red/Blue/Yellow, Disperse Violet, Lawsone, Indigo."""

async def classify(name: str, url: str, ingredients_raw: str) -> dict:
    resp = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=[
            {"type": "text", "text": SYSTEM},
            {"type": "text", "text": f"Mapping:\n{MAPPING}",
             "cache_control": {"type": "ephemeral"}}
        ],
        messages=[{"role": "user", "content":
            f"Product: {name}\nURL: {url}\nIngredients: {ingredients_raw}\n\nReturn JSON only."}]
    )
    return json.loads(resp.content[0].text)
```

Note: the classifier now returns `components` (grouped) instead of a flat list — this drives the component-grouped display in ProductCard directly from the API, no frontend parsing needed.

---

## UI Screens — Detailed Spec

### Screen 1: Home / URL Input (`/`)
```
┌──────────────────────────────────────────────┐
│  🧪 Formulation Wiki              [Jobs] [↗] │
├──────────────────────────────────────────────┤
│                                              │
│  Paste product URLs — one per line           │
│  ┌────────────────────────────────────────┐  │
│  │ https://www.ulta.com/p/...             │  │
│  │ https://www.loreal-paris.co.uk/...     │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [📎 Upload input.txt]    3 URLs detected    │
│  ● ulta.com  ● loreal-paris.co.uk           │
│                                              │
│  [       Start Scraping →       ]            │
│                                              │
├──────────────────────────────────────────────┤
│  Recent Runs                                 │
│  2026-04-24  41 products  ✓ Complete  [View] │
│  2026-04-23  12 products  ✓ Complete  [View] │
└──────────────────────────────────────────────┘
```
- Textarea: one URL per line, basic HTML5 URL validation on submit
- File upload: parses `input.txt` format, strips `#` comments, populates textarea
- Domain chips shown as preview below textarea
- Submit disables until ≥1 URL entered

---

### Screen 2: Live Job Progress (`/jobs/[id]`)
```
┌────────────────────────────────────────────────────────┐
│  ← Back    Job 2026-04-24 14:32  •  🟡 Running         │
├────────────────────────────────────────────────────────┤
│  ████████████░░░░░░░░  24 / 48 products  (50%)         │
│  Estimated: ~3 min remaining                            │
├────────────────────┬───────────────────────────────────┤
│  Live Feed         │  Stats                            │
│                    │  🟢 In scope:   21                │
│  🟢 IGK 4N Brown   │  🔴 Excluded:    3                │
│     URL match      │  ⚠️  Errors:     0                │
│                    │  ⏱  Avg: 4.2s/product             │
│  🔴 CÉCRED Drops   │                                   │
│     No dye actives │                                   │
│                    │                                   │
│  ⟳  Schwarzkopf..  │                                   │
│     Scraping...    │                                   │
└────────────────────┴───────────────────────────────────┘
│  [View Results]  ← appears on completion                │
└────────────────────────────────────────────────────────┘
```
SSE hook in React (`useEffect` + `EventSource`) updates progress and live feed in real time.

---

### Screen 3: Run Results (`/results/[jobId]`)

**Export bar (always visible at top):**
```
Run: 2026-04-24  •  41 in scope  •  7 excluded
[⬇ Download CSV]  [⬇ Download MD]  [⬇ Download ZIP]
```

**Tabs:** Products | Ingredients | Excluded

**Products tab — ProductCard:**
```
┌────────────────────────────────────────────────────────┐
│  IGK – 4N Original Brown Permanent Color Kit      🟢   │
│  ulta.com  •  URL contains "permanent-color"           │
│  ⚠️ Dye actives: Hydrogen Peroxide  m-Aminophenol      │
│                  p-Aminophenol  Toluene-2,5-Diamine    │
├────────────────────────────────────────────────────────┤
│  COLOR BLOCK BARRIER GEL                               │
│  Prunus Amygdalus Dulcis Oil  Caprylic/Capric          │
│  Triglyceride  Glycerin  Sucrose Laurate  Water        │
├────────────────────────────────────────────────────────┤
│  NOURISHING COLOR DEVELOPER                            │
│  Water  [Hydrogen Peroxide ⚠️]  Cetearyl Alcohol       │
│  Squalane  Etidronic Acid  Phosphoric Acid  ···        │
├────────────────────────────────────────────────────────┤
│  COLOR RICH CREAM PIGMENT                              │
│  Water  Cetyl Alcohol  [Toluene-2,5-Diamine ⚠️]        │
│  Cocamide MEA  [m-Aminophenol ⚠️]  ···                 │
│  [▼ Show all 28 ingredients]                           │
├────────────────────────────────────────────────────────┤
│  POST-COLOR TREATMENT MASK                             │
│  Water  Cetearyl Alcohol  Cetrimonium Chloride  ···    │
└────────────────────────────────────────────────────────┘
```

Ingredient display rules:
- **Dye actives** → amber pill with ⚠️, listed in card header summary
- **Mapped ingredients** (have internal name) → dotted underline + hover tooltip
- **Components** → section header in ALL CAPS, sourced directly from Claude API `components` field
- Lists >8 items → collapsed with "Show all N" toggle
- INCI names preserved exactly as scraped

**Ingredients tab:**
```
[Search...]  [⚠️ Dye actives only]    Showing 55 ingredients

Ingredient              Internal Name     Count   Frequency
─────────────────────────────────────────────────────────
Cetearyl Alcohol        Test Wax Blend      7    ███████
Aqua / Water            Test Water          7    ███████
Phenoxyethanol          Test Dye Coupler    4    ████
⚠️ Hydrogen Peroxide     —                   3    ███
Glycerin                —                   4    ████
```
- Amber left border on dye active rows
- Click any row → expandable panel listing which products contain it
- Sort by count (default) or name; client-side, no API call needed

**Excluded tab:** table of excluded products with name, URL, reason.

---

### Screen 4: Global Ingredients (`/results`)
Same ingredient table across all runs. Adds:
- Run filter dropdown
- Date range filter
- [Download Master CSV] button

---

## Deployment — Single Docker Container

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Install Node for frontend build
RUN apt-get update && apt-get install -y nodejs npm curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build React frontend
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci
COPY frontend/ frontend/
RUN cd frontend && npm run build

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

# Copy backend
COPY backend/ backend/
COPY data/ backend/data/

WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml — single service
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./db:/app/db             # SQLite file persisted here
      - ./exports:/app/exports   # generated CSV/MD/ZIP
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    restart: unless-stopped
```

Start everything:
```bash
docker compose up -d
```
App available at `http://localhost:8000`. Frontend and backend on the same port — no CORS issues.

---

## Token Cost Reference

| Item | Tokens |
|---|---|
| Per-product input (name + ingredients + cached mapping) | ~400 |
| Cached mapping (paid once per session at $0.15/M) | ~200 |
| Per-product output (structured JSON with components) | ~250 |
| **Per-product total** | **~$0.002** |

For 10K products: use Anthropic Batch API (50% discount) → **~$10–15 total**.

---

## Build Timeline (with Claude Code)

| Phase | Scope | Estimate |
|---|---|---|
| **Phase 1** | FastAPI + SQLite + Playwright + Claude API + URL input → results table | Day 1 |
| **Phase 2** | SSE live progress, ProductCard with component grouping + dye badges, export endpoints | Day 2 |
| **Phase 3** | Frequency chart, global ingredients screen, Docker single-container build | Day 3 |
| **Phase 4** | Polish: empty states, error handling, mobile responsiveness | Half day |

**Total: ~3–3.5 days with Claude Code**

---

## Cost Summary

| Scale | Approach | Est. API cost |
|---|---|---|
| 1K products | Hybrid + real-time API | ~$2 |
| 10K products | Hybrid + Batch API | ~$10–15 |
| 100K products | Hybrid + Batch API | ~$100–150 |

---

## Limitations of This Simplified Design (and when to revisit)

| Limitation | Threshold to revisit |
|---|---|
| BackgroundTasks are lost if server restarts mid-job | If jobs routinely exceed 2 hours or uptime is unreliable → add `arq` (Redis-lite queue, much simpler than Celery) |
| SQLite single-writer lock | If multiple users submit jobs simultaneously → PostgreSQL |
| Sequential scraping (1 product at a time) | If 10K products in <1 hour is required → add BrowserPool with 3–5 concurrent contexts |

For the stated requirements (small users, 10K total over time), none of these thresholds apply.

---

## Key Reference Files (CLI repo)

| File | Purpose |
|---|---|
| `.claude/commands/get-ingredients.md` | Scraping logic + one-shot JS — port directly to `scraper.py` |
| `data/mapped-ingredients.txt` | Ingredient → internal name mapping (copy to `backend/data/`) |
| `output/ingredients-master.csv` | Existing data — import into SQLite `ingredients` table on first run |
| `input.txt` | CLI URL list — replaced by UI textarea in web app |

---

## Build Order

1. `docker-compose.yml` + `Dockerfile` skeleton
2. `backend/database.py` + `models.py` → SQLite tables created on startup
3. `backend/services/scraper.py` → test against a real Ulta URL
4. `backend/services/classifier.py` → test Claude API JSON output
5. `backend/services/job_runner.py` → wire scraper + classifier + DB writes
6. `backend/routers/jobs.py` + `stream.py` → submit job, SSE endpoint
7. `backend/routers/exports.py` → CSV / MD / ZIP generation
8. Frontend: URL input (Screen 1) → wire to POST /api/jobs
9. Frontend: Live progress (Screen 2) → SSE hook
10. Frontend: ProductCard + IngredientTable + ExportBar (Screen 3)
11. Frontend: Global ingredients (Screen 4)
12. Docker build → single container test → deploy
