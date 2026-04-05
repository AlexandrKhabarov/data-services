import asyncio
import logging
import uuid

from app.models.telegram_account import TelegramAccount
from app.telegram.client import TelegramAccountClient

logger = logging.getLogger(__name__)


class NoAvailableAccountError(Exception):
    """Raised when all accounts are busy or the pool is empty."""


class AccountManager:
    """
    In-memory pool of Telegram user account clients with round-robin load balancing.

    Design decisions:
    - One job at a time per account to avoid reply-correlation ambiguity
      (we can't tell which bot reply belongs to which concurrent send).
    - `_in_flight` is tracked in memory; `last_used_at` is persisted in the DB
      (via the worker) so ordering survives restarts.
    - Accounts are added/removed dynamically via the admin API.
    """

    def __init__(self) -> None:
        self._clients: dict[uuid.UUID, TelegramAccountClient] = {}
        # 0 = free, 1 = busy
        self._in_flight: dict[uuid.UUID, int] = {}
        self._lock = asyncio.Lock()

    def __len__(self) -> int:
        return len(self._clients)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def add_account(self, account: TelegramAccount) -> None:
        from app.crud.telegram_account import get_plain_session

        session_string = get_plain_session(account)
        client = TelegramAccountClient(
            api_id=account.api_id,
            api_hash=account.api_hash,
            session_string=session_string,
        )
        await client.connect()
        async with self._lock:
            self._clients[account.id] = client
            self._in_flight[account.id] = 0
        logger.info("Account %s added to pool (%d total)", account.phone_number, len(self._clients))

    async def remove_account(self, account_id: uuid.UUID) -> None:
        async with self._lock:
            client = self._clients.pop(account_id, None)
            self._in_flight.pop(account_id, None)
        if client:
            await client.disconnect()
        logger.info("Account %s removed from pool", account_id)

    async def shutdown(self) -> None:
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
            self._in_flight.clear()
        for client in clients:
            try:
                await client.disconnect()
            except Exception:
                pass

    # ── Acquisition / release ────────────────────────────────────────────────

    async def acquire(self) -> tuple[uuid.UUID, TelegramAccountClient]:
        """
        Return the first free (in_flight == 0) client and mark it busy.
        Raises NoAvailableAccountError if all clients are busy or pool is empty.
        """
        async with self._lock:
            for account_id, client in self._clients.items():
                if self._in_flight.get(account_id, 0) == 0:
                    self._in_flight[account_id] = 1
                    return account_id, client
            raise NoAvailableAccountError(
                "No free Telegram accounts available — pool is empty or all are busy."
            )

    async def release(self, account_id: uuid.UUID) -> None:
        """Mark an account as free again. Safe to call even if the account was removed."""
        async with self._lock:
            if account_id in self._in_flight:
                self._in_flight[account_id] = 0

    # ── Introspection (for health endpoint) ──────────────────────────────────

    def pool_stats(self) -> dict[str, int]:
        total = len(self._clients)
        busy = sum(1 for v in self._in_flight.values() if v > 0)
        return {"total": total, "busy": busy, "free": total - busy}
