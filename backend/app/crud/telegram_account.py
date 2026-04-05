import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import decrypt_session, encrypt_session
from app.models.telegram_account import AccountStatus, TelegramAccount
from app.schemas.account import AccountCreate, AccountUpdate


def get(db: Session, account_id: uuid.UUID) -> TelegramAccount | None:
    return db.get(TelegramAccount, account_id)


def get_by_phone(db: Session, phone: str) -> TelegramAccount | None:
    return db.exec(
        select(TelegramAccount).where(TelegramAccount.phone_number == phone)
    ).first()


def get_all(db: Session) -> list[TelegramAccount]:
    return list(db.exec(select(TelegramAccount)).all())


def get_active(db: Session) -> list[TelegramAccount]:
    return list(
        db.exec(
            select(TelegramAccount).where(
                TelegramAccount.status == AccountStatus.active
            )
        ).all()
    )


def get_least_loaded_active(db: Session) -> TelegramAccount | None:
    """Return the active account with the oldest last_used_at (round-robin)."""
    accounts = list(
        db.exec(
            select(TelegramAccount).where(
                TelegramAccount.status == AccountStatus.active
            )
        ).all()
    )
    if not accounts:
        return None
    # Never-used accounts (last_used_at=None) get highest priority
    accounts.sort(key=lambda a: a.last_used_at or datetime.min)
    return accounts[0]


def create(db: Session, data: AccountCreate) -> TelegramAccount:
    encrypted = encrypt_session(data.session_string, settings.SESSION_ENCRYPTION_KEY)
    account = TelegramAccount(
        phone_number=data.phone_number,
        api_id=data.api_id,
        api_hash=data.api_hash,
        session_string=encrypted,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update(
    db: Session, account: TelegramAccount, data: AccountUpdate
) -> TelegramAccount:
    if data.status is not None:
        account.status = data.status
    if data.session_string is not None:
        account.session_string = encrypt_session(
            data.session_string, settings.SESSION_ENCRYPTION_KEY
        )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def delete(db: Session, account: TelegramAccount) -> None:
    db.delete(account)
    db.commit()


def update_last_used(db: Session, account_id: uuid.UUID) -> None:
    account = db.get(TelegramAccount, account_id)
    if account:
        account.last_used_at = datetime.utcnow()
        db.add(account)
        db.commit()


def mark_rate_limited(db: Session, account_id: uuid.UUID, wait_seconds: int) -> None:
    account = db.get(TelegramAccount, account_id)
    if account:
        account.status = AccountStatus.rate_limited
        account.rate_limited_until = datetime.utcnow() + timedelta(seconds=wait_seconds)
        db.add(account)
        db.commit()


def restore_expired_rate_limits(db: Session) -> int:
    """Restore accounts whose rate-limit window has passed. Returns restored count."""
    now = datetime.utcnow()
    accounts = list(
        db.exec(
            select(TelegramAccount).where(
                TelegramAccount.status == AccountStatus.rate_limited,
                TelegramAccount.rate_limited_until <= now,  # type: ignore[operator]
            )
        ).all()
    )
    for account in accounts:
        account.status = AccountStatus.active
        account.rate_limited_until = None
        db.add(account)
    if accounts:
        db.commit()
    return len(accounts)


def get_plain_session(account: TelegramAccount) -> str:
    """Return the decrypted StringSession for a TelegramAccount."""
    return decrypt_session(account.session_string, settings.SESSION_ENCRYPTION_KEY)
