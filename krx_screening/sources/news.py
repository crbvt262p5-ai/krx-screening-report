from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

import requests

from ..config import Settings
from ..models import EquitySnapshot

KEYWORDS = {
    "공급부족": 2.0,
    "ASP 상승": 2.0,
    "가동률 상승": 1.5,
    "고부가 믹스 전환": 2.0,
    "증설": 1.0,
}


class NewsEnricher:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            }
        )

    def enrich_growth_candidates(self, equities: list[EquitySnapshot]) -> None:
        candidates = sorted(
            equities,
            key=lambda item: (
                item.forecast_growth_next_year or -999,
                item.returns_6m or -999,
            ),
            reverse=True,
        )[: self.settings.news_candidate_limit]

        with ThreadPoolExecutor(max_workers=min(6, self.settings.max_workers)) as executor:
            futures = {executor.submit(self._fetch_keywords, equity): equity for equity in candidates}
            for future in as_completed(futures):
                equity = futures[future]
                try:
                    equity.news_keyword_hits = future.result()
                except Exception as exc:  # pragma: no cover
                    self.logger.warning("News enrich failed for %s %s: %s", equity.ticker, equity.name, exc)
                    equity.mark_missing("news_keywords")

    def _fetch_keywords(self, equity: EquitySnapshot) -> list[str]:
        query = quote_plus(f'"{equity.name}" 주식')
        url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
        response = self.session.get(url, timeout=self.settings.request_timeout)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        text = " ".join(
            " ".join(filter(None, [item.findtext("title"), item.findtext("description")]))
            for item in root.findall(".//item")[:15]
        )

        hits = [keyword for keyword in KEYWORDS if keyword in text]
        return hits
