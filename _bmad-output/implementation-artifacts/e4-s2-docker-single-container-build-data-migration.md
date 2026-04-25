# Story E4-S2: Docker Single-Container Build & Data Migration

**Epic:** E4 — Global Ingredients & Deployment  
**Story ID:** E4-S2  
**Status:** ready-for-dev  
**Date Created:** 2026-04-25

---

## User Story

As a developer  
I want to build and run the full app in a single Docker container  
So that deployment is one command

---

## Acceptance Criteria

- [ ] `docker compose up -d` builds and starts without errors
- [ ] App accessible at `http://localhost:8000`
- [ ] Frontend SPA served by FastAPI at `/` with correct React Router client-side routing (fallback to `index.html`)
- [ ] SQLite file persisted in `./db/` volume across container restarts
- [ ] Exports persisted in `./exports/` volume
- [ ] On first run, existing `output/ingredients-master.csv` can be imported into `ingredients` table via a one-shot script

---

## Technical Requirements

### This Story Is Primarily Integration + Verification

E1-S1 already defined the Dockerfile and docker-compose.yml. This story finalizes and verifies them work end-to-end with the full codebase built in E1–E4.

### Dockerfile (Final — Finalize from E1-S1 Draft)

```dockerfile
# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime with Playwright
FROM python:3.12-slim
WORKDIR /app

# System deps for Playwright chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libx11-6 libx11-xcb1 libxcb1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY backend/ ./backend/
COPY --from=frontend-build /frontend/dist ./frontend/dist

RUN mkdir -p /app/db /app/exports

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml (Final)

```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./db:/app/db
      - ./exports:/app/exports
    env_file: .env
    restart: unless-stopped
```

### React Router Fallback — StaticFiles with html=True

The `html=True` parameter in `StaticFiles` enables SPA mode: unknown paths serve `index.html`. This is already in `main.py` from E1-S1. Verify this works:

```bash
# After `docker compose up`:
curl http://localhost:8000/              # → index.html
curl http://localhost:8000/results      # → index.html (React Router handles client-side)
curl http://localhost:8000/api/health   # → {"status": "ok"}
```

**Critical:** API routes must be registered BEFORE the StaticFiles mount in `main.py`. The StaticFiles mount is a catch-all.

### One-Shot Data Migration Script

`backend/scripts/import_master.py` — imports existing `output/ingredients-master.csv` into the DB:

```python
#!/usr/bin/env python3
"""
One-time import of existing ingredients-master.csv into the SQLite database.
Usage: python -m backend.scripts.import_master [csv_path]
"""
import csv, sys
from pathlib import Path
from backend.database import SessionLocal, engine, Base
from backend.models import Ingredient

def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/ingredients-master.csv")
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    imported = 0
    skipped = 0
    
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("ingredient", "").strip()
            if not name:
                continue
            
            existing = db.query(Ingredient).filter(Ingredient.name == name).first()
            if existing:
                # Merge counts
                existing.count += int(row.get("count", 0))
                if row.get("internal_name") and not existing.internal_name:
                    existing.internal_name = row["internal_name"]
                skipped += 1
            else:
                ing = Ingredient(
                    name=name,
                    internal_name=row.get("internal_name") or None,
                    count=int(row.get("count", 1)),
                    is_dye_active=False,
                )
                db.add(ing)
                imported += 1
    
    db.commit()
    db.close()
    print(f"Import complete: {imported} new, {skipped} merged")

if __name__ == "__main__":
    main()
```

### Smoke Test Checklist

After `docker compose up -d`, verify:
- [ ] `curl http://localhost:8000/api/health` → `{"status": "ok"}`
- [ ] `curl http://localhost:8000/` → HTML page with React app
- [ ] `curl http://localhost:8000/results` → Same HTML (SPA fallback working)
- [ ] `curl -X POST http://localhost:8000/api/jobs -H "Content-Type: application/json" -d '{"urls": ["https://example.com"]}'` → `{"job_id": "..."}`
- [ ] `ls ./db/` → `formulation_wiki.db` exists
- [ ] Stop and restart container, verify DB persists

### .env.example

```env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Implementation Tasks

- [ ] Finalise `Dockerfile` (multi-stage: Node build → Python runtime)
- [ ] Finalise `docker-compose.yml`
- [ ] Verify `StaticFiles` mount with `html=True` handles React Router paths correctly
- [ ] Write `backend/scripts/import_master.py` for one-time CSV import
- [ ] End-to-end smoke test: submit job → live progress → view results → export

---

## Dev Notes

### Playwright System Deps in Docker

The Playwright chromium system dependencies must be installed manually in the Dockerfile (rather than using `playwright install --with-deps`) to keep control over which packages are installed. The list above covers chromium on Debian slim. If chromium fails to launch, check the error message for missing libs and add them.

### Multi-Stage Build: Node Not in Final Image

The final image only contains the Python runtime + built frontend assets. Node.js is not in the final layer — this keeps the image lean. The Vite build output (`frontend/dist/`) is copied from the `frontend-build` stage.

### Volume Permissions

Docker volumes created by docker compose are owned by root. The Python process (running as root in the container by default) can write to `/app/db/` and `/app/exports/`. If you add a non-root user in the Dockerfile, ensure the `mkdir -p` and `chown` are handled accordingly.

### Running the Migration Script

From the host (with Docker running):
```bash
# Copy the CSV into the container and run the script
docker compose exec app python -m backend.scripts.import_master /path/to/ingredients-master.csv
```

Or copy the CSV file to a mounted volume path first.

### No Hot Reload in Production Container

The CMD uses `uvicorn` without `--reload`. For development, use `docker compose` with a bind mount for the `backend/` directory and add `--reload` to the CMD override. Don't add `--reload` to the production Dockerfile.

### E5 Stories: End-to-End Test

This story includes a full smoke test. After E5 (Polish & Quality), do a final end-to-end test to confirm all features work together in the Docker container.
