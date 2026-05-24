from __future__ import annotations

from typing import List

import httpx


class TelegramBotNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token and self._chat_id)

    async def send_markdown(self, text: str) -> None:
        if not self.enabled:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            for chunk in self._chunk_message(text):
                response = await client.post(
                    f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                    json={
                        "chat_id": self._chat_id,
                        "text": chunk,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if not payload.get("ok"):
                    raise RuntimeError(
                        f"Telegram Bot API request failed: {payload.get('description', 'unknown error')}"
                    )

    def _chunk_message(self, text: str, max_length: int = 3500) -> List[str]:
        if len(text) <= max_length:
            return [text]

        chunks: List[str] = []
        remaining = text
        while len(remaining) > max_length:
            split_at = remaining.rfind("\n", 0, max_length)
            if split_at <= 0:
                split_at = max_length
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()

        if remaining:
            chunks.append(remaining)
        return chunks
