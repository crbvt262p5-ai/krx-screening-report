from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session_name: str
    telegram_channels: List[str]
    filter_keywords: List[str]
    filter_min_views: int
    filter_min_forwards: int
    filter_lookback_hours: int
    filter_max_items: int
    openai_api_key: str
    openai_model: str
    digest_language: str
    output_dir: Path
    telegram_bot_token: str
    telegram_bot_chat_id: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        api_id = os.getenv("TELEGRAM_API_ID", "").strip()
        api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
        channels = _split_csv(os.getenv("TELEGRAM_CHANNELS", ""))
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

        if not api_id:
            raise ValueError("TELEGRAM_API_ID is required")
        if not api_hash:
            raise ValueError("TELEGRAM_API_HASH is required")
        if not channels:
            raise ValueError("TELEGRAM_CHANNELS is required")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")

        return cls(
            telegram_api_id=int(api_id),
            telegram_api_hash=api_hash,
            telegram_session_name=os.getenv("TELEGRAM_SESSION_NAME", "telegram-digest"),
            telegram_channels=channels,
            filter_keywords=_split_csv(os.getenv("FILTER_KEYWORDS", "")),
            filter_min_views=int(os.getenv("FILTER_MIN_VIEWS", "0")),
            filter_min_forwards=int(os.getenv("FILTER_MIN_FORWARDS", "0")),
            filter_lookback_hours=int(os.getenv("FILTER_LOOKBACK_HOURS", "24")),
            filter_max_items=int(os.getenv("FILTER_MAX_ITEMS", "20")),
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            digest_language=os.getenv("DIGEST_LANGUAGE", "ko"),
            output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_bot_chat_id=os.getenv("TELEGRAM_BOT_CHAT_ID", "").strip(),
        )
