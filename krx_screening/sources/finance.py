from __future__ import annotations

import io
import logging
import re
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..config import Settings
from ..models import EquitySnapshot


class FinanceEnricher:
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
        self._corp_code_map: dict[str, str] | None = None
        self._dart_semaphore = threading.BoundedSemaphore(
            max(1, self.settings.dart_max_concurrent)
        )
        self._history_cache = self._load_historical_cache()
        self._fnguide_dns_failures = 0
        self._fnguide_disabled = False
        self._fnguide_lock = threading.Lock()

    def enrich(self, equities: list[EquitySnapshot], trading_date: date) -> None:
        with ThreadPoolExecutor(max_workers=self.settings.max_workers) as executor:
            futures = {
                executor.submit(self._enrich_one, equity, trading_date): equity
                for equity in equities
            }
            for future in as_completed(futures):
                equity = futures[future]
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover
                    self.logger.warning("Finance enrich failed for %s %s: %s", equity.ticker, equity.name, exc)
                    equity.mark_missing("finance_bundle")

    def _enrich_one(self, equity: EquitySnapshot, trading_date: date) -> None:
        if self.settings.dart_enabled and self.settings.dart_api_key:
            try:
                self._apply_dart_financials(equity, trading_date)
            except requests.RequestException as exc:
                self.logger.warning(
                    "DART enrich failed for %s %s: %s",
                    equity.ticker,
                    equity.name,
                    exc,
                )
                equity.source_notes.append("dart:request_failed")
            except Exception as exc:  # pragma: no cover
                self.logger.warning(
                    "DART enrich failed for %s %s: %s",
                    equity.ticker,
                    equity.name,
                    exc,
                )
                equity.source_notes.append("dart:unexpected_error")
        try:
            self._apply_fnguide_fallback(equity)
        except requests.RequestException as exc:
            self.logger.warning("Finance enrich failed for %s %s: %s", equity.ticker, equity.name, exc)
            equity.mark_missing("finance_bundle")
        self._apply_historical_cache(equity)
        self._finalize_derived_metrics(equity)

    def _apply_dart_financials(self, equity: EquitySnapshot, trading_date: date) -> None:
        with self._dart_semaphore:
            corp_code = self._get_corp_code(equity.ticker)
            if not corp_code:
                equity.source_notes.append("dart:corp_code_missing")
                return

            years = [trading_date.year - offset for offset in (1, 2, 3)]
            annuals: list[dict[str, float | None]] = []
            for year in sorted(years):
                statement = self._fetch_dart_statement(corp_code, year)
                if statement:
                    annuals.append(statement)

            if not annuals:
                equity.source_notes.append("dart:no_financial_rows")
                return

            equity.sales_3y = [row.get("sales") for row in annuals][-3:]
            equity.op_income_3y = [row.get("op_income") for row in annuals][-3:]
            equity.net_income_3y = [row.get("net_income") for row in annuals][-3:]
            equity.debt_ratio = annuals[-1].get("debt_ratio") or equity.debt_ratio
            equity.cash_assets = annuals[-1].get("cash_assets") or equity.cash_assets
            equity.net_cash = annuals[-1].get("net_cash") or equity.net_cash
            equity.fcf = annuals[-1].get("fcf") or equity.fcf
            equity.source_notes.append("dart:annual_financials")

    def _apply_fnguide_fallback(self, equity: EquitySnapshot) -> None:
        if self._fnguide_disabled:
            equity.source_notes.append("fnguide:disabled_dns_failure")
            return

        url = (
            "https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp"
            f"?pGB=1&gicode=A{equity.ticker}&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701"
        )
        try:
            response = self._request_with_retries(url)
        except requests.RequestException as exc:
            if _is_dns_resolution_error(exc):
                with self._fnguide_lock:
                    self._fnguide_dns_failures += 1
                    if self._fnguide_dns_failures >= 3:
                        self._fnguide_disabled = True
                        self.logger.warning(
                            "FnGuide requests disabled for this run after repeated DNS failures"
                        )
                equity.source_notes.append("fnguide:dns_failed")
            raise

        soup = BeautifulSoup(response.text, "lxml")
        tables = self._read_html_tables(response.text)
        if not tables:
            equity.mark_missing("fnguide_tables")
            return

        snapshot = _parse_snapshot_table(tables)
        if equity.close is None:
            equity.close = snapshot.get("close")
        if equity.market_cap is None:
            equity.market_cap = snapshot.get("market_cap")
        if equity.per is None:
            equity.per = snapshot.get("per")
        if equity.dividend_yield is None:
            equity.dividend_yield = snapshot.get("dividend_yield")
            if equity.dividend_yield is not None:
                equity.dividend_yield_trailing = equity.dividend_yield
                equity.dividend_yield_normalized = equity.dividend_yield
                equity.dividend_yield_source = "fnguide_snapshot"
        if equity.pbr is None:
            equity.pbr = snapshot.get("pbr")
        if equity.close is not None:
            equity.clear_missing("prev_close")
        if equity.market_cap is not None:
            equity.clear_missing("market_cap")
        if equity.per is not None:
            equity.clear_missing("per", "value_per")
        if equity.pbr is not None:
            equity.clear_missing("pbr")
        if equity.dividend_yield is not None:
            equity.clear_missing("dividend_yield")

        if not equity.sales_3y or len(equity.sales_3y) < 3:
            parsed = _parse_annual_financials(tables)
            equity.sales_3y = parsed.get("sales_3y", equity.sales_3y)
            equity.op_income_3y = parsed.get("op_income_3y", equity.op_income_3y)
            equity.net_income_3y = parsed.get("net_income_3y", equity.net_income_3y)
            if equity.debt_ratio is None:
                equity.debt_ratio = parsed.get("debt_ratio")

        parsed_dividends = _parse_dividend_history(tables)
        if parsed_dividends and not equity.dividends_3y:
            equity.dividends_3y = parsed_dividends

        consensus_growth = _parse_consensus_growth(tables)
        if equity.forecast_growth_next_year is None:
            equity.forecast_growth_next_year = consensus_growth

        ratio_block = _parse_ratio_block(soup)
        if equity.payout_ratio is None:
            equity.payout_ratio = ratio_block.get("payout_ratio")
        if equity.debt_ratio is None:
            equity.debt_ratio = ratio_block.get("debt_ratio")
        if equity.cash_assets is None:
            equity.cash_assets = ratio_block.get("cash_assets")
        if equity.net_cash is None:
            equity.net_cash = ratio_block.get("net_cash")

        if equity.dividend_yield is None:
            equity.dividend_yield = ratio_block.get("dividend_yield")
            if equity.dividend_yield is not None:
                equity.dividend_yield_trailing = equity.dividend_yield
                equity.dividend_yield_normalized = equity.dividend_yield
                equity.dividend_yield_source = "fnguide_ratio_block"
        if equity.per is None:
            equity.per = ratio_block.get("per")
        if equity.pbr is None:
            equity.pbr = ratio_block.get("pbr")

        classification = _parse_business_classification(soup)
        if equity.sector is None:
            equity.sector = classification.get("sector")
        if equity.industry is None:
            equity.industry = classification.get("industry")
        equity.source_notes.append("fnguide:main")

    def _apply_historical_cache(self, equity: EquitySnapshot) -> None:
        cached = self._history_cache.get(equity.ticker)
        if not cached:
            return

        applied = False
        scalar_fields = {
            "per": "per",
            "pbr": "pbr",
            "dividend_yield": "dividend_yield",
            "op_income_volatility_pct": "op_income_volatility",
            "debt_ratio_pct": "debt_ratio",
            "cash_assets": "cash_assets",
            "net_cash": "net_cash",
            "fcf": "fcf",
            "payout_ratio_pct": "payout_ratio",
            "forecast_growth_next_year_pct": "forecast_growth_next_year",
        }
        for csv_field, attr in scalar_fields.items():
            if getattr(equity, attr) is None:
                value = _parse_amount(cached.get(csv_field))
                if value is not None:
                    setattr(equity, attr, value)
                    if attr == "dividend_yield" and equity.dividend_yield_source is None:
                        equity.dividend_yield_trailing = value
                        equity.dividend_yield_normalized = value
                        equity.dividend_yield_source = "historical_csv"
                    applied = True

        list_fields = {
            "sales_3y": "sales_3y",
            "op_income_3y": "op_income_3y",
            "net_income_3y": "net_income_3y",
            "dividends_3y": "dividends_3y",
        }
        for csv_field, attr in list_fields.items():
            current = getattr(equity, attr)
            if not current:
                values = _parse_pipe_numbers(cached.get(csv_field, ""))
                if values:
                    setattr(equity, attr, values)
                    applied = True

        for csv_field, attr in (("sector", "sector"), ("industry", "industry"), ("size_bucket", "size_bucket")):
            current = getattr(equity, attr)
            if not current:
                text = str(cached.get(csv_field) or "").strip()
                if text and text.lower() != "nan":
                    if attr in {"sector", "industry"}:
                        text = _clean_business_label(text) or ""
                    if text:
                        setattr(equity, attr, text)
                        applied = True

        if applied:
            equity.source_notes.append("cache:historical_csv")
            if equity.per is not None:
                equity.clear_missing("per", "value_per")
            if equity.pbr is not None:
                equity.clear_missing("pbr")
            if equity.dividend_yield is not None:
                equity.clear_missing("dividend_yield")
            if equity.sales_3y:
                equity.clear_missing("sales_3y")
            if equity.op_income_3y:
                equity.clear_missing("op_income_3y")
            if equity.net_income_3y:
                equity.clear_missing("net_income_3y")
            if equity.dividends_3y:
                equity.clear_missing("dividends_3y")

    def _load_historical_cache(self) -> dict[str, dict[str, str]]:
        data_dir = Path(self.settings.data_dir)
        files = sorted(data_dir.glob("screened_*.csv"), reverse=True)
        cache: dict[str, dict[str, str]] = {}
        for path in files:
            try:
                frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
            except Exception:  # pragma: no cover
                continue
            for row in frame.to_dict(orient="records"):
                ticker = str(row.get("ticker") or "").strip()
                if ticker and ticker not in cache:
                    cache[ticker] = row
            if len(cache) >= 2500:
                break
        return cache

    def _request_with_retries(self, url: str, attempts: int = 3) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.get(url, timeout=self.settings.request_timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt == attempts:
                    break
                time.sleep(min(1.5 * attempt, 3))
        assert last_error is not None
        raise last_error

    def _read_html_tables(self, html: str) -> list[pd.DataFrame]:
        try:
            return pd.read_html(io.StringIO(html), flavor=["lxml"])
        except ValueError:
            return []
        except ImportError:
            return pd.read_html(io.StringIO(html))

    def _finalize_derived_metrics(self, equity: EquitySnapshot) -> None:
        equity.sector = _clean_business_label(equity.sector) if equity.sector else None
        equity.industry = _clean_business_label(equity.industry) if equity.industry else None
        if equity.sales_3y and len(equity.sales_3y) < 3:
            equity.mark_missing("sales_3y")
        if equity.op_income_3y and len(equity.op_income_3y) < 3:
            equity.mark_missing("op_income_3y")
        if equity.net_income_3y and len(equity.net_income_3y) < 3:
            equity.mark_missing("net_income_3y")
        if equity.dividends_3y and len(equity.dividends_3y) < 3:
            equity.mark_missing("dividends_3y")

        if not equity.sales_3y:
            equity.mark_missing("sales_3y")
        else:
            equity.clear_missing("sales_3y")
        if not equity.op_income_3y:
            equity.mark_missing("op_income_3y")
        else:
            equity.clear_missing("op_income_3y")
        if not equity.net_income_3y:
            equity.mark_missing("net_income_3y")
        else:
            equity.clear_missing("net_income_3y")
        if not equity.dividends_3y:
            equity.mark_missing("dividends_3y")
        else:
            equity.clear_missing("dividends_3y")

        self._reconcile_dividend_yield(equity)

        if equity.op_income_3y and len(equity.op_income_3y) >= 2:
            series = pd.Series([v for v in equity.op_income_3y if v is not None and v != 0])
            if len(series) >= 2:
                equity.op_income_volatility = round(series.pct_change().dropna().std() * 100, 2)
        if equity.op_income_volatility is None:
            equity.mark_missing("op_income_volatility")
        else:
            equity.clear_missing("op_income_volatility")
        if equity.market_cap is not None:
            equity.size_bucket = _classify_size_bucket(equity.market_cap)

    def _reconcile_dividend_yield(self, equity: EquitySnapshot) -> None:
        non_zero_dividends = [value for value in equity.dividends_3y if value not in (None, 0)]
        trailing_dps = non_zero_dividends[-1] if non_zero_dividends else None
        normalized_dps = _normalized_dividend_dps(non_zero_dividends)

        computed_trailing = None
        computed_normalized = None
        if equity.close not in (None, 0):
            if trailing_dps is not None:
                computed_trailing = round((trailing_dps / equity.close) * 100, 2)
            if normalized_dps is not None:
                computed_normalized = round((normalized_dps / equity.close) * 100, 2)

        existing = equity.dividend_yield
        if computed_trailing is not None:
            if existing is None or _yield_mismatch(existing, computed_trailing):
                equity.dividend_yield = computed_trailing
                equity.source_notes.append("dividend_yield:reconciled")
            equity.dividend_yield_trailing = computed_trailing
        elif existing is not None and equity.dividend_yield_trailing is None:
            equity.dividend_yield_trailing = existing

        if computed_normalized is not None:
            equity.dividend_yield_normalized = computed_normalized
        elif existing is not None and equity.dividend_yield_normalized is None:
            equity.dividend_yield_normalized = existing

        if (
            equity.dividend_yield_trailing is not None
            and equity.dividend_yield_normalized is not None
            and equity.dividend_yield_trailing >= equity.dividend_yield_normalized * 1.8
            and "특별배당 가능성" not in equity.tags
        ):
            equity.tags.append("특별배당 가능성")

        if (
            equity.dividend_yield_source is None
            and (equity.dividend_yield_trailing is not None or equity.dividend_yield_normalized is not None)
        ):
            equity.dividend_yield_source = "reported"

        if equity.dividend_yield_trailing is not None or equity.dividend_yield_normalized is not None:
            equity.clear_missing("dividend_yield")
        else:
            equity.mark_missing("dividend_yield")

    def _get_corp_code(self, ticker: str) -> str | None:
        if self._corp_code_map is None:
            self._corp_code_map = self._load_corp_code_map()
        return self._corp_code_map.get(ticker) if self._corp_code_map else None

    def _load_corp_code_map(self) -> dict[str, str]:
        if not self.settings.dart_api_key:
            return {}

        cache_path = self.settings.cache_dir / "dart_corp_codes.csv"
        if cache_path.exists():
            frame = pd.read_csv(cache_path, dtype={"stock_code": str, "corp_code": str})
            return dict(zip(frame["stock_code"], frame["corp_code"]))

        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        response = self.session.get(
            url,
            params={"crtfc_key": self.settings.dart_api_key},
            timeout=self.settings.request_timeout,
        )
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_name = zf.namelist()[0]
            xml_bytes = zf.read(xml_name)

        xml_text = xml_bytes.decode("utf-8", errors="ignore")
        rows = []
        for soup_row in BeautifulSoup(xml_text, "xml").find_all("list"):
            stock_node = soup_row.find("stock_code")
            corp_node = soup_row.find("corp_code")
            stock_code = stock_node.text.strip() if stock_node and stock_node.text else ""
            corp_code = corp_node.text.strip() if corp_node and corp_node.text else ""
            if stock_code and corp_code:
                rows.append({"stock_code": stock_code, "corp_code": corp_code})

        frame = pd.DataFrame(rows)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(cache_path, index=False)
        return dict(zip(frame["stock_code"], frame["corp_code"]))

    def _fetch_dart_statement(self, corp_code: str, year: int) -> dict[str, float | None]:
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        response = self.session.get(
            url,
            params={
                "crtfc_key": self.settings.dart_api_key,
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": "11011",
                "fs_div": "CFS",
            },
            timeout=self.settings.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "000":
            response = self.session.get(
                url,
                params={
                    "crtfc_key": self.settings.dart_api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": "11011",
                    "fs_div": "OFS",
                },
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "000":
                return {}

        rows = data.get("list", [])
        lookup = {}
        for row in rows:
            account = (
                row.get("account_nm")
                or row.get("account_id")
                or ""
            ).replace(" ", "")
            amount = _parse_amount(row.get("thstrm_amount"))
            lookup[account] = amount

        sales = _first_value(lookup, ["매출액", "영업수익", "수익(매출액)"])
        op_income = _first_value(lookup, ["영업이익", "영업손실"])
        net_income = _first_value(lookup, ["당기순이익", "당기순손익", "연결당기순이익"])
        liabilities = _first_value(lookup, ["부채총계"])
        equity = _first_value(lookup, ["자본총계"])
        cash = _first_value(lookup, ["현금및현금성자산", "현금및현금성자산합계"])
        short_fin = _first_value(lookup, ["단기금융상품", "기타유동금융자산"])
        borrowings = _first_value(lookup, ["단기차입금", "장기차입금", "사채"])
        cfo = _first_value(lookup, ["영업활동으로인한현금흐름"])
        capex = sum(
            abs(v)
            for v in (
                _first_value(lookup, ["유형자산의취득"]),
                _first_value(lookup, ["무형자산의취득"]),
            )
            if v is not None
        ) or None

        debt_ratio = round((liabilities / equity) * 100, 2) if liabilities and equity else None
        cash_assets = (cash or 0) + (short_fin or 0) if cash or short_fin else None
        net_cash = (cash_assets - borrowings) if cash_assets is not None and borrowings is not None else None
        fcf = (cfo - capex) if cfo is not None and capex is not None else cfo

        return {
            "sales": sales,
            "op_income": op_income,
            "net_income": net_income,
            "debt_ratio": debt_ratio,
            "cash_assets": cash_assets,
            "net_cash": net_cash,
            "fcf": fcf,
        }


def _parse_annual_financials(tables: list[pd.DataFrame]) -> dict[str, list[float | None]]:
    parsed: dict[str, list[float | None]] = {}
    annual = None
    for table in tables:
        normalized = _normalize_financial_table(table)
        if normalized.empty:
            continue
        if {"매출액", "영업이익"}.issubset(set(normalized.index)):
            actual_cols = _actual_annual_columns(normalized.columns)
            if len(actual_cols) >= 3:
                annual = normalized
                break
    if annual is None:
        return parsed

    cols = _actual_annual_columns(annual.columns)[-3:]
    parsed["sales_3y"] = _parse_metric_row(annual, ["매출액", "영업수익"], cols)
    parsed["op_income_3y"] = _parse_metric_row(annual, ["영업이익"], cols)
    parsed["net_income_3y"] = _parse_metric_row(annual, ["당기순이익", "지배주주순이익"], cols)
    latest_col = cols[-1]
    liabilities = _lookup_metric_value(annual, ["부채총계"], latest_col)
    equity = _lookup_metric_value(annual, ["자본총계"], latest_col)
    parsed["debt_ratio"] = round((liabilities / equity) * 100, 2) if liabilities not in (None, 0) and equity not in (None, 0) else None
    return parsed


def _parse_dividend_history(tables: list[pd.DataFrame]) -> list[float | None]:
    for table in tables:
        normalized = _normalize_financial_table(table)
        if normalized.empty or "DPS" not in " ".join(normalized.index.astype(str)):
            continue
        cols = _actual_annual_columns(normalized.columns)[-3:]
        values = _parse_metric_row(normalized, ["DPS(원)", "DPS"], cols)
        if values:
            return values
    return []


def _parse_consensus_growth(tables: list[pd.DataFrame]) -> float | None:
    for table in tables:
        normalized = _normalize_financial_table(table)
        if normalized.empty:
            continue
        actual_cols = _actual_annual_columns(normalized.columns)
        estimate_cols = _estimate_annual_columns(normalized.columns)
        if not actual_cols or not estimate_cols:
            continue
        base_col = actual_cols[-1]
        est_col = estimate_cols[0]
        base = _lookup_metric_value(normalized, ["지배주주순이익", "당기순이익", "영업이익"], base_col)
        est = _lookup_metric_value(normalized, ["지배주주순이익", "당기순이익", "영업이익"], est_col)
        if base not in (None, 0) and est is not None:
            return round(((est / base) - 1) * 100, 2)
    return None


def _parse_snapshot_table(tables: list[pd.DataFrame]) -> dict[str, float | None]:
    result = {
        "close": None,
        "market_cap": None,
        "per": None,
        "pbr": None,
        "dividend_yield": None,
    }

    for table in tables[:2]:
        if table.empty:
            continue
        first_cell = str(table.iloc[0, 0]) if table.shape[1] >= 1 else ""
        if "종가" not in first_cell and "시가총액" not in table.to_string():
            continue
        try:
            close_fragment = str(table.iloc[0, 1]).split("/")[0].replace(",", "").strip()
            result["close"] = float(close_fragment)
        except (ValueError, TypeError, IndexError):
            pass
        try:
            market_cap_row = table[table.iloc[:, 0].astype(str).str.contains("시가총액", na=False)].iloc[0]
            result["market_cap"] = _parse_amount(market_cap_row.iloc[1])
        except Exception:
            pass

    for table in tables:
        if "PER" not in table.to_string():
            continue
        try:
            first_value_col = table.columns[1]
            key_col = table.columns[0]
            for label, field in (("PER", "per"), ("PBR", "pbr"), ("배당수익률", "dividend_yield")):
                matched = table[table[key_col].astype(str) == label]
                if not matched.empty:
                    parsed_value = _parse_amount(matched.iloc[0][first_value_col])
                    if parsed_value is not None:
                        result[field] = parsed_value
        except Exception:
            continue

    return result


def _parse_ratio_block(soup: BeautifulSoup) -> dict[str, float | None]:
    text = soup.get_text(" ", strip=True)
    result: dict[str, float | None] = {
        "payout_ratio": None,
        "debt_ratio": None,
        "cash_assets": None,
        "net_cash": None,
        "dividend_yield": None,
        "per": None,
        "pbr": None,
    }
    candidates = {
        "배당성향": "payout_ratio",
        "부채비율": "debt_ratio",
        "시가배당률": "dividend_yield",
        "PER": "per",
        "PBR": "pbr",
    }
    for label, key in candidates.items():
        value = _extract_label_value(text, label)
        if value is not None:
            result[key] = value
    return result


def _extract_label_value(text: str, label: str) -> float | None:
    match = re.search(rf"{re.escape(label)}[^0-9-]*(-?\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _parse_business_classification(soup: BeautifulSoup) -> dict[str, str | None]:
    text = soup.get_text(" ", strip=True)
    sector = None
    industry = None

    pattern = re.search(
        r"(KOSPI|KOSDAQ|KSE|코스피|코스닥)\s+([가-힣A-Za-z0-9&\-/ ]+?)\s*\|\s*FICS\s+([가-힣A-Za-z0-9&\-/ ]+)",
        text,
    )
    if pattern:
        sector = _clean_business_label(pattern.group(2))
        industry = _clean_business_label(pattern.group(3))

    if sector is None:
        sector = _extract_label_text(text, "업종")
    if industry is None:
        industry = _extract_label_text(text, "FICS")

    return {
        "sector": sector,
        "industry": industry,
    }


def _extract_label_text(text: str, label: str) -> str | None:
    match = re.search(
        rf"{re.escape(label)}\s*[:：]?\s*([가-힣A-Za-z0-9&\-/ ]{{2,40}})",
        text,
    )
    if not match:
        return None
    return _clean_business_label(match.group(1))


def _clean_business_label(value: str) -> str | None:
    text = str(value).strip(" |")
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"(주가추이|시세현황|외국인지분율).*$", "", text).strip()
    banned_tokens = (
        "분석",
        "경쟁사비교",
        "거래소공시",
        "금감원공시",
        "ETF",
        "ETN",
        "Snap",
        "News",
        "리포트",
        "실적속보",
        "컨센서스",
        "목표주가",
        "View",
    )
    if any(token.lower() in text.lower() for token in banned_tokens):
        return None
    text = re.sub(r"^(코스피|코스닥|KOSPI|KOSDAQ)\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+(코스피|코스닥|KOSPI|KOSDAQ)\s+", " ", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\b(FICS|WICS)\b.*$", "", text, flags=re.IGNORECASE).strip(" |")
    parts = [part for part in text.split() if part]
    if len(parts) >= 2 and parts[: len(parts) // 2] == parts[len(parts) // 2 :]:
        text = " ".join(parts[: len(parts) // 2])
    if not text:
        return None
    if len(text) > 24:
        return None
    allowed_keywords = (
        "금융",
        "보험",
        "증권",
        "은행",
        "건설",
        "화학",
        "기계",
        "유통",
        "금속",
        "반도체",
        "통신",
        "자동차",
        "운송",
        "서비스",
        "전기",
        "전자",
        "철강",
        "조선",
        "음식료",
        "바이오",
        "제약",
        "게임",
        "콘텐츠",
        "엔터",
        "미디어",
        "리츠",
        "소프트웨어",
        "인터넷",
        "헬스케어",
        "화장품",
        "교육",
    )
    if not any(keyword in text for keyword in allowed_keywords):
        return None
    return text.strip()


def _parse_metric_row(
    frame: pd.DataFrame, metric_names: list[str], columns: list[str]
) -> list[float | None]:
    for metric in metric_names:
        if metric in frame.index:
            row = frame.loc[metric, columns]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            if isinstance(row, pd.Series):
                return [_parse_amount(value) for value in row.tolist()]
    return []


def _lookup_metric_value(
    frame: pd.DataFrame, metric_names: list[str], column: str
) -> float | None:
    for metric in metric_names:
        if metric in frame.index and column in frame.columns:
            value = frame.loc[metric, column]
            if isinstance(value, pd.Series):
                value = value.dropna().iloc[0] if not value.dropna().empty else None
            return _parse_amount(value)
    return None


def _normalize_financial_table(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return pd.DataFrame()

    working = table.copy()
    if isinstance(working.columns, pd.MultiIndex):
        renamed_columns = []
        for index, column in enumerate(working.columns):
            if index == 0:
                renamed_columns.append("metric")
                continue
            top = str(column[0]).strip()
            bottom = str(column[1]).strip()
            if top in {"Annual", "Net Quarter"}:
                renamed_columns.append(f"{top}:{bottom}")
            else:
                renamed_columns.append(f"{top}_{bottom}")
        working.columns = renamed_columns
    else:
        working.columns = [str(col).strip() for col in working.columns]
        working = working.rename(columns={working.columns[0]: "metric"})

    if "metric" not in working.columns:
        return pd.DataFrame()
    working["metric"] = working["metric"].astype(str).str.strip()
    return working.set_index("metric")


def _actual_annual_columns(columns: pd.Index) -> list[str]:
    return [
        str(column)
        for column in columns
        if str(column).startswith("Annual:")
        and _is_year_column(_column_period(str(column)))
        and "(E)" not in str(column)
        and "(P)" not in str(column)
    ]


def _estimate_annual_columns(columns: pd.Index) -> list[str]:
    return [
        str(column)
        for column in columns
        if str(column).startswith("Annual:")
        and _is_year_column(_column_period(str(column)))
        and "(E)" in str(column)
    ]


def _is_year_column(value: str) -> bool:
    return len(value) >= 7 and value[:4].isdigit() and "/" in value


def _column_period(value: str) -> str:
    return value.split(":", 1)[1] if ":" in value else value


def _parse_amount(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    cleaned = str(value).replace(",", "").replace("%", "").strip()
    if not cleaned or cleaned in {"-", "N/A", "nan"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_pipe_numbers(value: str) -> list[float | None]:
    if not value:
        return []
    parsed = [_parse_amount(part) for part in str(value).split("|")]
    return parsed if any(item is not None for item in parsed) else []


def _is_dns_resolution_error(exc: requests.RequestException) -> bool:
    return "Failed to resolve" in str(exc) or "NameResolutionError" in str(exc)


def _first_value(lookup: dict[str, float | None], keys: list[str]) -> float | None:
    for key in keys:
        if key in lookup and lookup[key] is not None:
            return lookup[key]
    return None


def _classify_size_bucket(market_cap: float | None) -> str | None:
    if market_cap is None:
        return None
    if market_cap >= 10_000_000_000_000:
        return "Mega"
    if market_cap >= 2_000_000_000_000:
        return "Large"
    if market_cap >= 300_000_000_000:
        return "Mid"
    return "Small"


def _normalized_dividend_dps(dividends: list[float]) -> float | None:
    if not dividends:
        return None
    ordered = sorted(dividends)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def _yield_mismatch(existing: float, computed: float) -> bool:
    gap = abs(existing - computed)
    ratio_gap = gap / max(computed, 0.1)
    return gap >= 2.0 and ratio_gap >= 0.35
