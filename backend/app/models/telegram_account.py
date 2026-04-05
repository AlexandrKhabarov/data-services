import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AccountStatus(str, enum.Enum):
    active = "active"
    rate_limited = "rate_limited"
    inactive = "inactive"


class TelegramAccount(SQLModel, table=True):
    __tablename__ = "telegram_accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone_number: str = Field(unique=True, index=True)
    api_id: int
    api_hash: str
    # Fernet-encrypted Telethon StringSession
    session_string: str = Field(sa_column_kwargs={"nullable": False})
    status: AccountStatus = Field(default=AccountStatus.active)
    # In-memory load balancing uses AccountManager; this column persists
    # last_used_at for round-robin ordering across restarts.
    last_used_at: Optional[datetime] = Field(default=None)
    rate_limited_until: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
