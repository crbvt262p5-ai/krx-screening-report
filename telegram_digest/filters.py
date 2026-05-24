from __future__ import annotations

from typing import Iterable, List

from telegram_digest.models import TelegramMessage


def _contains_keyword(text: str, keywords: List[str]) -> bool:
    if not keywords:
        return True

    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def select_messages(
    messages: Iterable[TelegramMessage],
    keywords: List[str],
    min_views: int,
    min_forwards: int,
    max_items: int,
) -> List[TelegramMessage]:
    filtered = [
        message
        for message in messages
        if _contains_keyword(message.text, keywords)
        and message.views >= min_views
        and message.forwards >= min_forwards
    ]

    filtered.sort(
        key=lambda message: (message.views, message.forwards, message.posted_at),
        reverse=True,
    )
    return filtered[:max_items]
