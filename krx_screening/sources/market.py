from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from ..models import EquitySnapshot

try:
    from pykrx import stock as pykrx_stock
except ImportError:  # pragma: no cover
    pykrx_stock = None

try:
    import FinanceDataReader as fdr
except ImportError:  # pragma: no cover
    fdr = None


@dataclass
class MarketDataBundle:
    trading_date: date
    equities: list[EquitySnapshot]


def load_market_bundle(target_date: date, logger: logging.Logger) -> MarketDataBundle:
    trading_date = resolve_latest_trading_date(target_date, logger)
    logger.info("Using trading date %s", trading_date.isoformat())

    listings = []
    listing_details: dict[str, dict[str, float | None]] = {}
    for market in ("KOSPI", "KOSDAQ"):
        market_listings, detail_map = _load_market_listing(market, logger)
        listings.extend(market_listings)
        listing_details.update(detail_map)

    price_frames = {}
    cap_frames = {}
    fundamental_frames = {}
    date_str = trading_date.strftime("%Y%m%d")
    for market in ("KOSPI", "KOSDAQ"):
        price_frames[market] = _load_price_frame(date_str, market, logger)
        cap_frames[market] = _load_cap_frame(date_str, market, logger)
        fundamental_frames[market] = _load_fundamental_frame(date_str, market, logger)

    equities: list[EquitySnapshot] = []
    for item in listings:
        snapshot = EquitySnapshot(ticker=item["ticker"], market=item["market"], name=item["name"])
        price_row = _safe_row(price_frames.get(snapshot.market), snapshot.ticker)
        cap_row = _safe_row(cap_frames.get(snapshot.market), snapshot.ticker)
        fund_row = _safe_row(fundamental_frames.get(snapshot.market), snapshot.ticker)
        listing_detail = listing_details.get(snapshot.ticker, {})
        snapshot.sector = _coerce_text(listing_detail.get("sector"))
        snapshot.industry = _coerce_text(listing_detail.get("industry"))

        snapshot.close = _coerce_float(price_row.get("종가")) or _coerce_float(listing_detail.get("close"))
        snapshot.market_cap = _coerce_float(cap_row.get("시가총액")) or _coerce_float(
            listing_detail.get("market_cap")
        )
        snapshot.size_bucket = _classify_size_bucket(snapshot.market_cap)
        snapshot.per = _coerce_float(fund_row.get("PER"))
        snapshot.pbr = _coerce_float(fund_row.get("PBR"))
        snapshot.dividend_yield = _coerce_float(fund_row.get("DIV"))
        if snapshot.dividend_yield is not None:
            snapshot.dividend_yield_trailing = snapshot.dividend_yield
            snapshot.dividend_yield_normalized = snapshot.dividend_yield
            snapshot.dividend_yield_source = "pykrx_snapshot"

        if snapshot.close is None:
            snapshot.mark_missing("prev_close")
        if snapshot.market_cap is None:
            snapshot.mark_missing("market_cap")
        if snapshot.per is None:
            snapshot.mark_missing("per")
        if snapshot.pbr is None:
            snapshot.mark_missing("pbr")
        if snapshot.dividend_yield is None:
            snapshot.mark_missing("dividend_yield")

        equities.append(snapshot)

    return MarketDataBundle(trading_date=trading_date, equities=equities)


def resolve_latest_trading_date(target_date: date, logger: logging.Logger) -> date:
    if pykrx_stock is None and fdr is None:
        raise RuntimeError("pykrx or FinanceDataReader is required to resolve trading dates.")

    for offset in range(0, 10):
        candidate = target_date - timedelta(days=offset)
        if _has_market_data(candidate.strftime("%Y%m%d"), logger):
            return candidate
    raise RuntimeError("Could not resolve a recent KRX trading date.")


def enrich_with_price_history(
    equities: list[EquitySnapshot], trading_date: date, logger: logging.Logger
) -> None:
    start_date = trading_date - timedelta(days=430)
    for equity in equities:
        hist = _load_price_history(equity.ticker, start_date, trading_date, logger)
        if hist.empty or "Close" not in hist.columns:
            equity.mark_missing("price_history")
            continue

        close_series = hist["Close"].dropna()
        if close_series.empty:
            equity.mark_missing("price_history")
            continue

        latest_close = close_series.iloc[-1]
        if not latest_close:
            equity.mark_missing("price_history")
            continue

        equity.returns_1m = _return_over_days(close_series, 21)
        equity.returns_3m = _return_over_days(close_series, 63)
        equity.returns_6m = _return_over_days(close_series, 126)
        equity.returns_12m = _return_over_days(close_series, 252)
        rolling_high = close_series.tail(252).max()
        equity.high_52w_ratio = round((latest_close / rolling_high) * 100, 2) if rolling_high else None
        equity.avg_trading_value_20d = _average_trading_value(hist, 20)
        equity.avg_trading_value_60d = _average_trading_value(hist, 60)

        if equity.returns_1m is None:
            equity.mark_missing("returns_1m")
        if equity.returns_3m is None:
            equity.mark_missing("returns_3m")
        if equity.returns_6m is None:
            equity.mark_missing("returns_6m")
        if equity.returns_12m is None:
            equity.mark_missing("returns_12m")
        if equity.high_52w_ratio is None:
            equity.mark_missing("high_52w_ratio")
        if equity.avg_trading_value_20d is None:
            equity.mark_missing("avg_trading_value_20d")
        if equity.avg_trading_value_60d is None:
            equity.mark_missing("avg_trading_value_60d")


def _load_market_listing(
    market: str, logger: logging.Logger
) -> tuple[list[dict[str, str]], dict[str, dict[str, float | None]]]:
    if pykrx_stock is not None:
        try:
            tickers = pykrx_stock.get_market_ticker_list(market=market)
            listings = [
                {
                    "ticker": ticker,
                    "name": pykrx_stock.get_market_ticker_name(ticker),
                    "market": market,
                }
                for ticker in tickers
            ]
            return listings, {}
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx listing failed for %s: %s", market, exc)

    if fdr is not None:
        listing = fdr.StockListing(market)
        listings = [
            {"ticker": str(row.Code).zfill(6), "name": row.Name, "market": market}
            for row in listing.itertuples()
        ]
        detail_map = {
            str(row.Code).zfill(6): {
                "close": _coerce_float(getattr(row, "Close", None)),
                "market_cap": _coerce_float(getattr(row, "Marcap", None)),
                "sector": _first_present_text(row, "Sector", "업종", "WICS업종명"),
                "industry": _first_present_text(row, "Industry", "산업", "업종소"),
            }
            for row in listing.itertuples()
        }
        return listings, detail_map

    logger.error("No market listing source available for %s", market)
    return [], {}


def _has_market_data(date_str: str, logger: logging.Logger) -> bool:
    if pykrx_stock is not None:
        try:
            frame = pykrx_stock.get_market_ohlcv_by_ticker(date_str, market="KOSPI")
            return not frame.empty
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx trading date probe failed for %s: %s", date_str, exc)

    if fdr is not None:
        try:
            frame = fdr.DataReader("KS11", date_str, date_str)
            return not frame.empty
        except Exception as exc:  # pragma: no cover
            logger.warning("Trading date probe failed for %s: %s", date_str, exc)
            return False

    return False


def _load_price_frame(date_str: str, market: str, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            return pykrx_stock.get_market_ohlcv_by_ticker(date_str, market=market)
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx price snapshot failed for %s on %s: %s", market, date_str, exc)
    logger.warning("pykrx unavailable, price snapshot for %s may be incomplete", market)
    return pd.DataFrame()


def _load_cap_frame(date_str: str, market: str, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            return pykrx_stock.get_market_cap_by_ticker(date_str, market=market)
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx market cap snapshot failed for %s on %s: %s", market, date_str, exc)
    logger.warning("pykrx unavailable, market cap snapshot for %s may be incomplete", market)
    return pd.DataFrame()


def _load_fundamental_frame(date_str: str, market: str, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            return pykrx_stock.get_market_fundamental_by_ticker(date_str, market=market)
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx fundamentals snapshot failed for %s on %s: %s", market, date_str, exc)
    logger.warning("pykrx unavailable, fundamentals snapshot for %s may be incomplete", market)
    return pd.DataFrame()


def _load_price_history(ticker: str, start_date: date, end_date: date, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            frame = pykrx_stock.get_market_ohlcv_by_date(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                ticker,
            )
            if not frame.empty and "종가" in frame.columns:
                return frame.rename(columns={"종가": "Close", "거래량": "Volume"})
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx price history failed for %s: %s", ticker, exc)

    if fdr is not None:
        try:
            frame = fdr.DataReader(ticker, start_date, end_date)
            if not frame.empty:
                return frame
        except Exception as exc:  # pragma: no cover
            logger.warning("FinanceDataReader price history failed for %s: %s", ticker, exc)

    return pd.DataFrame()


def _return_over_days(close_series: pd.Series, periods: int) -> float | None:
    if len(close_series) <= periods:
        return None
    previous = close_series.iloc[-periods - 1]
    latest = close_series.iloc[-1]
    if previous in (None, 0):
        return None
    return round(((latest / previous) - 1) * 100, 2)


def _average_trading_value(frame: pd.DataFrame, periods: int) -> float | None:
    if frame.empty or "Close" not in frame.columns or "Volume" not in frame.columns:
        return None
    window = frame[["Close", "Volume"]].dropna().tail(periods)
    if len(window) < min(periods, 10):
        return None
    traded = pd.to_numeric(window["Close"], errors="coerce") * pd.to_numeric(
        window["Volume"], errors="coerce"
    )
    traded = traded.dropna()
    if traded.empty:
        return None
    return round(float(traded.mean()), 2)


def _safe_row(frame: pd.DataFrame | None, ticker: str) -> pd.Series:
    if frame is None or frame.empty or ticker not in frame.index:
        return pd.Series(dtype="object")
    return frame.loc[ticker]


def _coerce_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _first_present_text(row: object, *names: str) -> str | None:
    for name in names:
        value = getattr(row, name, None)
        text = _coerce_text(value)
        if text:
            return text
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
