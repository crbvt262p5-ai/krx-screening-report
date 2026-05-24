from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from telethon import TelegramClient
from telethon.errors import UsernameInvalidError

from telegram_digest.models import TelegramMessage


class TelegramCollector:
    def __init__(self, api_id: int, api_hash: str, session_name: str) -> None:
        self._client = TelegramClient(session_name, api_id, api_hash)

    async def collect_recent_messages(
        self,
        channels: List[str],
        lookback_hours: int,
    ) -> List[TelegramMessage]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        messages: List[TelegramMessage] = []

        async with self._client:
            for channel in channels:
                try:
                    entity = await self._client.get_entity(channel)
                except UsernameInvalidError as exc:
                    raise ValueError(
                        "Invalid TELEGRAM_CHANNELS entry. Replace example values like "
                        "'@channel_a' with real Telegram channel usernames."
                    ) from exc
                async for message in self._client.iter_messages(entity, limit=300):
                    if not message.date or message.date < cutoff:
                        break

                    text = (message.message or "").strip()
                    if not text:
                        continue

                    messages.append(
                        TelegramMessage(
                            channel=channel,
                            message_id=message.id,
                            text=text,
                            posted_at=message.date,
                            views=message.views or 0,
                            forwards=message.forwards or 0,
                            link=getattr(message, "link", None),
                        )
                    )

        return messages
