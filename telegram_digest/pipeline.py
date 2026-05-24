from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from telegram_digest.collector import TelegramCollector
from telegram_digest.config import Settings
from telegram_digest.filters import select_messages
from telegram_digest.models import DigestResult
from telegram_digest.notifier import TelegramBotNotifier
from telegram_digest.summarizer import DigestSummarizer


class DailyDigestPipeline:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._collector = TelegramCollector(
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            session_name=settings.telegram_session_name,
        )
        self._summarizer = DigestSummarizer(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            language=settings.digest_language,
        )
        self._notifier = TelegramBotNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_bot_chat_id,
        )

    async def run(self) -> DigestResult:
        date_label = datetime.now().strftime("%Y-%m-%d")
        collected = await self._collector.collect_recent_messages(
            channels=self._settings.telegram_channels,
            lookback_hours=self._settings.filter_lookback_hours,
        )
        selected = select_messages(
            messages=collected,
            keywords=self._settings.filter_keywords,
            min_views=self._settings.filter_min_views,
            min_forwards=self._settings.filter_min_forwards,
            max_items=self._settings.filter_max_items,
        )
        selected = self._exclude_previously_sent(selected)
        summary, summary_mode = self._summarizer.summarize(selected, date_label=date_label)
        self._write_output(date_label, summary)
        delivered = False
        if selected and self._notifier.enabled:
            await self._notifier.send_markdown(summary)
            delivered = True
        if selected:
            self._remember_sent_messages(selected)
        return DigestResult(
            date_label=date_label,
            total_collected=len(collected),
            total_selected=len(selected),
            summary_markdown=summary,
            delivered_to_telegram=delivered,
            summary_mode=summary_mode,
        )

    def _write_output(self, date_label: str, summary: str) -> None:
        self._settings.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._settings.output_dir / f"digest-{date_label}.md"
        output_path.write_text(summary + "\n", encoding="utf-8")

    def _exclude_previously_sent(self, messages):
        sent_keys = self._load_sent_keys()
        return [message for message in messages if self._message_key(message) not in sent_keys]

    def _remember_sent_messages(self, messages) -> None:
        sent_keys = self._load_sent_keys()
        updated = sent_keys.union(self._message_key(message) for message in messages)
        payload = {"sent_keys": sorted(updated)[-500:]}
        self._state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _load_sent_keys(self) -> set[str]:
        if not self._state_path.exists():
            return set()
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return set()
        return set(payload.get("sent_keys", []))

    def _message_key(self, message) -> str:
        return f"{message.channel}:{message.message_id}"

    @property
    def _state_path(self) -> Path:
        self._settings.output_dir.mkdir(parents=True, exist_ok=True)
        return self._settings.output_dir / "sent_state.json"

    @property
    def output_path(self) -> Path:
        date_label = datetime.now().strftime("%Y-%m-%d")
        return self._settings.output_dir / f"digest-{date_label}.md"
