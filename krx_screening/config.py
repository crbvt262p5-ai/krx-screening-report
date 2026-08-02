from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    reports_dir: Path
    data_dir: Path
    logs_dir: Path
    cache_dir: Path
    timezone: ZoneInfo
    dart_api_key: str | None
    dart_enabled: bool
    max_workers: int
    news_candidate_limit: int
    request_timeout: int
    dart_max_concurrent: int
    portfolio_overlay_enabled: bool

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        base_dir = Path(os.getenv("KRX_SCREEN_BASE_DIR", Path.cwd()))
        load_dotenv(base_dir / ".env")
        return cls(
            base_dir=base_dir,
            reports_dir=base_dir / os.getenv("KRX_REPORTS_DIR", "reports"),
            data_dir=base_dir / os.getenv("KRX_DATA_DIR", "data"),
            logs_dir=base_dir / os.getenv("KRX_LOGS_DIR", "logs"),
            cache_dir=base_dir / os.getenv("KRX_CACHE_DIR", ".cache/krx_screening"),
            timezone=ZoneInfo(os.getenv("KRX_TIMEZONE", "Asia/Seoul")),
            dart_api_key=os.getenv("DART_API_KEY"),
            dart_enabled=os.getenv("KRX_USE_DART", "0").strip().lower() in {"1", "true", "yes", "on"},
            max_workers=int(os.getenv("KRX_MAX_WORKERS", "8")),
            news_candidate_limit=int(os.getenv("KRX_NEWS_CANDIDATE_LIMIT", "80")),
            request_timeout=int(os.getenv("KRX_REQUEST_TIMEOUT", "15")),
            dart_max_concurrent=int(os.getenv("KRX_DART_MAX_CONCURRENT", "2")),
            portfolio_overlay_enabled=os.getenv("KRX_ENABLE_PORTFOLIO_OVERLAY", "0").strip().lower() in {"1", "true", "yes", "on"},
        )

    def ensure_directories(self) -> None:
        for path in (
            self.reports_dir,
            self.data_dir,
            self.logs_dir,
            self.cache_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
