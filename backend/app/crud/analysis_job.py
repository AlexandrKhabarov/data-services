import uuid
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session

from app.models.analysis_job import AnalysisJob, JobStatus


def get(db: Session, job_id: uuid.UUID) -> Optional[AnalysisJob]:
    return db.get(AnalysisJob, job_id)


def create(db: Session, photo_bytes: bytes, photo_filename: str) -> AnalysisJob:
    job = AnalysisJob(photo_bytes=photo_bytes, photo_filename=photo_filename)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def set_processing(
    db: Session, job_id: uuid.UUID, account_id: uuid.UUID
) -> None:
    job = db.get(AnalysisJob, job_id)
    if job:
        job.status = JobStatus.processing
        job.telegram_account_id = account_id
        db.add(job)
        db.commit()


def complete(db: Session, job_id: uuid.UUID, result: dict[str, Any]) -> None:
    job = db.get(AnalysisJob, job_id)
    if job:
        job.status = JobStatus.completed
        job.result = result
        job.completed_at = datetime.utcnow()
        db.add(job)
        db.commit()


def fail(db: Session, job_id: uuid.UUID, error: str) -> None:
    job = db.get(AnalysisJob, job_id)
    if job:
        job.status = JobStatus.failed
        job.error_message = error
        job.completed_at = datetime.utcnow()
        db.add(job)
        db.commit()
