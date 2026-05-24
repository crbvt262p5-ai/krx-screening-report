from __future__ import annotations

import asyncio

from telegram_digest.config import Settings
from telegram_digest.pipeline import DailyDigestPipeline


async def _main() -> None:
    settings = Settings.from_env()
    pipeline = DailyDigestPipeline(settings)
    result = await pipeline.run()

    print(f"Collected: {result.total_collected}")
    print(f"Selected: {result.total_selected}")
    print(f"Output: {pipeline.output_path}")
    print(f"Delivered to Telegram: {result.delivered_to_telegram}")
    print(f"Summary mode: {result.summary_mode}")


if __name__ == "__main__":
    asyncio.run(_main())
