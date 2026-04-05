import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON, LargeBinary
from sqlmodel import Field, SQLModel


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AnalysisJob(SQLModel, table=True):
    __tablename__ = "analysis_jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: JobStatus = Field(default=JobStatus.pending)
    # Raw photo bytes stored in the DB. For large-scale use, replace with
    # an object-storage reference (S3 key, etc.).
    photo_bytes: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    photo_filename: str
    # Parsed response from the Telegram bot
    result: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    error_message: Optional[str] = Field(default=None)
    telegram_account_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="telegram_accounts.id"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
