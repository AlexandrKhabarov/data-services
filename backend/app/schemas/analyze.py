import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.analysis_job import JobStatus


class AnalyzeResponse(BaseModel):
    """Returned immediately after a photo is submitted."""

    job_id: uuid.UUID
    status: JobStatus


class JobStatusResponse(BaseModel):
    """Returned when polling a job by ID."""

    job_id: uuid.UUID
    status: JobStatus
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
