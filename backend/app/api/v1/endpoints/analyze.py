import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
    status,
)
from sqlmodel import Session

from app import crud
from app.api.deps import get_account_manager, get_db, require_api_key
from app.schemas.analyze import AnalyzeResponse, JobStatusResponse
from app.telegram.account_manager import AccountManager
from app.telegram.worker import process_job

router = APIRouter()

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a photo for analysis",
    description=(
        "Upload a person's photo (JPEG / PNG / WebP, max 10 MB). "
        "The photo is enqueued and forwarded to the Telegram bot asynchronously. "
        "Poll `GET /analyze/{job_id}` until `status` is `completed` or `failed`."
    ),
    dependencies=[Depends(require_api_key)],
)
async def submit_analysis(
    photo: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    account_manager: AccountManager = Depends(get_account_manager),
) -> AnalyzeResponse:
    if photo.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type '{photo.content_type}'. "
            f"Allowed: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}",
        )

    photo_bytes = await photo.read()
    if len(photo_bytes) > _MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo exceeds the {_MAX_PHOTO_BYTES // (1024 * 1024)} MB limit",
        )

    job = crud.analysis_job.create(
        db,
        photo_bytes=photo_bytes,
        photo_filename=photo.filename or "photo.jpg",
    )

    background_tasks.add_task(process_job, job.id, account_manager)

    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll analysis job status",
    dependencies=[Depends(require_api_key)],
)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    job = crud.analysis_job.get(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
