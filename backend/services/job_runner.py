import asyncio
from collections import defaultdict
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Ingredient, Job, Product, ProductIngredient
from backend.services.classifier import classify
from backend.services.scraper import scrape

# In-memory queues: job_id → list of asyncio.Queue (one per SSE client)
_job_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


def register_queue(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _job_queues[job_id].append(q)
    return q


def unregister_queue(job_id: str, q: asyncio.Queue) -> None:
    if job_id in _job_queues:
        try:
            _job_queues[job_id].remove(q)
        except ValueError:
            pass


async def _publish(job_id: str, event: dict) -> None:
    for q in list(_job_queues.get(job_id, [])):
        await q.put(event)


async def run_job(job_id: str, urls: list[str]) -> None:
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        for url in urls:
            _event: dict | None = None
            try:
                scrape_result = await scrape(url)
                classify_result = await classify(
                    name=scrape_result["name"],
                    url=url,
                    ingredients_raw=scrape_result["ingredients_raw"],
                )

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

                if classify_result["in_scope"]:
                    _persist_ingredients(db, product.id, classify_result)
                    job.in_scope += 1
                else:
                    job.excluded += 1

                _event = {
                    "type": "product_done",
                    "name": product.name or url,
                    "in_scope": classify_result["in_scope"],
                    "progress": {"done": job.processed + 1, "total": job.url_count},
                }

            except Exception as e:
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
                _event = {"type": "error", "url": url, "message": str(e)}

            job.processed += 1
            db.commit()
            if _event:
                await _publish(job_id, _event)

        job.status = "complete" if job.errors < len(urls) else "failed"
        job.completed_at = datetime.utcnow()
        db.commit()

        duration = 0.0
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()
        await _publish(job_id, {
            "type": "job_complete",
            "stats": {
                "in_scope": job.in_scope,
                "excluded": job.excluded,
                "duration_sec": round(duration, 1),
            },
        })
    finally:
        db.close()


def _persist_ingredients(db: Session, product_id: str, classify_result: dict) -> None:
    """Upsert ingredients into the global registry; create junction rows."""
    dye_actives = set(classify_result.get("dye_actives", []))
    internal_names = classify_result.get("internal_names", {})
    linked_ingredient_ids: set[int] = set()

    for component_name, ingredient_names in classify_result.get("components", {}).items():
        for ing_name in ingredient_names:
            is_dye = ing_name in dye_actives
            internal = internal_names.get(ing_name)

            ing = db.query(Ingredient).filter(Ingredient.name == ing_name).first()
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
                    is_dye_active=is_dye,
                )
                db.add(ing)
                db.flush()

            # Junction table PK is (product_id, ingredient_id); avoid duplicates
            if ing.id in linked_ingredient_ids:
                continue
            pi = ProductIngredient(
                product_id=product_id,
                ingredient_id=ing.id,
                component=component_name,
                is_dye_active=is_dye,
            )
            db.add(pi)
            linked_ingredient_ids.add(ing.id)
