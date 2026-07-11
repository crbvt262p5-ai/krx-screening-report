from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from urllib.parse import quote_plus

import pandas as pd
import requests

from ..config import Settings
from ..models import EquitySnapshot

KEYWORDS = {
    "공급부족": 2.0,
    "ASP 상승": 2.0,
    "가동률 상승": 1.5,
    "고부가 믹스 전환": 2.0,
    "증설": 1.0,
    "증익": 1.8,
    "실적 상향": 2.2,
    "컨센서스 상향": 2.2,
    "수주 증가": 1.8,
    "점유율 확대": 2.0,
    "신규 고객": 1.7,
    "데이터센터": 1.6,
    "AI": 1.4,
    "전력기기": 1.4,
    "원전": 1.2,
    "방산": 1.2,
    "CAPA 확대": 1.8,
    "자사주": 1.8,
    "소각": 1.8,
    "배당 확대": 2.0,
    "주주환원": 2.0,
    "분리과세": 1.8,
    "익금불산입": 1.8,
    "지배구조": 1.6,
    "인적분할": 1.7,
    "합병": 1.4,
    "밸류업": 1.8,
    "상법 개정": 1.8,
}

IMPORTANT_NEWS_KEYWORDS = {
    "실적": 2.4,
    "컨센서스": 2.2,
    "상향": 2.1,
    "수주": 2.2,
    "계약": 1.9,
    "증설": 1.7,
    "증익": 2.0,
    "신규 고객": 1.8,
    "점유율": 1.8,
    "가동률": 1.6,
    "공급": 1.5,
    "데이터센터": 1.5,
    "AI": 1.4,
    "HBM": 1.8,
    "패키징": 1.7,
    "방산": 1.4,
    "조선": 1.4,
    "미국": 1.2,
    "ODM": 1.5,
    "배당": 1.7,
    "자사주": 1.8,
    "소각": 2.0,
    "밸류업": 1.7,
}

DISCLOSURE_KEYWORDS = {
    "영업(잠정)실적": 2.6,
    "단일판매ㆍ공급계약체결": 2.5,
    "자기주식": 2.3,
    "소각": 2.5,
    "배당": 2.1,
    "현금ㆍ현물배당": 2.2,
    "합병": 2.1,
    "분할": 2.1,
    "유상증자": 2.2,
    "무상증자": 1.9,
    "전환사채": 1.7,
    "신주인수권부사채": 1.7,
    "시설투자": 1.9,
    "조회공시": 1.4,
    "불성실공시": 1.4,
}

LOW_QUALITY_NEWS_PATTERNS = (
    "AI주식상승확률분석",
    "AI가 분석해주는",
    "주가 전망",
    "밀릴때마다",
    "저점을 줄때마다",
    "물량 모아둘 기회",
    "이후 전망 및 대응전략",
    "네이버 블로그",
    "투자분석",
    "Sonia Citron",
    "gVhDYuEzku",
    "주식민원처리반",
)

LOW_QUALITY_NEWS_REGEXES = (
    re.compile(r"^\[[^\]]*시그널\]"),
    re.compile(r"상승확률"),
    re.compile(r"적정주가"),
    re.compile(r"상한가가 고점 신호"),
)


class NewsEnricher:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger
        self.session = requests.Session()
        self._corp_code_map: dict[str, str] | None = None
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            }
        )

    def enrich_growth_candidates(self, equities: list[EquitySnapshot]) -> None:
        candidates = self._select_candidates(equities)

        with ThreadPoolExecutor(max_workers=min(6, self.settings.max_workers)) as executor:
            futures = {executor.submit(self._fetch_news_bundle, equity): equity for equity in candidates}
            for future in as_completed(futures):
                equity = futures[future]
                try:
                    payload = future.result()
                    equity.news_keyword_hits = payload["keywords"]
                    equity.important_news_items = payload["news_items"]
                    equity.important_disclosures = payload["disclosures"]
                except Exception as exc:  # pragma: no cover
                    self.logger.warning("News enrich failed for %s %s: %s", equity.ticker, equity.name, exc)
                    equity.mark_missing("news_keywords")

    def _select_candidates(self, equities: list[EquitySnapshot]) -> list[EquitySnapshot]:
        ranked = sorted(
            equities,
            key=lambda item: (
                item.forecast_growth_next_year or -999,
                item.eps_revision_3m_pct or -999,
                item.op_income_revision_3m_pct or -999,
                item.returns_3m or -999,
                item.returns_6m or -999,
                item.market_cap or -999,
                item.dividend_yield_normalized or item.dividend_yield_trailing or -999,
            ),
            reverse=True,
        )
        return ranked[: self.settings.news_candidate_limit]

    def _fetch_news_bundle(self, equity: EquitySnapshot) -> dict[str, list[str]]:
        query = quote_plus(f'"{equity.name}" 주식')
        url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
        response = self.session.get(url, timeout=self.settings.request_timeout)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        items = root.findall(".//item")[:15]
        texts = [
            " ".join(filter(None, [item.findtext("title"), item.findtext("description")]))
            for item in items
        ]
        text = " ".join(texts)

        hits = [keyword for keyword in KEYWORDS if keyword in text]
        news_items = self._important_news_titles(equity.name, items)
        disclosures = self._important_disclosures(equity)
        return {
            "keywords": hits,
            "news_items": news_items,
            "disclosures": disclosures,
        }

    def _important_news_titles(self, company_name: str, items: list[ET.Element]) -> list[str]:
        ranked: list[tuple[float, str]] = []
        seen: set[str] = set()
        for item in items:
            title = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").strip()
            cleaned_title = self._clean_title(title)
            if not title or cleaned_title in seen or self._is_low_quality_title(cleaned_title):
                continue
            score = self._score_news_text(company_name, f"{title} {description}")
            if score < 1.8:
                continue
            seen.add(cleaned_title)
            ranked.append((score, cleaned_title))
        ranked.sort(key=lambda entry: entry[0], reverse=True)
        return [title for _, title in ranked[:3]]

    def _score_news_text(self, company_name: str, text: str) -> float:
        score = 0.0
        if not self._mentions_company_strictly(company_name, text):
            return 0.0
        score += 1.0
        for keyword, weight in IMPORTANT_NEWS_KEYWORDS.items():
            if keyword in text:
                score += weight
        return score

    def _important_disclosures(self, equity: EquitySnapshot) -> list[str]:
        if not (self.settings.dart_enabled and self.settings.dart_api_key):
            return []

        corp_code = self._get_corp_code(equity.ticker)
        if not corp_code:
            return []

        try:
            disclosures = self._fetch_dart_disclosures(corp_code)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Disclosure fetch failed for %s %s: %s", equity.ticker, equity.name, exc)
            equity.mark_missing("important_disclosures")
            return []

        ranked: list[tuple[float, str]] = []
        seen: set[str] = set()
        for disclosure in disclosures:
            report_name = disclosure.get("report_nm", "").strip()
            receipt_date = disclosure.get("rcept_dt", "").strip()
            if not report_name:
                continue
            label = self._format_disclosure_label(receipt_date, report_name)
            if label in seen:
                continue
            score = sum(weight for keyword, weight in DISCLOSURE_KEYWORDS.items() if keyword in report_name)
            if score <= 0:
                continue
            seen.add(label)
            ranked.append((score, label))
        ranked.sort(key=lambda entry: entry[0], reverse=True)
        return [label for _, label in ranked[:2]]

    def _get_corp_code(self, ticker: str) -> str | None:
        if self._corp_code_map is None:
            self._corp_code_map = self._load_corp_code_map()
        return self._corp_code_map.get(ticker) if self._corp_code_map else None

    def _load_corp_code_map(self) -> dict[str, str]:
        cache_path = self.settings.cache_dir / "dart_corp_codes.csv"
        if not self.settings.dart_api_key or not cache_path.exists():
            return {}
        frame = pd.read_csv(cache_path, dtype={"stock_code": str, "corp_code": str})
        return dict(zip(frame["stock_code"], frame["corp_code"]))

    def _fetch_dart_disclosures(self, corp_code: str) -> list[dict[str, str]]:
        end = date.today()
        start = end - timedelta(days=10)
        response = self.session.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": self.settings.dart_api_key,
                "corp_code": corp_code,
                "bgn_de": start.strftime("%Y%m%d"),
                "end_de": end.strftime("%Y%m%d"),
                "page_count": "20",
            },
            timeout=self.settings.request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "000":
            return []
        return payload.get("list", [])

    def _format_disclosure_label(self, receipt_date: str, report_name: str) -> str:
        if len(receipt_date) == 8:
            return f"{receipt_date[4:6]}/{receipt_date[6:8]} {report_name}"
        return report_name

    def _clean_title(self, title: str) -> str:
        title = re.sub(r"\s*-\s*Google 뉴스$", "", title).strip()
        title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
        title = re.sub(r"\s+\|\s+[^|]+$", "", title).strip()
        title = re.sub(r'^["“”\']+|["“”\']+$', "", title).strip()
        title = re.sub(r"\s{2,}", " ", title)
        return title.strip()

    def _is_low_quality_title(self, title: str) -> bool:
        if not title:
            return True
        if any(pattern in title for pattern in LOW_QUALITY_NEWS_PATTERNS):
            return True
        return any(regex.search(title) for regex in LOW_QUALITY_NEWS_REGEXES)

    def _mentions_company_strictly(self, company_name: str, text: str) -> bool:
        if not company_name:
            return False
        pattern = re.compile(
            rf"(?<![0-9A-Za-z가-힣]){re.escape(company_name)}(?![0-9A-Za-z가-힣])"
        )
        return bool(pattern.search(text))
