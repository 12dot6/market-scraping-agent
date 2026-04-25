# Architecture: Formulation Wiki Web App
_Version 1.0 | 2026-04-24 | Sources: PRD + web-app-plan.md_

---

## 1. Purpose

Define a lightweight, implementation-ready architecture for the Formulation Wiki web app that supports:
- URL-based scrape job submission from browser
- Sequential scraping + Claude classification
- Persistent ingredient frequency analytics
- Per-run and global export workflows

This architecture is intentionally optimized for a small internal user base and ~10K products over time.

---

## 2. Architecture Decision Summary

- **App shape:** Monolith (single FastAPI process serving both API and frontend static assets)
- **Frontend:** Vite + React SPA
- **Backend:** FastAPI with BackgroundTasks
- **Database:** SQLite (WAL mode, local file)
- **Scraping:** Playwright (single headless browser, sequential processing)
- **Classification:** Anthropic Claude API (`claude-sonnet-4-6`)
- **Deployment:** Single Docker container

### Why this design

- Eliminates unnecessary operational complexity (no Redis/Celery/Postgres for current scale).
- Meets requirements for persistence, progress visibility, and exports.
- Keeps implementation and maintenance cost low for a solo/small team workflow.

---

## 3. High-Level System View

```text
Browser (React SPA)
    <-> REST + SSE
FastAPI (single process)
    |- Routers (jobs/results/exports/stream)
    |- BackgroundTask job runner
    |    |- Playwright scraper
    |    \- Claude classifier
    \- SQLite (SQLAlchemy ORM, WAL mode)

Local persisted files:
- /app/db/formulation_wiki.db
- /app/exports/*
```

---

## 4. Core Components

### 4.1 Frontend (Vite + React)
- Screens: Home (URL input), Job Progress (SSE), Run Results (products/ingredients/excluded), Global Ingredients.
- Data fetching: REST for snapshots, SSE for live job progress.
- UX behavior: domain preview chips, progress metrics, ingredient frequency table, export actions.

### 4.2 API Layer (FastAPI)
- `POST /api/jobs`: create job, return `job_id`, start background processing.
- `GET /api/jobs`, `GET /api/jobs/{id}`: job history and status.
- `GET /api/jobs/{id}/products`, `GET /api/ingredients`: result retrieval.
- `GET /api/jobs/{id}/stream`: live progress events via SSE.
- Export endpoints for CSV/MD/ZIP and master CSV.

### 4.3 Job Runner
- Orchestrates: URL list -> scrape product -> classify -> persist -> emit progress event.
- Sequential processing by design to reduce scraping complexity and anti-bot fragility.
- Error-tolerant: failed product should not fail entire job.

### 4.4 Scraper Service
- Async Playwright-based extraction.
- One-shot extraction heuristic ported from `.claude/commands/get-ingredients.md`.
- Timeout-safe; returns `"Not listed"` when ingredients are unavailable.

### 4.5 Classifier Service
- Uses Claude API to produce structured output:
  - `in_scope`
  - `scope_reason`
  - `components`
  - `dye_actives`
  - `internal_names`
- Ingredient mapping data loaded once at startup to reduce per-call overhead.

### 4.6 Persistence (SQLite + SQLAlchemy)
- Tables: `jobs`, `products`, `ingredients`, `product_ingredients`.
- Global ingredient counts maintained incrementally during job ingestion.
- WAL mode enabled to improve read/write behavior under mixed API + background updates.

---

## 5. Data Model (logical)

- **Job**: run metadata and progress counters (`queued/running/complete/failed`, totals, timestamps).
- **Product**: raw scraped record + scope determination for each URL.
- **Ingredient**: normalized global registry with count + optional `internal_name`.
- **ProductIngredient**: junction linking product to ingredient with `component` and `is_dye_active`.

---

## 6. Key Runtime Flows

### 6.1 Job Execution Flow
1. User submits one or more URLs.
2. API creates `job` row and schedules background task.
3. Job runner processes discovered products sequentially.
4. For each product: scrape -> classify -> persist product + ingredient relations.
5. SSE emits `product_done` events continuously.
6. On completion, job status updated and `job_complete` event emitted.

### 6.2 Read & Export Flow
1. UI reads job/product/ingredient APIs for display.
2. Export endpoints materialize per-run CSV/MD/ZIP and global master CSV from DB.
3. Files are stored under `/exports` and returned as downloads.

---

## 7. Non-Functional Decisions

- **Reliability:** Graceful per-product failure handling; job-level completion despite partial errors.
- **Performance target:** Sequential throughput acceptable for overnight 10K processing.
- **Cost control:** Batch API for larger ingestion runs.
- **Security (internal scope):** No multi-tenant or RBAC; keep secret management via `.env`.
- **Operability:** Single service deployment; standard Python logging.

---

## 8. Constraints and Trade-Offs

- **BackgroundTasks durability:** In-flight jobs can be lost on app restart.
- **SQLite writer model:** Suitable for low-concurrency writes; reassess if parallel job submission grows.
- **Sequential scrape throughput:** Simpler and safer now; revisit parallel browser contexts only if SLA demands.

---

## 9. Evolution Triggers

Revisit architecture when any threshold is hit:
- frequent restart-related job loss -> introduce durable queue/worker
- sustained concurrent job submissions -> move SQLite to PostgreSQL
- need for much faster ingestion (<1h for 10K) -> add controlled scrape parallelism

---

## 10. Implementation Alignment

This architecture aligns directly with:
- PRD feature requirements (`FR-01` to `FR-09`)
- Epic sequence in `epics-and-stories-formulation-wiki-web-app-2026-04-24.md`
- Existing scraping logic in `.claude/commands/get-ingredients.md`

Recommended next BMAD step: **[IR] Check Implementation Readiness** (`bmad-check-implementation-readiness`).
