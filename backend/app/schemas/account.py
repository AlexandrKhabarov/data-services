import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.telegram_account import AccountStatus


class AccountCreate(BaseModel):
    phone_number: str
    api_id: int
    api_hash: str
    # Plain-text StringSession — the API layer encrypts it before storage.
    session_string: str


class AccountUpdate(BaseModel):
    status: AccountStatus | None = None
    # If provided (plain text), the stored session is re-encrypted.
    session_string: str | None = None


class AccountRead(BaseModel):
    id: uuid.UUID
    phone_number: str
    api_id: int
    status: AccountStatus
    last_used_at: datetime | None
    rate_limited_until: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
