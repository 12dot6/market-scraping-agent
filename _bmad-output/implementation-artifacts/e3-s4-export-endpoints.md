# Story E3-S4: Export Endpoints

**Epic:** E3 — Results UI & Export  
**Story ID:** E3-S4  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a user  
I want to download per-run and global exports as CSV, MD, and ZIP  
So that I can use the data in spreadsheets and reports

---

## Acceptance Criteria

- [ ] `GET /api/jobs/{id}/export/csv` — ingredients for this run as CSV
- [ ] `GET /api/jobs/{id}/export/md` — formatted markdown report for this run
- [ ] `GET /api/jobs/{id}/export/zip` — CSV + MD bundled as ZIP
- [ ] `GET /api/export/master-csv` — all ingredients across all runs
- [ ] Files saved to `/exports/` directory and returned as file download responses
- [ ] CSV column order: ingredient, internal_name, count, is_dye_active, component

---

## Technical Requirements

### Files to Create

```
backend/
├── services/
│   └── export_service.py          ← generates CSV/MD/ZIP from DB
└── routers/
    └── exports.py                 ← four endpoints
```

### export_service.py

```python
import csv, io, zipfile, os
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session, joinedload
from backend.models import Job, Product, Ingredient, ProductIngredient

EXPORTS_DIR = Path("/app/exports")

def _ensure_exports_dir():
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_run_csv(db: Session, job_id: str) -> Path:
    _ensure_exports_dir()
    
    products = (
        db.query(Product)
        .filter(Product.job_id == job_id, Product.in_scope == True)
        .options(joinedload(Product.product_ingredients).joinedload(ProductIngredient.ingredient))
        .all()
    )
    
    # Aggregate: ingredient → {internal_name, count_in_run, is_dye_active, component}
    seen = {}
    for product in products:
        for pi in product.product_ingredients:
            ing = pi.ingredient
            key = ing.name
            if key not in seen:
                seen[key] = {
                    "ingredient": ing.name,
                    "internal_name": ing.internal_name or "",
                    "count": 0,
                    "is_dye_active": ing.is_dye_active,
                    "component": pi.component,
                }
            seen[key]["count"] += 1
    
    rows = sorted(seen.values(), key=lambda r: -r["count"])
    
    job = db.query(Job).filter(Job.id == job_id).first()
    date_str = job.created_at.strftime("%Y-%m-%d")
    filename = EXPORTS_DIR / f"run-{date_str}-{job_id[:8]}.csv"
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ingredient", "internal_name", "count", "is_dye_active", "component"])
        writer.writeheader()
        writer.writerows(rows)
    
    return filename


def generate_run_md(db: Session, job_id: str) -> Path:
    _ensure_exports_dir()
    
    job = db.query(Job).filter(Job.id == job_id).first()
    products = (
        db.query(Product)
        .filter(Product.job_id == job_id)
        .options(joinedload(Product.product_ingredients).joinedload(ProductIngredient.ingredient))
        .all()
    )
    
    date_str = job.created_at.strftime("%Y-%m-%d")
    lines = [
        f"# Formulation Wiki Export — {date_str}",
        f"",
        f"**Job ID:** {job_id}  ",
        f"**Products scraped:** {job.url_count}  ",
        f"**In scope:** {job.in_scope}  ",
        f"**Excluded:** {job.excluded}  ",
        f"**Errors:** {job.errors}  ",
        f"",
        "---",
        "",
    ]
    
    for product in sorted(products, key=lambda p: not p.in_scope):
        lines.append(f"## {product.name or product.url}")
        lines.append(f"**URL:** {product.url}  ")
        lines.append(f"**In scope:** {'Yes' if product.in_scope else 'No'}  ")
        if product.scope_reason:
            lines.append(f"**Reason:** {product.scope_reason}  ")
        lines.append("")
        
        if product.in_scope and product.product_ingredients:
            # Group by component
            from collections import defaultdict
            components = defaultdict(list)
            for pi in product.product_ingredients:
                components[pi.component].append(pi)
            
            for component, pis in components.items():
                lines.append(f"### {component}")
                for pi in pis:
                    marker = " ⚠️" if pi.is_dye_active else ""
                    internal = f" _(→ {pi.ingredient.internal_name})_" if pi.ingredient.internal_name else ""
                    lines.append(f"- {pi.ingredient.name}{marker}{internal}")
                lines.append("")
        lines.append("---")
        lines.append("")
    
    filename = EXPORTS_DIR / f"run-{date_str}-{job_id[:8]}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    return filename


def generate_run_zip(db: Session, job_id: str) -> Path:
    csv_path = generate_run_csv(db, job_id)
    md_path = generate_run_md(db, job_id)
    
    job = db.query(Job).filter(Job.id == job_id).first()
    date_str = job.created_at.strftime("%Y-%m-%d")
    zip_path = EXPORTS_DIR / f"run-{date_str}-{job_id[:8]}.zip"
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, csv_path.name)
        zf.write(md_path, md_path.name)
    
    return zip_path


def generate_master_csv(db: Session) -> Path:
    _ensure_exports_dir()
    
    ingredients = db.query(Ingredient).order_by(Ingredient.count.desc()).all()
    
    filename = EXPORTS_DIR / "ingredients-master.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ingredient", "internal_name", "count", "is_dye_active"])
        writer.writeheader()
        for ing in ingredients:
            writer.writerow({
                "ingredient": ing.name,
                "internal_name": ing.internal_name or "",
                "count": ing.count,
                "is_dye_active": ing.is_dye_active,
            })
    
    return filename
```

### routers/exports.py

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services.export_service import (
    generate_run_csv, generate_run_md, generate_run_zip, generate_master_csv
)

router = APIRouter(tags=["exports"])

@router.get("/api/jobs/{job_id}/export/csv")
def export_run_csv(job_id: str, db: Session = Depends(get_db)):
    path = generate_run_csv(db, job_id)
    return FileResponse(path, media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={path.name}"})

@router.get("/api/jobs/{job_id}/export/md")
def export_run_md(job_id: str, db: Session = Depends(get_db)):
    path = generate_run_md(db, job_id)
    return FileResponse(path, media_type="text/markdown",
                        headers={"Content-Disposition": f"attachment; filename={path.name}"})

@router.get("/api/jobs/{job_id}/export/zip")
def export_run_zip(job_id: str, db: Session = Depends(get_db)):
    path = generate_run_zip(db, job_id)
    return FileResponse(path, media_type="application/zip",
                        headers={"Content-Disposition": f"attachment; filename={path.name}"})

@router.get("/api/export/master-csv")
def export_master_csv(db: Session = Depends(get_db)):
    path = generate_master_csv(db)
    return FileResponse(path, media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=ingredients-master.csv"})
```

### Register Router in main.py

```python
from backend.routers import exports
app.include_router(exports.router)
```

---

## Implementation Tasks

- [ ] Create `backend/services/export_service.py` — generates MD, CSV, ZIP from DB query
- [ ] Create `backend/routers/exports.py` — four endpoints using `FileResponse`
- [ ] Verify master CSV includes deduplicated ingredient rows with total count
- [ ] Register exports router in `main.py`

---

## Dev Notes

### FileResponse + Content-Disposition

`FileResponse` from FastAPI serves file downloads. The `Content-Disposition: attachment` header triggers browser download. The `filename=` in the header sets the suggested download filename.

### /exports/ Volume

The `/app/exports/` directory is mounted as a Docker volume (`./exports:/app/exports`). Files written here persist across container restarts. The `_ensure_exports_dir()` call handles first-run creation inside the container.

### CSV Column Order

The AC specifies: `ingredient, internal_name, count, is_dye_active, component`

The master CSV omits `component` (a global aggregate doesn't have a single component). The per-run CSV includes `component`.

### Master CSV vs. Per-Run CSV

- **Master CSV**: reads directly from `Ingredient` table (global counts accumulated across all runs)
- **Per-run CSV**: joins through `Product → ProductIngredient → Ingredient` and counts per-run occurrences

The `Ingredient.count` field is the global count (incremented every time a product is ingested). The per-run count is recalculated at export time by counting junction rows.

### Regeneration on Each Call

Exports are regenerated on every API call (not cached). For small datasets (<10K products), this is fast. The files are also saved to disk for reference.

### ZIP Contents

The ZIP contains two files: `run-{date}-{job_id_prefix}.csv` and `run-{date}-{job_id_prefix}.md`. Both are generated fresh before zipping.
