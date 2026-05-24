from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TelegramMessage:
    channel: str
    message_id: int
    text: str
    posted_at: datetime
    views: int
    forwards: int
    link: Optional[str]


@dataclass
class DigestResult:
    date_label: str
    total_collected: int
    total_selected: int
    summary_markdown: str
    delivered_to_telegram: bool
    summary_mode: str
