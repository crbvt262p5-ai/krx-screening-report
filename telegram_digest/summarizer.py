from __future__ import annotations

from collections import Counter
from typing import Iterable

from openai import OpenAI
from openai import OpenAIError

from telegram_digest.models import TelegramMessage


class DigestSummarizer:
    def __init__(self, api_key: str, model: str, language: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._language = language

    def summarize(self, messages: Iterable[TelegramMessage], date_label: str) -> tuple[str, str]:
        prepared_messages = list(messages)
        if not prepared_messages:
            return (
                f"# Daily Telegram Digest ({date_label})\n\n"
                "선택된 메시지가 없어 요약을 생성하지 않았습니다.\n",
                "empty",
            )

        try:
            prompt = self._build_prompt(prepared_messages, date_label)
            response = self._client.responses.create(
                model=self._model,
                input=prompt,
            )
            return response.output_text.strip(), "openai"
        except OpenAIError:
            return self._fallback_summary(prepared_messages, date_label), "fallback"

    def _build_prompt(self, messages: list[TelegramMessage], date_label: str) -> str:
        rendered_messages = []
        for index, message in enumerate(messages, start=1):
            rendered_messages.append(
                "\n".join(
                    [
                        f"[{index}] channel={message.channel}",
                        f"posted_at={message.posted_at.isoformat()}",
                        f"views={message.views}",
                        f"forwards={message.forwards}",
                        f"link={message.link or 'N/A'}",
                        f"text={message.text}",
                    ]
                )
            )

        joined_messages = "\n\n".join(rendered_messages)
        return f"""
You are a news digest editor.
Create a concise daily digest in {self._language} for Telegram messages.

Requirements:
- Output must be valid Markdown.
- Start with a title including the date: {date_label}.
- Include these sections:
  1. 오늘의 핵심 한줄
  2. 주요 주제 3개
  3. 조회수 높은 메시지 TOP 5
  4. 빠르게 훑기
- Mention channels when relevant.
- Preserve links when available.
- Do not invent facts not present in the messages.
- Group similar items into themes instead of listing everything separately.

Messages:
{joined_messages}
""".strip()

    def _fallback_summary(self, messages: list[TelegramMessage], date_label: str) -> str:
        top_messages = sorted(
            messages,
            key=lambda message: (message.views, message.forwards, message.posted_at),
            reverse=True,
        )[:5]
        keyword_counts = self._extract_keyword_counts(messages)

        lines = [f"# Daily Telegram Digest ({date_label})", ""]
        lines.append("## 오늘의 핵심 한줄")
        lines.append(
            f"최근 24시간 기준으로 {len(messages)}건의 후보 메시지 중 조회수 상위 이슈를 정리했습니다."
        )
        lines.append("")
        lines.append("## 주요 주제 3개")
        if keyword_counts:
            for keyword, count in keyword_counts[:3]:
                lines.append(f"- `{keyword}` 관련 메시지 {count}건")
        else:
            lines.append("- 반복적으로 등장한 키워드는 적었고, 조회수 기준 상위 메시지를 중심으로 정리했습니다.")
        lines.append("")
        lines.append("## 조회수 높은 메시지 TOP 5")
        for index, message in enumerate(top_messages, start=1):
            preview = self._truncate(message.text.replace("\n", " "), 120)
            link = message.link or "링크 없음"
            lines.append(
                f"{index}. [{message.channel}] 조회수 {message.views}, 전달 {message.forwards} | {preview} | {link}"
            )
        lines.append("")
        lines.append("## 빠르게 훑기")
        for message in top_messages:
            lines.append(
                f"- {message.channel}: {self._truncate(message.text.replace(chr(10), ' '), 90)}"
            )
        lines.append("")
        lines.append("> 이 요약은 OpenAI 호출 없이 규칙 기반 임시 모드로 생성되었습니다.")
        return "\n".join(lines).strip() + "\n"

    def _extract_keyword_counts(self, messages: list[TelegramMessage]) -> list[tuple[str, int]]:
        words: Counter[str] = Counter()
        for message in messages:
            for token in message.text.replace("\n", " ").split():
                clean = token.strip(".,!?:;()[]{}\"'").lower()
                if len(clean) < 3:
                    continue
                if clean.startswith("http"):
                    continue
                words[clean] += 1
        return words.most_common(3)

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."
