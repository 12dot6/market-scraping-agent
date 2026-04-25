import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from backend.database import get_db
from backend.models import Job
from backend.services.job_runner import register_queue, unregister_queue

router = APIRouter(prefix="/api/jobs", tags=["stream"])


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ("complete", "failed"):
        async def immediate():
            duration = 0.0
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "job_complete",
                    "stats": {
                        "in_scope": job.in_scope,
                        "excluded": job.excluded,
                        "duration_sec": round(duration, 1),
                    },
                }),
            }

        return EventSourceResponse(immediate())

    queue = register_queue(job_id)

    async def generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"event": "message", "data": json.dumps(event)}
                    if event["type"] == "job_complete":
                        break
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            unregister_queue(job_id, queue)

    return EventSourceResponse(generator())
