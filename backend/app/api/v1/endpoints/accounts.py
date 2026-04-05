import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app import crud
from app.api.deps import get_account_manager, get_db, require_admin_key
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.telegram.account_manager import AccountManager

router = APIRouter()


@router.get(
    "",
    response_model=list[AccountRead],
    summary="List all Telegram accounts",
    dependencies=[Depends(require_admin_key)],
)
def list_accounts(db: Session = Depends(get_db)) -> list[AccountRead]:
    return [AccountRead.model_validate(a) for a in crud.telegram_account.get_all(db)]


@router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a Telegram account to the pool",
)
async def add_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    account_manager: AccountManager = Depends(get_account_manager),
    _: None = Depends(require_admin_key),
) -> AccountRead:
    if crud.telegram_account.get_by_phone(db, data.phone_number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account with phone {data.phone_number!r} already exists",
        )

    account = crud.telegram_account.create(db, data)

    try:
        await account_manager.add_account(account)
    except Exception as exc:
        # Saved to DB but couldn't connect. Admin can fix the session and PATCH.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Account saved but failed to connect: {exc}",
        ) from exc

    return AccountRead.model_validate(account)


@router.get(
    "/{account_id}",
    response_model=AccountRead,
    summary="Get a single Telegram account",
    dependencies=[Depends(require_admin_key)],
)
def get_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AccountRead:
    account = crud.telegram_account.get(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return AccountRead.model_validate(account)


@router.put(
    "/{account_id}",
    response_model=AccountRead,
    summary="Update a Telegram account (status or session)",
)
async def update_account(
    account_id: uuid.UUID,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    account_manager: AccountManager = Depends(get_account_manager),
    _: None = Depends(require_admin_key),
) -> AccountRead:
    account = crud.telegram_account.get(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    updated = crud.telegram_account.update(db, account, data)

    # Sync in-memory pool with DB changes
    if data.session_string is not None:
        # Re-connect with new session
        await account_manager.remove_account(account_id)
        await account_manager.add_account(updated)
    elif data.status == "active" and account_id not in account_manager._clients:
        await account_manager.add_account(updated)
    elif data.status in ("inactive", "rate_limited"):
        await account_manager.remove_account(account_id)

    return AccountRead.model_validate(updated)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a Telegram account from the pool",
)
async def delete_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    account_manager: AccountManager = Depends(get_account_manager),
    _: None = Depends(require_admin_key),
) -> None:
    account = crud.telegram_account.get(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    await account_manager.remove_account(account_id)
    crud.telegram_account.delete(db, account)
