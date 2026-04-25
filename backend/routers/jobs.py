from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Job
from backend.schemas import JobCreate, JobCreated, JobDetail, JobSummary
from backend.services.job_runner import run_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobCreated)
async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = Job(
        id=str(uuid4()),
        status="queued",
        url_count=len(body.urls),
        processed=0,
        in_scope=0,
        excluded=0,
        errors=0,
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
