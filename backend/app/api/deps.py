from typing import Generator

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.telegram.account_manager import AccountManager

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def _valid_api_keys() -> set[str]:
    """All keys that are allowed to call the analysis endpoint."""
    keys = set(settings.API_KEYS)
    keys.add(settings.ADMIN_API_KEY)
    return keys


def require_api_key(api_key: str = Security(_api_key_header)) -> None:
    """Dependency: allow any key from API_KEYS or ADMIN_API_KEY."""
    if api_key not in _valid_api_keys():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )


def require_admin_key(api_key: str = Security(_api_key_header)) -> None:
    """Dependency: allow only ADMIN_API_KEY (for account management)."""
    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )


def get_account_manager(request: Request) -> AccountManager:
    return request.app.state.account_manager
