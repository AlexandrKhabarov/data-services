from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_account_manager
from app.telegram.account_manager import AccountManager

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    telegram_pool: dict[str, int]


@router.get(
    "",
    response_model=HealthResponse,
    summary="Service health and pool statistics",
)
def health_check(
    account_manager: AccountManager = Depends(get_account_manager),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        telegram_pool=account_manager.pool_stats(),
    )
