import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.telegram_account import AccountStatus


class AccountCreate(BaseModel):
    phone_number: str
    api_id: int
    api_hash: str
    # Plain-text StringSession — the API layer encrypts it before storage.
    session_string: str


class AccountUpdate(BaseModel):
    status: Optional[AccountStatus] = None
    # If provided (plain text), the stored session is re-encrypted.
    session_string: Optional[str] = None


class AccountRead(BaseModel):
    id: uuid.UUID
    phone_number: str
    api_id: int
    status: AccountStatus
    last_used_at: Optional[datetime]
    rate_limited_until: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
