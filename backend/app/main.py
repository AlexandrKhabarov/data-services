import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from sqlmodel import Session

from app import crud
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import engine
from app.telegram.account_manager import AccountManager

logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    return route.name


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Telegram account pool ─────────────────────────────────────────────
    account_manager = AccountManager()

    with Session(engine) as db:
        accounts = crud.telegram_account.get_active(db)

    for account in accounts:
        try:
            await account_manager.add_account(account)
            logger.info("Connected Telegram account: %s", account.phone_number)
        except Exception as exc:
            logger.warning(
                "Failed to connect account %s: %s", account.phone_number, exc
            )

    app.state.account_manager = account_manager
    logger.info("Telegram pool ready — %d active client(s)", len(account_manager))

    yield

    await account_manager.shutdown()
    logger.info("Telegram account pool shut down")


app = FastAPI(
    title="Data Services API",
    description="Telegram photo analysis proxy service",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
