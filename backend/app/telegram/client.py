import asyncio
import io
import logging

from telethon import TelegramClient, events
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)


class TelegramAccountClient:
    """
    Thin async wrapper around a Telethon TelegramClient for a single user account.

    Responsibilities:
    - Maintain a persistent MTProto connection.
    - Send a photo file to a target bot and await the first reply.

    Thread-safety: designed for use inside a single asyncio event loop.
    """

    def __init__(self, api_id: int, api_hash: str, session_string: str) -> None:
        self._client = TelegramClient(
            StringSession(session_string),
            api_id,
            api_hash,
        )

    async def connect(self) -> None:
        await self._client.connect()
        if not await self._client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authorized. "
                "Re-run scripts/add_account.py to generate a fresh session."
            )

    async def disconnect(self) -> None:
        if self._client.is_connected():
            await self._client.disconnect()

    async def send_photo_and_get_reply(
        self,
        photo_bytes: bytes,
        filename: str,
        target_bot: str,
        timeout: int = 60,
    ) -> str:
        """
        Send *photo_bytes* as a file to *target_bot* and return the first text reply.

        The handler is registered just before the send and removed immediately after
        the reply arrives (or the timeout fires), so concurrent jobs on different
        accounts never interfere with each other.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()

        @self._client.on(events.NewMessage(from_users=target_bot))  # type: ignore[untyped-decorator]
        async def _handler(event: events.NewMessage.Event) -> None:
            if not future.done():
                future.set_result(event.raw_text or "")

        try:
            bio = io.BytesIO(photo_bytes)
            bio.name = filename  # Telethon uses .name as the filename hint
            await self._client.send_file(target_bot, bio)
            logger.debug(
                "Photo sent to %s; awaiting reply (timeout=%ds)", target_bot, timeout
            )

            reply = await asyncio.wait_for(future, timeout=timeout)
            logger.debug("Reply received from %s", target_bot)
            return reply
        finally:
            self._client.remove_event_handler(_handler)
