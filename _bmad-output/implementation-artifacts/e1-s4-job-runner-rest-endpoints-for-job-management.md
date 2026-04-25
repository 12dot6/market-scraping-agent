# Story E1-S4: Job Runner & REST Endpoints for Job Management

**Epic:** E1 — Backend Foundation  
**Story ID:** E1-S4  
**Status:** done  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want to submit URLs and retrieve job status and results via API  
So that the frontend can wire up to a working backend

---

## Acceptance Criteria

- [ ] `POST /api/jobs` with `{urls: [...]}` creates a job record, starts BackgroundTask, returns `{job_id}` immediately
- [ ] BackgroundTask: for each URL → scrape → classify → write `products` + `ingredients` + `product_ingredients` rows → update `jobs.processed` count
- [ ] `GET /api/jobs` returns list of jobs, most recent first
- [ ] `GET /api/jobs/{id}` returns job detail with progress counts
- [ ] `GET /api/jobs/{id}/products` returns full product list with classified ingredients

---

## Technical Requirements

### Files to Create

```
backend/
├── services/
│   └── job_runner.py          ← orchestrates scrape → classify → DB writes
└── routers/
    ├── jobs.py                ← POST + GET /api/jobs and /api/jobs/{id}
    └── results.py             ← GET /api/jobs/{id}/products
```

### Request/Response Schemas (in `schemas.py`)

```python
# POST /api/jobs
class JobCreate(BaseModel):
    urls: list[str]  # min 1 URL

# Response: POST /api/jobs
class JobCreated(BaseModel):
    job_id: str  # UUID as string

# GET /api/jobs item
class JobSummary(BaseModel):
    id: str
    status: str  # queued | running | complete | failed
    url_count: int
    processed: int
    in_scope: int
    excluded: int
    errors: int
    created_at: datetime
    completed_at: datetime | None

# GET /api/jobs/{id}
class JobDetail(JobSummary):
    started_at: datetime | None

# Ingredient in product response
class IngredientItem(BaseModel):
    name: str
    internal_name: str | None
    component: str
    is_dye_active: bool

# GET /api/jobs/{id}/products item
class ProductResult(BaseModel):
    id: str
    url: str
    name: str
    in_scope: bool
    scope_reason: str | None
    ingredients: list[IngredientItem]
    error: str | None
```

### job_runner.py — Core Orchestration Logic

```python
import asyncio
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Job, Product, Ingredient, ProductIngredient
from backend.services.scraper import scrape
from backend.services.classifier import classify

async def run_job(job_id: str, urls: list[str]):
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        for url in urls:
            try:
                # 1. Scrape
                scrape_result = await scrape(url)
                
                # 2. Classify
                classify_result = await classify(
                    name=scrape_result["name"],
                    url=url,
                    ingredients_raw=scrape_result["ingredients_raw"]
                )
                
                # 3. Persist product
                product = Product(
                    id=str(uuid4()),
                    job_id=job_id,
                    url=url,
                    name=scrape_result["name"],
                    ingredients_raw=scrape_result["ingredients_raw"],
                    in_scope=classify_result["in_scope"],
                    scope_reason=classify_result.get("scope_reason"),
                )
                db.add(product)
                db.flush()
                
                # 4. Persist ingredients + junction (only for in-scope products)
                if classify_result["in_scope"]:
                    _persist_ingredients(db, product.id, classify_result)
                    job.in_scope += 1
                else:
                    job.excluded += 1
                    
            except Exception as e:
                # Per-URL failure: log error, increment counter, continue
                product = Product(
                    id=str(uuid4()),
                    job_id=job_id,
                    url=url,
                    name="",
                    ingredients_raw="",
                    in_scope=False,
                    error=str(e),
                )
                db.add(product)
                job.errors += 1
            
            job.processed += 1
            db.commit()
        
        job.status = "complete" if job.errors < len(urls) else "failed"
        job.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

def _persist_ingredients(db: Session, product_id: str, classify_result: dict):
    """Upsert ingredients globally; create junction rows."""
    for component_name, ingredient_names in classify_result.get("components", {}).items():
        for ing_name in ingredient_names:
            is_dye = ing_name in classify_result.get("dye_actives", [])
            internal = classify_result.get("internal_names", {}).get(ing_name)
            
            # Upsert ingredient (global registry)
            ing = db.query(Ingredient).filter(
                Ingredient.name == ing_name
            ).first()
            if ing:
                ing.count += 1
                if internal and not ing.internal_name:
                    ing.internal_name = internal
                if is_dye:
                    ing.is_dye_active = True
            else:
                ing = Ingredient(
                    name=ing_name,
                    internal_name=internal,
                    count=1,
                    is_dye_active=is_dye
                )
                db.add(ing)
                db.flush()
            
            # Create junction row
            pi = ProductIngredient(
                product_id=product_id,
                ingredient_id=ing.id,
                component=component_name,
                is_dye_active=is_dye,
            )
            db.add(pi)
```

### routers/jobs.py

```python
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import JobCreate, JobCreated, JobSummary, JobDetail
from backend.models import Job
from backend.services.job_runner import run_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.post("", response_model=JobCreated)
async def create_job(body: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = Job(
        id=str(uuid4()),
        status="queued",
        url_count=len(body.urls),
        processed=0, in_scope=0, excluded=0, errors=0,
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    background_tasks.add_task(run_job, job.id, body.urls)
    return {"job_id": job.id}

@router.get("", response_model=list[JobSummary])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).all()

@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

### routers/results.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from backend.database import get_db
from backend.models import Product, ProductIngredient, Ingredient
from backend.schemas import ProductResult, IngredientItem

router = APIRouter(prefix="/api/jobs", tags=["results"])

@router.get("/{job_id}/products", response_model=list[ProductResult])
def get_products(job_id: str, db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .filter(Product.job_id == job_id)
        .options(
            joinedload(Product.product_ingredients)
            .joinedload(ProductIngredient.ingredient)
        )
        .all()
    )
    result = []
    for p in products:
        ingredients = [
            IngredientItem(
                name=pi.ingredient.name,
                internal_name=pi.ingredient.internal_name,
                component=pi.component,
                is_dye_active=pi.is_dye_active,
            )
            for pi in p.product_ingredients
        ]
        result.append(ProductResult(
            id=p.id, url=p.url, name=p.name,
            in_scope=p.in_scope, scope_reason=p.scope_reason,
            ingredients=ingredients, error=p.error,
        ))
    return result
```

### Register Routers in main.py

```python
from backend.routers import jobs, results
app.include_router(jobs.router)
app.include_router(results.router)
# StaticFiles LAST
```

---

## Implementation Tasks

- [x] Create `backend/services/job_runner.py` — orchestrates scrape → classify → DB writes
- [x] Create `backend/routers/jobs.py` — POST + GET endpoints
- [x] Create `backend/routers/results.py` — products endpoint
- [x] Upsert logic for `ingredients` table (increment `count` if name already exists)
- [x] Add `get_db` dependency to `database.py`
- [x] Register routers in `main.py`
- [x] Test full pipeline: submit 3 URLs → verify DB rows and products endpoint response

### Review Findings

- [x] [Review][Patch] Enforce `POST /api/jobs` input contract (`urls` must contain at least one URL) [`backend/schemas.py`]
- [x] [Review][Patch] Guard `run_job()` when job id is missing so background execution exits safely [`backend/services/job_runner.py`]
- [x] [Review][Patch] Prevent duplicate `(product_id, ingredient_id)` junction inserts when same ingredient appears in multiple components [`backend/services/job_runner.py`]
- [x] [Review][Patch] Add regression tests for empty URL rejection, missing job-id handling, and duplicate ingredient component input [`tests/test_jobs_router.py`, `tests/test_job_runner.py`]

---

## Dev Notes

### BackgroundTask Runs in Thread Pool

FastAPI's `BackgroundTasks.add_task()` runs the function after the response is sent, in the thread pool. The `run_job` function uses `asyncio` — if it's `async def`, use `asyncio.run()` wrapper or make it a sync function that calls `asyncio.run(scrape(...))` internally.

Alternatively, use `asyncio.get_event_loop().run_in_executor()` from a sync background task.

### SQLite Session Per Background Task

Do NOT share the `db` session from the request with the background task. Create a new `SessionLocal()` in `run_job()` and close it in `finally`. This is shown in the code above.

### Ingredient Upsert — Flush Before Junction

When creating a new `Ingredient`, call `db.flush()` to get the auto-assigned `id` before creating the `ProductIngredient` junction row. Without `flush()`, `ing.id` will be `None`.

### job.status: "failed" vs "complete"

- `"failed"` = ALL URLs errored (nothing succeeded)  
- `"complete"` = at least 1 URL processed without error (partial success is still "complete")

This is consistent with E5-S2 error handling requirements.

### Sequential Processing Is Intentional

The loop in `run_job` processes URLs one at a time. No parallelism. This is the architectural decision per the PRD — safer against anti-bot measures. Do not add concurrency here.

---

## Dev Agent Record

### Implementation Notes

- `main.py` moved `Base.metadata.create_all` from module-level into an `asynccontextmanager` lifespan handler so tests can import the app without touching the Docker-only DB path (`/app/db/`). `StaticFiles` mount is guarded with `os.path.isdir("frontend/dist")` for the same reason.
- `run_job` is `async def` — FastAPI BackgroundTasks correctly awaits async functions in the event loop (not a thread pool). Sessions are created fresh per job run and closed in `finally`.
- `_persist_ingredients` calls `db.flush()` after inserting a new `Ingredient` to get its auto-assigned `id` before creating the `ProductIngredient` junction row.
- Job status logic: `"failed"` only if ALL URLs errored (`job.errors >= len(urls)`); partial success is `"complete"`.
- `schemas.py` extended with `JobCreated`, `JobSummary`, `JobDetail`, `IngredientItem`, `ProductResult` alongside existing raw response schemas.
- Test infra: in-memory SQLite with `StaticPool` shares a single DB across connections per test. `run_job` tests use a `Session` fixture and re-query state in a fresh session after the coroutine closes its own session.
- 42 total tests pass across all four stories (E1-S1 through E1-S4).

### Completion Notes

All 7 tasks complete. `job_runner.py`, `routers/jobs.py`, `routers/results.py` created. `main.py` updated with lifespan and conditional StaticFiles mount. 21 new tests added (12 unit + 9 integration), all passing. No regressions in prior test suites.

Code review follow-up applied: `JobCreate` now enforces non-empty `urls`, `run_job()` now safely exits if job id is absent, and `_persist_ingredients()` now avoids duplicate junction rows for repeated ingredients across components. Added focused regression tests for each fix.

---

## File List

- `backend/main.py` (updated — lifespan, router registration, conditional StaticFiles)
- `backend/schemas.py` (updated — added JobCreated, JobSummary, JobDetail, IngredientItem, ProductResult)
- `backend/services/job_runner.py`
- `backend/routers/__init__.py`
- `backend/routers/jobs.py`
- `backend/routers/results.py`
- `tests/test_job_runner.py`
- `tests/test_jobs_router.py`

---

## Change Log

- 2026-04-25: E1-S4 implemented — job runner orchestration (scrape→classify→DB), REST endpoints (POST /api/jobs, GET /api/jobs, GET /api/jobs/{id}, GET /api/jobs/{id}/products), ingredient upsert logic, lifespan DB init. 21 unit + integration tests added.
- 2026-04-25: Code review patches applied — validated non-empty job input, hardened missing-job handling, and prevented duplicate product-ingredient junction inserts; added regression tests.
