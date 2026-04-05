import asyncio
import logging
import uuid

from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.telegram.account_manager import AccountManager, NoAvailableAccountError

logger = logging.getLogger(__name__)


async def process_job(job_id: uuid.UUID, account_manager: AccountManager) -> None:
    """
    FastAPI background task: send the job's photo to @mycommentinst_bot via an
    available Telegram account and persist the reply.

    This function creates its own DB sessions so it runs safely after the HTTP
    response has been sent and the request-scoped session has been closed.
    """
    logger.info("Starting job %s", job_id)

    # ── 1. Acquire a free Telegram account ───────────────────────────────────
    try:
        account_id, client = await account_manager.acquire()
    except NoAvailableAccountError as exc:
        logger.error("Job %s failed — no available accounts: %s", job_id, exc)
        with Session(engine) as db:
            crud.analysis_job.fail(db, job_id, str(exc))
        return

    # ── 2. Mark job as processing and load photo data ────────────────────────
    with Session(engine) as db:
        crud.analysis_job.set_processing(db, job_id, account_id)
        job = crud.analysis_job.get(db, job_id)
        if job is None:
            await account_manager.release(account_id)
            return
        photo_bytes = job.photo_bytes
        photo_filename = job.photo_filename

    # ── 3. Send to bot and await reply ───────────────────────────────────────
    try:
        reply = await client.send_photo_and_get_reply(
            photo_bytes=photo_bytes,
            filename=photo_filename,
            target_bot=settings.TELEGRAM_TARGET_BOT,
            timeout=settings.TELEGRAM_REPLY_TIMEOUT_SECONDS,
        )
        with Session(engine) as db:
            crud.analysis_job.complete(db, job_id, result={"text": reply})
            crud.telegram_account.update_last_used(db, account_id)
        logger.info("Job %s completed", job_id)

    except asyncio.TimeoutError:
        error = (
            f"No reply from bot within {settings.TELEGRAM_REPLY_TIMEOUT_SECONDS}s"
        )
        logger.warning("Job %s timed out", job_id)
        with Session(engine) as db:
            crud.analysis_job.fail(db, job_id, error)

    except Exception as exc:
        # Import here to avoid hard dependency at module level if telethon isn't installed
        try:
            from telethon.errors import FloodWaitError

            if isinstance(exc, FloodWaitError):
                logger.warning(
                    "Account %s hit FloodWait (%ds)", account_id, exc.seconds
                )
                with Session(engine) as db:
                    crud.analysis_job.fail(
                        db, job_id, f"Rate limited — retry after {exc.seconds}s"
                    )
                    crud.telegram_account.mark_rate_limited(
                        db, account_id, exc.seconds
                    )
                # Remove from pool; it will be re-added if status is restored via admin API
                await account_manager.remove_account(account_id)
                return  # skip the release below — account was already removed
        except ImportError:
            pass

        logger.exception("Job %s failed with unexpected error", job_id)
        with Session(engine) as db:
            crud.analysis_job.fail(db, job_id, str(exc))

    finally:
        await account_manager.release(account_id)
