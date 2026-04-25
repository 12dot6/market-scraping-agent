# PRD: Formulation Wiki Web App
_Version 1.0 | 2026-04-24 | Author: Srini_

---

## 1. Problem Statement

Ingredient research for hair colour/dye-adjacent products is currently a manual, CLI-only workflow. The `/get-ingredients` slash command in Claude Code scrapes product URLs sequentially, classifies ingredients via the Claude API, and writes outputs to flat files. There is no persistent storage, no UI for non-technical users, no job history, and no cross-run ingredient frequency analysis. Productionising this as a web app removes the CLI dependency, adds persistence, and enables frequency-based insight across all scraped products.

---

## 2. Goals

| Goal | Metric |
|------|--------|
| Remove CLI dependency | Any user can submit scrape jobs via browser |
| Persist results across sessions | SQLite DB survives container restarts |
| Surface ingredient frequency | Global ingredient table sortable by count |
| Enable data portability | Per-run and master CSV/MD/ZIP export |
| Keep total API cost bounded | ≤$15 for 10K products via Batch API |

**Non-goals:**
- Public-facing or multi-tenant deployment
- Real-time concurrent scraping (sequential overnight is acceptable)
- SEO or server-side rendering
- Enterprise auth, RBAC, or audit logs

---

## 3. Users

**Primary:** Srini (solo operator) — runs scraping jobs, reviews ingredient classifications, exports data for formulation analysis.

**Secondary:** Small team of domain researchers (≤5 users) who view results and export data but do not submit jobs.

**Scale constraint:** 10K total products over time, not concurrently. No high-traffic requirements.

---

## 4. Architecture Summary

Single Docker container. FastAPI serves the React SPA and the REST/SSE API. SQLite handles persistence (WAL mode, <50MB at 10K products). Playwright scrapes sequentially (1 product at a time, ~5s each). Claude API classifies and maps ingredients. No Redis, no Celery, no separate worker service.

```
Browser (Vite + React SPA)
    ↕ REST + SSE
FastAPI (single process)
    ├── BackgroundTask → Playwright → Claude API
    └── SQLite (WAL mode)
```

**Tech stack:**
- Frontend: Vite + React 18, Tailwind CSS, Shadcn/ui, TanStack Query, Recharts, React Router 6
- Backend: FastAPI, Playwright (async), Anthropic SDK, SQLAlchemy 2.0, Pydantic v2
- Infra: SQLite (WAL), Docker (1 container), /exports/ file store

---

## 5. Feature Requirements

### FR-01: URL Input & Job Submission
- Textarea accepting one URL per line
- File upload parsing `input.txt` format (strips `#` comments)
- Domain chip preview below textarea
- HTML5 URL validation; submit disabled until ≥1 URL
- `POST /api/jobs` returns `job_id` immediately; scraping runs as BackgroundTask

### FR-02: Live Job Progress
- SSE stream at `GET /api/jobs/{id}/stream`
- Progress bar (done/total, %), estimated time remaining
- Live feed: product name + in-scope/excluded status as each completes
- Stats panel: running counts for in-scope, excluded, errors, avg time/product
- "View Results" button appears on job completion

### FR-03: Run Results — Products Tab
- ProductCard per scraped in-scope product
- Ingredient display: component sections (ALL CAPS headers), dye actives as amber ⚠️ pills
- Lists >8 ingredients collapsed with "Show all N" toggle
- Mapped ingredients: dotted underline + hover tooltip showing internal name
- INCI names preserved exactly as scraped

### FR-04: Run Results — Ingredients Tab
- Table: ingredient name, internal name, count, frequency bar
- Dye active rows: amber left border
- Row click → expandable panel listing containing products
- Client-side sort by count (default) or name
- Filter: dye actives only toggle
- Search box (client-side)

### FR-05: Run Results — Excluded Tab
- Table: product name, URL, exclusion reason

### FR-06: Export
- Per-run: CSV, MD, ZIP (CSV + MD combined)
- Global: master CSV across all runs
- Export bar always visible at top of Run Results screen

### FR-07: Global Ingredients Screen
- Same ingredient table as FR-04 across all runs
- Run filter dropdown
- Date range filter
- [Download Master CSV] button

### FR-08: Job History
- Home screen lists recent runs: date, product count, status, [View] link
- `GET /api/jobs` returns jobs most-recent-first

### FR-09: Classification (Claude API)
- Model: `claude-sonnet-4-6`
- Returns: `in_scope`, `scope_reason`, `components` (grouped ingredients), `dye_actives`, `internal_names`
- Ingredient mapping file loaded once at module startup (prompt cache)
- For 10K products: use Anthropic Batch API (50% discount)

---

## 6. Database Schema

Four tables: `jobs`, `products`, `ingredients`, `product_ingredients` (junction).
See `web-app-plan.md` §Database Schema for full DDL.
SQLite WAL + NORMAL synchronous mode enabled on engine connect.

---

## 7. API Surface

```
POST  /api/jobs                       Submit job
GET   /api/jobs                       Job list
GET   /api/jobs/{id}                  Job detail + progress
GET   /api/jobs/{id}/stream           SSE live progress
GET   /api/jobs/{id}/products         Product list for run
GET   /api/ingredients                Global ingredient list
GET   /api/jobs/{id}/export/csv|md|zip  Per-run exports
GET   /api/export/master-csv          Global export
```

---

## 8. Design System

- Component library: Shadcn/ui
- Primary: `#7C3AED` (violet) | Accent: `#F59E0B` (amber, dye highlights)
- Success: `#10B981` | Danger: `#EF4444` | Background: `#FAFAF9`

---

## 9. Deployment

Single Docker container. `docker compose up -d`. App at `http://localhost:8000`.
SQLite and exports persisted via Docker volumes.
`ANTHROPIC_API_KEY` via `.env`.

---

## 10. Constraints & Known Limitations

| Limitation | Threshold to revisit |
|------------|----------------------|
| BackgroundTasks lost on server restart mid-job | Add `arq` if jobs routinely exceed 2h |
| SQLite single-writer lock | Switch to PostgreSQL if multiple concurrent job submitters |
| Sequential scraping | Add BrowserPool (3–5 contexts) if <1h for 10K is required |

---

## 11. Cost Reference

| Scale | Approach | Est. API Cost |
|-------|----------|---------------|
| 1K products | Real-time API | ~$2 |
| 10K products | Batch API | ~$10–15 |
| 100K products | Batch API | ~$100–150 |

---

## 12. Out of Scope (Deliberately Cut)

PostgreSQL, Celery, Redis, BrowserPool, Alembic, Next.js, TanStack Table, react-hook-form/zod, structlog, multiple Docker services.
